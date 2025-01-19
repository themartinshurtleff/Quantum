import asyncio
import json
import os
from datetime import datetime
import pytz
from websockets import connect
from termcolor import cprint
import discord

# Discord bot setup
intents = discord.Intents.default()
Quantum = discord.Client(intents=intents)

DISCORD_TOKEN = ""  # Replace with your Discord bot token
DISCORD_CHANNEL_ID = 1330340295874973846  # Replace with your Discord channel ID (integer)

websocket_url = 'wss://fstream.binance.com/ws/!forceOrder@arr'
filename = 'binance.csv'

if not os.path.isfile(filename):
    with open(filename, 'w') as f:
        f.write(",".join([
            'symbol', 'side', 'order_type', 'time_in_force',
            'original_quantity', 'price', 'average_price', 'order_status',
            'order_last_filled_quantity', 'order_filled_accumulated_quantity',
            'order_trade_time', 'usd_size'
        ]) + "\n")


async def binance_liquidation(uri, filename):
    async with connect(uri) as websocket:
        while True:
            try:
                msg = await websocket.recv()
                order_data = json.loads(msg)['o']
                symbol = order_data['s'].replace('USDT', '')
                side = order_data['S']
                timestamp = int(order_data['T'])
                filled_quantity = float(order_data['z'])
                price = float(order_data['p'])
                usd_size = filled_quantity * price
                est = pytz.timezone("US/Eastern")
                time_est = datetime.fromtimestamp(timestamp / 1000, est).strftime('%H:%M:%S')

                if usd_size > 20000:
                    liquidation_type = 'BUY LIQUIDATION' if side == 'SELL' else 'SELL LIQUIDATION'
                    display_symbol = symbol[:4]
                    output = f"{liquidation_type} {display_symbol} {time_est} ${usd_size:,.0f}"
                    color = 0x00FF00 if side == 'SELL' else 0xFF0000

                    embed = discord.Embed(
                        title=f"{liquidation_type} Alert 🚨",
                        description=f"**Symbol**: {display_symbol}\n"
                                    f"**Side**: {side}\n"
                                    f"**Price**: ${price:,.2f}\n"
                                    f"**Quantity**: {filled_quantity:,.2f}\n"
                                    f"**USD Size**: ${usd_size:,.2f}\n"
                                    f"**Time**: {time_est}",
                        color=color,
                        timestamp=datetime.utcnow()
                    )
                    embed.set_footer(text="Quantum Liquidation Tracker")
                    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/690014618546208768/1329714589587341373/ico.png?ex=678b58b7&is=678a0737&hm=6df65cc1308d1bfc2c7fe7ad375889d45cd69e6327eeece2da73bc91ae62d91e&")

                    # Send embed to Discord
                    await send_discord_embed(embed)

                msg_values = [str(order_data.get(key)) for key in ['s', 'S', 'o', 'f', 'q', 'p', 'ap', 'X', 'l', 'z', 'T']]
                msg_values.append(str(usd_size))
                with open(filename, 'a') as f:
                    trade_info = ','.join(msg_values) + '\n'
                    trade_info = trade_info.replace('USDT', '')
                    f.write(trade_info)

            except Exception as e:
                print(f"Error: {e}")
                await asyncio.sleep(5)


async def send_discord_embed(embed):
    await Quantum.wait_until_ready()
    channel = Quantum.get_channel(DISCORD_CHANNEL_ID)
    if channel:
        await channel.send(embed=embed)
    else:
        print("Discord channel not found!")


@Quantum.event
async def on_ready():
    print(f'Logged in as {Quantum.user}')
    await Quantum.wait_until_ready()
    channel = Quantum.get_channel(DISCORD_CHANNEL_ID)
    if channel:
        await channel.send("Quantum Liquidation Tracker - Status Online")
    else:
        print("Discord channel not found!")
    asyncio.create_task(binance_liquidation(websocket_url, filename))


# Run the Discord bot
Quantum.run(DISCORD_TOKEN)
