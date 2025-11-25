# This example requires the 'message_content' intent.

import discord
import os
from dotenv import load_dotenv

load_dotenv("token.env")
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

client.run(TOKEN)
