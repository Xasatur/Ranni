import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
from discord.ext import tasks
from datetime import datetime, time, timedelta
import requests
import openai
import requests
from requests.auth import HTTPBasicAuth


def load_bot_personality(file_path):
    with open(file_path, 'r') as f:
        personality = f.read()
    return personality
    
twitch_client_id = os.getenv('TWITCH_CLIENT_ID')
twitch_client_secret = os.getenv('TWITCH_CLIENT_SECRET')

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True  # Enabling the GUILD_MEMBERS intent

bot = commands.Bot(command_prefix=commands.when_mentioned_or('!'), intents=intents)
bot_personality = load_bot_personality("ranni personality.txt")  # Update this with the correct file name

openai.api_key = os.getenv("OPENAI_API_KEY")

def get_twitch_token(client_id, client_secret):
    url = 'https://id.twitch.tv/oauth2/token'
    body = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials'
    }
    response = requests.post(url, data=body)
    return response.json().get('access_token')


@bot.event
async def on_ready():
    print(f"{bot.user.name} has connected to Discord!")
    send_good_morning.start()
    check_twitch_streams.start()

async def generate_good_morning_message():
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt="Write a creative good morning message for a Discord community.",
        max_tokens=50
    )
    return response.choices[0].text.strip()

twitch_token = get_twitch_token(twitch_client_id, twitch_client_secret)

@tasks.loop(minutes=5)
async def check_twitch_streams():
    global twitch_token
    headers = {'Client-ID': twitch_client_id, 'Authorization': f'Bearer {twitch_token}'}
    
    # List of Twitch usernames to monitor
    twitch_users = ['jj_da_silva_', 'Kamaloya_']  

    for user in twitch_users:
        response = requests.get(f'https://api.twitch.tv/helix/streams?user_login={user}', headers=headers)
        data = response.json()

        if data['data']:  # If the user is currently streaming
            channel = bot.get_channel(842884135978926120)
            await channel.send(f"{user} is now live on Twitch! https://twitch.tv/{user}")

@tasks.loop(hours=24)
async def send_good_morning():
    now = datetime.now()
    target_time = time(hour=7, minute=0)  # Set the target time as 7 AM
    if now.time() > target_time:  # If it's already past 7 AM, wait until the next day
        tomorrow = now + timedelta(days=1)
        target_datetime = datetime.combine(tomorrow.date(), target_time)
    else:
        target_datetime = datetime.combine(now.date(), target_time)
    
    wait_seconds = (target_datetime - now).total_seconds()
    await asyncio.sleep(wait_seconds)  # Wait until 7 AM
    
    message = await generate_good_morning_message()
    channel = bot.get_channel(842847835803615292)
    if channel:
        await channel.send(message)

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
    welcome_channel = bot.get_channel(841775840089473056)  # Replace with your actual channel ID
    if welcome_channel is not None:
        embed = discord.Embed(
            title="Herzlich Willkommen auf Hunter's Dream Community!",
            description=f"Hey {member.mention}, willkommen! Wir hoffen, du findest dich gut zurecht. \n\n"
                        "Vergiss nicht, die Regeln im #regeln Kanal zu lesen und akzeptieren. \n"
                        "Wenn du Fragen hast, zögere nicht, das Team oder mich zu kontaktieren. \n"
                        "Viel Spaß!",
            color=0x800080  # You can change this to any color you like
        )
        embed.set_thumbnail(url=member.avatar_url)
        embed.set_author(name=member.name, icon_url=member.avatar_url)
        embed.set_footer(text="Hunter's Dream Community")
        await welcome_channel.send(embed=embed)
    else:
        print("Welcome channel not found.")

@bot.event
async def on_raw_reaction_add(payload):
    print("Reaction added!")
    if payload.channel_id == 843015545099649067 and payload.message_id == 914245852497870879 and payload.emoji.name == '✅':
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

@bot.command(name='poll')
async def poll(ctx, question, *options: str):
    if len(options) > 20:
        await ctx.send("You can only have a maximum of 20 options.")
        return

    if len(options) < 2:
        await ctx.send("You need at least 2 options to create a poll.")
        return

    emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟', 
              '🇦', '🇧', '🇨', '🇩', '🇪', '🇫', '🇬', '🇭', '🇮', '🇯']

    description = []
    for x, option in enumerate(options):
        description += '\n {} {}'.format(emojis[x], option)
    embed = discord.Embed(title=question, description=''.join(description))
    react_message = await ctx.send(embed=embed)

    for emoji in emojis[:len(options)]:
        await react_message.add_reaction(emoji)

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    mentioned = False
    for mention in message.mentions:
        if mention.id == bot.user.id:
            mentioned = True
            break

    keywords = ["Rannibot", "ranni", "Ranni", "praise the sun", "One Piece" ]  # Add more keywords as needed

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
    
    # This line is crucial for commands to be processed
    await bot.process_commands(message)

if __name__ == '__main__':
    # Start bot
    bot.run(os.getenv('DISCORD_BOT_TOKEN'))
