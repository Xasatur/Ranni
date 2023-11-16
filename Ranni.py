import os
import asyncio
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
intents.members = True  # Enabling the GUILD_MEMBERS intent

bot = commands.Bot(command_prefix=commands.when_mentioned_or('!'), intents=intents)
bot_personality = load_bot_personality("ranni personality.txt")  # Update this with the correct file name

openai.api_key = os.getenv("OPENAI_API_KEY")

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member):
    await member.ban()
    await ctx.send(f"{member.mention} has been banned.")

@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, user: discord.User):
    banned_users = await ctx.guild.bans()
    for ban_entry in banned_users:
        if ban_entry.user.id == user.id:
            await ctx.guild.unban(user)
            await ctx.send(f"{user.name} has been unbanned.")
            return
    await ctx.send(f"{user.name} is not currently banned.")

@bot.event
async def on_ready():
    print(f"{bot.user.name} has connected to Discord!")

@bot.event
async def on_member_join(member):
    print(f"{member.name} has joined the server.")  # Debug print
    welcome_channel = bot.get_channel(1050711007741358110)  # Replace with your actual channel ID
    if welcome_channel is not None:
        await welcome_channel.send(f"Welcome {member.mention} to the server!")
    else:
        print("Welcome channel not found.")

@bot.event
async def on_raw_reaction_add(payload):
    print("Reaction added!")
    if payload.channel_id == 1050711007741358110 and payload.message_id == 1173646740818231337 and payload.emoji.name == '✅':
        guild = bot.get_guild(payload.guild_id)
        role = discord.utils.get(guild.roles, name='Hollow')

        if role is None:
            print("Role not found.")
            return

        try:
            member = await guild.fetch_member(payload.user_id)
        except discord.NotFound:
            print("Member not found.")
            return
        except discord.HTTPException:
            print("An error occurred while fetching the member.")
            return

        try:
            await member.add_roles(role)
        except discord.Forbidden:
            print("Missing permissions to add role.")
        except discord.HTTPException:
            print("An error occurred while adding the role.")
        else:
            print("Role added successfully.")


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    mentioned = False
    for mention in message.mentions:
        if mention.id == bot.user.id:
            mentioned = True
            break

    keywords = ["Rannibot", "ranni", "Ranni"]  # Add more keywords as needed

    if mentioned or any(keyword in message.content.lower() for keyword in keywords):
        # Bot is mentioned or the message contains one of the keywords
        await bot.wait_until_ready()
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
            ai_response = response["choices"][0]["message"]["content"].strip()[:2000]  # Truncate to 2000 characters
            await message.channel.send(ai_response)
        else:
            print("Error:", response.get("error"))




if __name__ == '__main__':
    # Start bot
    bot.run(os.getenv('DISCORD_BOT_TOKEN'))
