import asyncio
import json
import os
from datetime import datetime
import pytz
from websockets import connect
import discord

# Discord bot setup
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
Quantum = discord.Client(intents=intents)

DISCORD_TOKEN = ""  # Replace with your bot token
DISCORD_CHANNEL_ID = 1309266576683569203  # Replace with your channel ID (integer)

# Binance tracking setup
symbols = ['pnutusdt', 'swarmsusdt', 'btcusdt', 'ethusdt', 'xrpusdt', 'solusdt']
websocket_url_base = 'wss://fstream.binance.com/ws/'

# Define thresholds for each symbol (in USD size)
thresholds = {
    'pnutusdt': 50000,
    'swarmsusdt': 50000,
    'btcusdt': 1000000,
    'ethusdt': 300000,
    'xrpusdt': 200000,
    'solusdt': 120000
}

# CSV file for logging trades
trades_filename = 'binance_trades.csv'
if not os.path.isfile(trades_filename):
    with open(trades_filename, 'w') as f:
        f.write('Event Time, Symbol, Aggregate Trade ID, Price, Quantity, First Trade ID, Trade Time, Is Buyer Maker\n')


async def binance_trade_stream(uri, symbol, filename):
    async with connect(uri) as websocket:
        while True:
            try:
                message = await websocket.recv()
                data = json.loads(message)
                event_time = int(data['E'])
                agg_trade_id = data['a']
                price = float(data['p'])
                quantity = float(data['q'])
                trade_time = int(data['T'])
                is_buyer_maker = data['m']
                est = pytz.timezone('US/Eastern')
                readable_trade_time = datetime.fromtimestamp(trade_time / 1000, est).strftime('%H:%M:%S')
                usd_size = price * quantity
                display_symbol = symbol.upper().replace('USDT', '')

                # Get the threshold for the current symbol
                threshold = thresholds[symbol]

                # Determine priority
                if threshold <= usd_size < 1.5 * threshold:
                    priority = "Low"
                    priority_color = 0x00FF00  # Green
                    role_mention = ""  # No ping for low priority
                elif 1.5 * threshold <= usd_size < 1.75 * threshold:
                    priority = "Medium"
                    priority_color = 0xFFFF00  # Yellow
                    role_mention = ""  # No ping for medium priority
                elif usd_size >= 1.75 * threshold:
                    priority = "High"
                    priority_color = 0xFF0000  # Red
                    role_mention = f"<@&1329716159708270654>"  # Ping role for high priority
                else:
                    continue  # Skip trades below the threshold

                # Determine trade type and color
                trade_type = 'SELL' if is_buyer_maker else 'BUY'
                trade_color = 0xFF0000 if trade_type == 'SELL' else 0x00FF00

                # Create Discord embed
                embed = discord.Embed(
                    title=f"{trade_type} Alert 🚨 {priority} Priority",
                    description=f"{role_mention}\n\n"
                                f"**Symbol**: {display_symbol}\n"
                                f"**Priority**: {priority}\n"
                                f"**Price**: ${price:,.2f}\n"
                                f"**Quantity**: {quantity:,.2f}\n"
                                f"**USD Size**: ${usd_size:,.2f}\n"
                                f"**Time**: {readable_trade_time}",
                    color=trade_color,
                    timestamp=datetime.utcnow()
                )
                embed.set_footer(text="TradeNet Quantum V0.1")
                embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/690014618546208768/1329714589587341373/ico.png")

                # Log to CSV
                with open(filename, 'a') as f:
                    f.write(f"{event_time}, {symbol.upper()}, {agg_trade_id}, {price}, {quantity}, {trade_time}, {is_buyer_maker}\n")

                # Send embed to Discord
                await send_discord_embed(embed)
            except Exception as e:
                await asyncio.sleep(5)


async def send_discord_embed(embed):
    await Quantum.wait_until_ready()
    channel = Quantum.get_channel(DISCORD_CHANNEL_ID)
    if channel:
        await channel.send(embed=embed)
    else:
        print("Discord channel not found!")


async def main():
    filename = 'binance_trades.csv'

    # Create a task for each symbol trade stream
    tasks = []
    for symbol in symbols:
        stream_url = f"{websocket_url_base}{symbol}@aggTrade"
        tasks.append(binance_trade_stream(stream_url, symbol, filename))

    await asyncio.gather(*tasks)


@Quantum.event
async def on_ready():
    print(f'Logged in as {Quantum.user}')
    await Quantum.wait_until_ready()
    channel = Quantum.get_channel(DISCORD_CHANNEL_ID)
    if channel:
        await channel.send("TradeNet Quantum V0.1 - Status Online")
    else:
        print("Discord channel not found!")
    await main()  # Start the Binance stream when the bot is ready


# Run the Discord bot
Quantum.run(DISCORD_TOKEN)
