import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
import requests

def load_bot_personality(file_path):
    with open(file_path, 'r') as f:
        personality = f.read()
    return personality

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True

bot = commands.Bot(command_prefix=commands.when_mentioned_or('/'), intents=intents)
bot_personality = load_bot_personality("ranni personality.txt")  # Update this with the correct path

openai.api_key = os.getenv("OPENAI_API_KEY")

@bot.event
async def on_ready():
    print(f"{bot.user.name} has connected to Discord!")

@bot.event
async def on_message(message):
    await bot.wait_until_ready()

    if message.author.bot:
        return

    ctx = await bot.get_context(message)
    if ctx.valid:
        await bot.process_commands(message)
    else:
        data = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": bot_personality},
                {"role": "user", "content": message.content},
            ],
            "max_tokens": 1000,
            "temperature": 0.7,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {openai.api_key}",
        }

        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data).json()

        if 'choices' in response:
            ai_response = response["choices"][0]["message"]["content"].strip()
            await message.channel.send(ai_response)
        else:
            print("Error:", response.get("error"))

if __name__ == '__main__':
    # Start bot
    bot.run(os.getenv('DISCORD_BOT_TOKEN'))



