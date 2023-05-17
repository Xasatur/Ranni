import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import requests
import openai

def load_bot_personality(file_path):
    with open(file_path, 'r') as f:
        personality = f.read()
    return personality

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True

bot = commands.Bot(command_prefix=commands.when_mentioned_or('/'), intents=intents)
bot_personality = load_bot_personality("ranni personality.txt")  # Update this with the correct file name

openai.api_key = os.getenv("OPENAI_API_KEY")

@bot.event
async def on_ready():
    print(f"{bot.user.name} has connected to Discord!")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    await bot.process_commands(message)

    if not message.content.startswith(commands.when_mentioned_or('/').clean_prefix):
        if isinstance(message.channel, discord.DMChannel) or message.channel.name.lower() == 'ranni-bot':
            # Ranni responds in DMs and the #Ranni-Bot channel
            await generate_and_send_response(message)
        elif message.channel.name.lower() == 'roundtable':
            # Ranni responds when mentioned (not necessarily at the beginning) in the #Roundtable channel
            if bot.user in message.mentions:
                await generate_and_send_response(message)

async def generate_and_send_response(message):
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





