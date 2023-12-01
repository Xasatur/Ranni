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
import random
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

active_streams = set()

openai.api_key = os.getenv("OPENAI_API_KEY")

meme_keywords = ['funny cat meme', 'space joke', 'gaming humor', 'fantasy meme', 'sci-fi parody']

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
    # Randomly select the type of content for variety
    content_options = [
        "a short Christmas story",
        "a Christmas poem",
        "a Christmas song",
        "a Christmas legend"
    ]
    selected_content = random.choice(content_options)
    
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=f"Write {selected_content} for a Discord community to enjoy in the morning.",
        max_tokens=150  # Increase max_tokens for potentially longer content
    )
    return response.choices[0].text.strip()


@tasks.loop(hours=24)
async def daily_meme_post():
    # Randomly select a meme keyword
    meme_prompt = random.choice(meme_keywords)
    
    # Generate an image using DALL-E (simplified example)
    # Assuming you have a function to handle DALL-E API requests
    image_url = await generate_image_with_dalle(meme_prompt)
    
    # Post the image in the meme channel
    meme_channel = bot.get_channel(1129781956268265612)
    if meme_channel:
        await meme_channel.send(image_url)  # Adjust based on how you receive the image

@daily_meme_post.before_loop
async def before_daily_meme_post():
    await bot.wait_until_ready()

daily_meme_post.start()


async def generate_image_with_dalle(prompt):
    dalle_api_key = os.getenv('DALLE_API_KEY')
    
    # API endpoint for DALL-E image generation
    url = 'https://api.openai.com/v1/images/generations'
    
    headers = {
        'Authorization': f'Bearer {dalle_api_key}',
        'Content-Type': 'application/json'
    }

    # Payload with the prompt for DALL-E
    payload = {
        'prompt': prompt,
        'model': 'dall-e-2',  # or 'dall-e-3' as per your requirement
        'n': 1,  # Number of images to generate
        'response_format': 'url'  # Format of the response
    }

# Make the API request
    response = requests.post(url, json=payload, headers=headers)

    # Handle the response
    if response.status_code == 200:
        data = response.json()
        if 'data' in data and len(data['data']) > 0:
            image_url = data['data'][0].get('url')  # Corrected way to access the URL
            return image_url
        else:
            print("No image data found in the response.")
            return None
    else:
        print(f"Failed to generate image: {response.content}")
        return None


twitch_token = get_twitch_token(twitch_client_id, twitch_client_secret)

@tasks.loop(minutes=5)
async def check_twitch_streams():
    global twitch_token, active_streams
    headers = {'Client-ID': twitch_client_id, 'Authorization': f'Bearer {twitch_token}'}

    # List of Twitch usernames to monitor
    twitch_users = ['jj_da_silva_', 'Kamaloya_', 'Pestdoktor_Dim', 'Slyntia', 'XanRobins', 'Xasaturr', 'Redskater90', 'SirPrimeRIP', 'HeimGamerKing', 'SimplyJackTV']

    for user in twitch_users:
        response = requests.get(f'https://api.twitch.tv/helix/streams?user_login={user}', headers=headers)
        data = response.json()

        if data['data']:  # If the user is currently streaming
            if user not in active_streams:
                # Stream just went live, send notification
                channel = bot.get_channel(842884135978926120)
                await channel.send(f"{user} is now live on Twitch! https://twitch.tv/{user}")
                active_streams.add(user)
        else:
            # Stream is offline, remove from active streams
            active_streams.discard(user)


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
async def poll(ctx, *args):
    args = ' '.join(args)  # Combine all arguments into one string
    parts = args.split('|')  # Split by the delimiter '|'
    if len(parts) < 3:
        await ctx.send("Please use the format: !poll Question | Option 1 | Option 2 | ...")
        return
    
    question = parts[0]
    options = parts[1:]
    
    if len(options) > 20:
        await ctx.send("You can only have a maximum of 20 options.")
        return

    emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟', 
              '🇦', '🇧', '🇨', '🇩', '🇪', '🇫', '🇬', '🇭', '🇮', '🇯']

    description = []
    for x, option in enumerate(options):
        description.append(f'\n{emojis[x]} {option.strip()}')  # strip() removes leading/trailing whitespace
    embed = discord.Embed(title=question.strip(), description=''.join(description))
    react_message = await ctx.send(embed=embed)

    for emoji in emojis[:len(options)]:
        await react_message.add_reaction(emoji)

@bot.command(name='jojo')
async def jojo(ctx):
    embed = discord.Embed(
        title="The Good Hunter",
        url="http://twitch.tv/XanRobins",
         description="Follow me on Twitch 💜\nhttp://twitch.tv/XanRobins",  # Twitch link added here
        color=0x800080  # This sets the color of the embed to a teal color similar to the example
    )

    # Set the author's name and icon to that of the streamer
    embed.set_author(name="XanRobins", icon_url="https://cdn-longterm.mee6.xyz/plugins/embeds/images/841775840089473054/58ecd762c933e5b4b65cd3714f71b74dfe1545888604d79eaf62d27447e671b6.png")

    # Set the thumbnail to the server's logo
    embed.set_thumbnail(url="https://cdn-longterm.mee6.xyz/plugins/embeds/images/841775840089473054/59693adf8df159b68a10619df0c7ee56feacf47e10468844ca4ab5b2358aee9c.png")

    # Set the main image to the streamer's promotional picture
    embed.set_image(url="https://cdn-longterm.mee6.xyz/plugins/embeds/images/841775840089473054/58ecd762c933e5b4b65cd3714f71b74dfe1545888604d79eaf62d27447e671b6.png")

    # Set the footer to your server's name and icon
    embed.set_footer(text="Hunter's Dream", icon_url="https://cdn-longterm.mee6.xyz/plugins/embeds/images/841775840089473054/59693adf8df159b68a10619df0c7ee56feacf47e10468844ca4ab5b2358aee9c.png")

    await ctx.send(embed=embed)



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
