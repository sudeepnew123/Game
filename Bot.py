import random
import json
import time
from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage

API_TOKEN = os.getenv('BOT_TOKEN')  # Get bot token from environment variables
ADMIN_ID = int(os.getenv('ADMIN_ID'))  # Get admin ID from environment variables
DATA_FILE = 'users.json'  # Data file to store user information
  

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# Load and save data functions
def load_data():
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# Create grid with mines and gems
def create_grid(mines):
    grid = ['💎'] * 25
    for i in random.sample(range(25), mines):
        grid[i] = '💣'
    return grid

data = load_data()

# Command: /start
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id not in data:
        data[user_id] = {
            'username': message.from_user.username or message.from_user.first_name,
            'balance': 500,
            'game': None,
            'last_daily': 0,
            'last_weekly': 0
        }
        save_data(data)
        await message.reply("Account created! You got 500 Hiwa to start.")
    else:
        await message.reply("You're already registered.")

# Command: /balance
@dp.message_handler(commands=['balance'])
async def balance(message: types.Message):
    user = data.get(str(message.from_user.id))
    if user:
        await message.reply(f"Your balance: {user['balance']} Hiwa")
    else:
        await message.reply("Please use /start first.")

# Command: /mine
@dp.message_handler(commands=['mine'])
async def mine(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id not in data:
        await message.reply("Please use /start first.")
        return

    parts = message.text.split()
    if len(parts) != 3:
        await message.reply("Usage: /mine <amount> <mines>")
        return

    try:
        amount = int(parts[1])
        mines = int(parts[2])
        assert 3 <= mines <= 24
    except:
        await message.reply("Invalid input. Mines must be between 3 and 24.")
        return

    user = data[user_id]
    if user['balance'] < amount:
        await message.reply("Not enough Hiwa.")
        return

    grid = create_grid(mines)
    user['balance'] -= amount
    user['game'] = {
        'bet': amount,
        'mines': mines,
        'grid': grid,
        'revealed': []
    }
    save_data(data)

    display = ""
    for i in range(25):
        display += f'{i+1:2} '
        if (i + 1) % 5 == 0:
            display += '\n'

    await message.reply(f"Game started with {mines} mines!\nBet: {amount} Hiwa\n\n{display}\nUse /reveal <1-25> to pick a tile.")

# Command: /reveal
@dp.message_handler(commands=['reveal'])
async def reveal(message: types.Message):
    user_id = str(message.from_user.id)
    user = data.get(user_id)
    if not user or not user['game']:
        await message.reply("No active game. Use /mine to start one.")
        return

    parts = message.text.split()
    if len(parts) != 2:
        await message.reply("Usage: /reveal <1-25>")
        return

    try:
        tile = int(parts[1]) - 1
        assert 0 <= tile < 25
    except:
        await message.reply("Invalid tile number.")
        return

    if tile in user['game']['revealed']:
        await message.reply("Tile already revealed.")
        return

    user['game']['revealed'].append(tile)
    symbol = user['game']['grid'][tile]
    if symbol == '💣':
        user['game'] = None
        save_data(data)
        await message.reply("Boom! You hit a bomb and lost the game.")
        return

    save_data(data)
    await message.reply(f"Tile {tile+1} revealed: {symbol}\nUse /cashout to secure winnings or keep revealing!")

# Command: /cashout
@dp.message_handler(commands=['cashout'])
async def cashout(message: types.Message):
    user_id = str(message.from_user.id)
    user = data.get(user_id)
    if not user or not user['game']:
        await message.reply("No active game.")
        return

    gems = len(user['game']['revealed'])
    if gems < 2:
        await message.reply("Reveal at least 2 gems to cash out.")
        return

    reward = user['game']['bet'] + gems * 10
    user['balance'] += reward
    user['game'] = None
    save_data(data)
    await message.reply(f"You cashed out and won {reward} Hiwa!\nNew balance: {user['balance']}")

# Command: /daily
@dp.message_handler(commands=['daily'])
async def daily(message: types.Message):
    user_id = str(message.from_user.id)
    user = data.get(user_id)
    if not user:
        await message.reply("Use /start first.")
        return

    now = time.time()
    if now - user['last_daily'] < 86400:
        remain = int(86400 - (now - user['last_daily']))
        hours = remain // 3600
        minutes = (remain % 3600) // 60
        await message.reply(f"Come back in {hours}h {minutes}m for your daily bonus.")
        return

    user['balance'] += 100
    user['last_daily'] = now
    save_data(data)
    await message.reply("You received 100 Hiwa as daily bonus!")

# Command: /weekly
@dp.message_handler(commands=['weekly'])
async def weekly(message: types.Message):
    user_id = str(message.from_user.id)
    user = data.get(user_id)
    if not user:
        await message.reply("Use /start first.")
        return

    now = time.time()
    if now - user['last_weekly'] < 604800:
        remain = int(604800 - (now - user['last_weekly']))
        days = remain // 86400
        hours = (remain % 86400) // 3600
        await message.reply(f"Come back in {days}d {hours}h for your weekly bonus.")
        return

    user['balance'] += 300
    user['last_weekly'] = now
    save_data(data)
    await message.reply("You received 300 Hiwa as weekly bonus!")

# Command: /leaderboard
@dp.message_handler(commands=['leaderboard'])
async def leaderboard(message: types.Message):
    leaderboard = sorted(data.items(), key=lambda x: x[1]['balance'], reverse=True)[:5]
    text = "\n".join([f"{i+1}. {v['username']}: {v['balance']} Hiwa" for i, (k, v) in enumerate(leaderboard)])
    await message.reply("🏆 Top Players:\n" + text)

# Command: /gift
@dp.message_handler(commands=['gift'])
async def gift(message: types.Message):
    parts = message.text.split()
    if len(parts) != 3 or not parts[1].startswith('@'):
        await message.reply("Usage: /gift @username <amount>")
        return

    sender_id = str(message.from_user.id)
    sender = data.get(sender_id)
    if not sender:
        await message.reply("Use /start first.")
        return

    username = parts[1][1:].lower()
    try:
        amount = int(parts[2])
        assert amount > 0
    except:
        await message.reply("Enter a valid amount.")
        return

    receiver_id = None
    for uid, info in data.items():
        if info['username'].lower() == username:
            receiver_id = uid
            break

    if not receiver_id:
        await message.reply("Receiver not found.")
        return

    if sender['balance'] < amount:
        await message.reply("Not enough balance.")
        return

    sender['balance'] -= amount
    data[receiver_id]['balance'] += amount
    save_data(data)
    await message.reply(f"You sent {amount} Hiwa to @{username}!")

# Admin Command: /broadcast
@dp.message_handler(commands=['broadcast'])
async def broadcast(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    text = message.text.replace('/broadcast', '').strip()
    if not text:
        await message.reply("Usage: /broadcast <message>")
        return
    for uid in data:
        try:
            await bot.send_message(uid, f"📢 {text}")
        except:
            continue
    await message.reply("Broadcast sent!")

# Admin Command: /setbalance
@dp.message_handler(commands=['setbalance'])
async def setbalance(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) != 3:
        await message.reply("Usage: /setbalance @username <amount>")
        return
    username = parts[1][1:].lower()
    amount = int(parts[2])
    for uid, user in data.items():
        if user['username'].lower() == username:
            user['balance'] = amount
            save_data(data)
            await message.reply(f"Balance set to {amount} for @{username}")
            return
    await message.reply("User not found.")

# Admin Command: /addbalance
@dp.message_handler(commands=['addbalance'])
async def addbalance(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) != 3:
        await message.reply("Usage: /addbalance @username <amount>")
        return
    username = parts[1][1:].lower()
    amount = int(parts[2])
    for uid, user in data.items():
        if user['username'].lower() == username:
            user['balance'] += amount
            save_data(data)
            await message.reply(f"Added {amount} to @{username}'s balance.")
            return
    await message.reply("User not found.")

# ------------------- Start Bot -------------------
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
  
