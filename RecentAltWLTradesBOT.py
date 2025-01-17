import asyncio
import json
import os
from datetime import datetime
from datetime import timezone
import pytz
from websockets import connect
from termcolor import cprint
import discord

# Discord bot setup
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
Quantum = discord.Client(intents=intents)

DISCORD_TOKEN = "MTMyOTcwNjgxMzI2ODE2ODc2NA.GH2JOo.vyu1o2sPY1YU8MRsdzxSTTnUbKSVp0b0OibncY"  # Replace with your bot token
DISCORD_CHANNEL_ID = 1309266576683569203  # Replace with your channel ID (integer)

# Binance tracking setup
symbols = ['pnutusdt', 'swarmsusdt']
websocket_url_base = 'wss://fstream.binance.com/ws/'
trades_filename = 'binance_trades.csv'

# Check if the CSV file exists
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

                if usd_size > 10000:
                    trade_type = 'SELL' if is_buyer_maker else 'BUY'
                    color = 0xFF0000 if trade_type == 'SELL' else 0x00FF00  # Red for SELL, Green for BUY
                    # Determine priority level based on trade size
                    if usd_size < 20000:
                        priority = "Low"
                        priority_color = 0x00FF00  # Green
                        titlee = f"{trade_type} Alert 🚨"
                        role_mention = ""  # No ping for low priority
                    elif 20000 <= usd_size < 30000:
                        priority = "Medium"
                        priority_color = 0xFFFF00  # Yellow
                        titlee = f"{trade_type} Alert 🚨🚨"
                        role_mention = ""  # No ping for medium priority
                    else:
                        priority = "High"
                        priority_color = 0xFF0000  # Red
                        titlee = f"{trade_type} Alert 🚨🚨🚨"
                        role_mention = f"<@&{1329716159708270654}>"  # Ping role for high priority

                    embed = discord.Embed(
                        title=f"{titlee}",
                        description=f"{role_mention}\n\n"
                                    f"**Symbol**: {display_symbol}\n"
                                    f"**Priority**: {priority}\n"
                                    f"**Price**: ${price:,.2f}\n"
                                    f"**Quantity**: {quantity:,.2f}\n"
                                    f"**USD Size**: ${usd_size:,.2f}\n"
                                    f"**Time**: {readable_trade_time}",
                        color=color,
                        timestamp=datetime.utcnow()
                    )
                    embed.set_footer(text="TradeNet Quantum V0.1")
                    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/690014618546208768/1329714589587341373/ico.png?ex=678b58b7&is=678a0737&hm=6df65cc1308d1bfc2c7fe7ad375889d45cd69e6327eeece2da73bc91ae62d91e&")

                    # Log to CSV
                    with open(filename, 'a') as f:
                        f.write(f"{event_time}, {symbol.upper()},{agg_trade_id},{price},{quantity},"
                                f"{trade_time},{is_buyer_maker}\n")

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
