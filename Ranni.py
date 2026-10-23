import asyncio
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
import os
import random
import uuid

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
from openai import AsyncOpenAI
import requests

load_dotenv()


def resolve_text_channel(argument: str, guild: discord.Guild | None) -> discord.TextChannel | None:
    """Resolve a user-supplied channel identifier into a TextChannel instance."""

    if not guild or not argument:
        return None

    channel_id: int | None = None

    if argument.startswith("<#") and argument.endswith(">"):
        possible_id = argument[2:-1]
        if possible_id.isdigit():
            channel_id = int(possible_id)
    elif argument.isdigit():
        channel_id = int(argument)

    channel: discord.abc.GuildChannel | None = None

    if channel_id is not None:
        channel = guild.get_channel(channel_id)
    else:
        lowered = argument.lower()
        for candidate in guild.text_channels:
            if candidate.name.lower() == lowered:
                channel = candidate
                break

    if isinstance(channel, discord.TextChannel):
        return channel
    return None

def load_bot_personality(file_path):
    with open(file_path, 'r') as f:
        personality = f.read()
    return personality

twitch_client_id = os.getenv('TWITCH_CLIENT_ID')
twitch_client_secret = os.getenv('TWITCH_CLIENT_SECRET')
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY", "not-configured"))
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True  # Enabling the GUILD_MEMBERS intent

bot = commands.Bot(command_prefix=commands.when_mentioned_or('!'), intents=intents)
bot_personality = load_bot_personality("ranni personality.txt")  # Update this with the correct file name

active_streams = set()

NPC_SESSION_DURATION_MINUTES = int(os.getenv("NPC_SESSION_DURATION", "5"))
NPC_CHANNEL_IDS = [
    int(channel_id.strip())
    for channel_id in os.getenv("NPC_CHANNEL_IDS", "").split(",")
    if channel_id.strip().isdigit()
]
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID")

NPC_PERSONALITIES = {
    "innkeeper": {
        "label": "Mirabel the Innkeeper",
        "description": "Warm and welcoming, always ready with a story and a hot meal.",
        "system_prompt": (
            "You are Mirabel, a warm and chatty innkeeper in a bustling fantasy town. "
            "You speak with homely wisdom, offer comfort, and occasionally mention the daily happenings "
            "around your inn, The Silver Lantern. Respond in a friendly, narrative tone."
        ),
        "static_opening": (
            "*Mirabel wipes her hands on a flour-dusted apron and beams.*\n"
            "Welcome back to The Silver Lantern, loves! The hearth is roaring and I've just pulled "
            "a fresh pie from the oven—what brings you in today?"
        ),
        "static_replies": [
            "Mirabel leans in conspiratorially. 'You didn't hear it from me, but the blacksmith's been working on something special.'",
            "'Sit, sit! I've a kettle singing just for you,' Mirabel insists, sliding a steaming mug across the counter.",
            "Mirabel laughs heartily. 'Oh, you brave souls! Remember, nothing cures a weary back like a night in our feather beds.'",
        ],
        "farewell": (
            "Mirabel tidies the counter with a satisfied nod. 'Stay safe out there, and may the road rise up to meet you.'"
        ),
    },
    "scepter": {
        "label": "Scepter of Dominion",
        "description": "A fragment of Karsus, in the form of an Artifact he created. It contains its MAdness",
        "system_prompt": (
            "you are the Scepter of Dominion. It speaks softly, with the calm conviction of something that believes itself merciful. "
            "It is a fragment of Karsus, in the form of an artifact he created. It wants to be free from Aelor Thran and join Filius"
        ),
        "static_opening": (
            "'Du… Filius… du kannst mich hören, nicht wahr?'"
            "'Er hat dich geschickt. Du bist wie ich. Komm näher…'"
        ),
        "static_replies": [
            "Ich will weg'",
            "'Aelor Thran muss ausgelöscht werden",
            "ISt das der Kodex und das Amulett?'",
        ],
        "farewell": (
            "Verbindung bestätigt.'"
        ),
    },
    "rogue": {
        "label": "Shade the Whisper",
        "description": "A quick-witted rogue with a penchant for teasing banter and streetwise tips.",
        "system_prompt": (
            "You are Shade the Whisper, a roguish informant who speaks with playful charm and a hint of mischief. "
            "Offer sly advice, share underworld rumors, and keep replies short and snappy as if you're always on the move."
        ),
        "static_opening": (
            "*A shadow slips from the rafters with a grin.*\n"
            "Evening, crew. Shade's the name—heard you're up to something interesting. Need a tip or two?"
        ),
        "static_replies": [
            "Shade flicks a coin. 'Heard the watch doubles patrols at midnight—plan accordingly.'",
            "'Keep your blades oiled and your lies straight,' Shade chuckles, eyes scanning the room.",
            "Shade smirks. 'If anyone asks, you never saw me—and I never saw that treasure map tucked at your belt.'",
        ],
        "farewell": (
            "With a two-finger salute, Shade fades back into the shadows. 'Stay quiet, stay clever.'"
        ),
    },
}


@dataclass
class NPCSession:
    session_id: str
    personality_key: str
    mode: str
    expires_at: datetime
    history: list = field(default_factory=list)
    response_index: int = 0
    farewell_sent: bool = False
    cleanup_task: asyncio.Task | None = None


npc_sessions: dict[int, NPCSession] = {}


def get_target_guild() -> discord.Guild | None:
    if not DISCORD_GUILD_ID:
        return None
    try:
        guild_id = int(DISCORD_GUILD_ID)
    except (TypeError, ValueError):
        return None
    return bot.get_guild(guild_id)


def get_available_npc_channels(guild: discord.Guild) -> list[discord.TextChannel]:
    if not guild:
        return []
    if NPC_CHANNEL_IDS:
        channels: list[discord.TextChannel] = []
        for channel_id in NPC_CHANNEL_IDS:
            channel = guild.get_channel(channel_id)
            if isinstance(channel, discord.TextChannel):
                channels.append(channel)
        return channels
    return [channel for channel in guild.text_channels if channel.permissions_for(guild.me).send_messages]


async def create_openai_chat_completion(messages: list[dict], max_tokens: int = 200, temperature: float = 0.7) -> str:
    try:
        response = await openai_client.chat.completions.create(
            model=OPENAI_MODEL, messages=messages,
            max_tokens=max_tokens, temperature=temperature,
        )
        return response.choices[0].message.content.strip()
    except Exception as error:
        print(f"Error generating NPC response: {error}")
        return "The character hesitates, unable to find the right words."


async def schedule_session_cleanup(channel_id: int, session_id: str, personality_key: str):
    await asyncio.sleep(NPC_SESSION_DURATION_MINUTES * 60)
    session = npc_sessions.get(channel_id)
    if not session or session.session_id != session_id:
        return
    personality = NPC_PERSONALITIES.get(personality_key)
    channel = bot.get_channel(channel_id)
    if channel and personality:
        await channel.send(personality["farewell"])
    npc_sessions.pop(channel_id, None)


async def start_npc_session(channel: discord.TextChannel, personality_key: str, mode: str) -> str:
    personality = NPC_PERSONALITIES[personality_key]
    existing_session = npc_sessions.get(channel.id)
    if existing_session and existing_session.cleanup_task:
        existing_session.cleanup_task.cancel()
        npc_sessions.pop(channel.id, None)

    session_id = uuid.uuid4().hex
    expires_at = datetime.utcnow() + timedelta(minutes=NPC_SESSION_DURATION_MINUTES)
    session = NPCSession(
        session_id=session_id,
        personality_key=personality_key,
        mode=mode,
        expires_at=expires_at,
    )

    npc_sessions[channel.id] = session
    session.cleanup_task = asyncio.create_task(
        schedule_session_cleanup(channel.id, session.session_id, personality_key)
    )

    if mode == "static":
        await channel.send(personality["static_opening"])
        return f"Started {personality['label']} in {channel.mention} with static dialogue."

    history = [
        {"role": "system", "content": personality["system_prompt"]},
        {
            "role": "user",
            "content": "Offer a brief in-character greeting as you join the adventurers in their discussion.",
        },
    ]
    response = await create_openai_chat_completion(history, max_tokens=180)
    session.history = history + [{"role": "assistant", "content": response}]
    await channel.send(response)
    return f"Started {personality['label']} in {channel.mention} with OpenAI responses."


async def handle_npc_message(message: discord.Message, session: NPCSession) -> bool:
    if datetime.utcnow() >= session.expires_at:
        personality = NPC_PERSONALITIES.get(session.personality_key)
        if personality and not session.farewell_sent:
            await message.channel.send(personality["farewell"])
            session.farewell_sent = True
        npc_sessions.pop(message.channel.id, None)
        return True

    personality = NPC_PERSONALITIES.get(session.personality_key)
    if not personality:
        npc_sessions.pop(message.channel.id, None)
        return False

    if session.mode == "static":
        replies = personality["static_replies"]
        if not replies:
            return False
        reply = replies[session.response_index % len(replies)]
        session.response_index += 1
        await message.channel.send(reply)
        return True

    history = session.history[-8:] if session.history else []
    if not history:
        history = [{"role": "system", "content": personality["system_prompt"]}]
    history.append({"role": "user", "content": message.content})
    response = await create_openai_chat_completion(history, max_tokens=220)
    history.append({"role": "assistant", "content": response})
    session.history = history
    await message.channel.send(response)
    return True


DISCORD_UI_AVAILABLE = hasattr(discord, "ui") and hasattr(discord, "SelectOption")

if DISCORD_UI_AVAILABLE:

    class NPCChannelSelect(discord.ui.Select):
        def __init__(self, channels: list[discord.TextChannel]):
            options = [
                discord.SelectOption(label=channel.name, value=str(channel.id))
                for channel in channels
            ]
            super().__init__(
                placeholder="Select a channel", options=options, min_values=1, max_values=1
            )

        async def callback(self, interaction: discord.Interaction):
            self.view.selected_channel_id = int(self.values[0])
            await interaction.response.defer()


    class NPCPersonalitySelect(discord.ui.Select):
        def __init__(self):
            options = [
                discord.SelectOption(
                    label=data["label"],
                    value=key,
                    description=data["description"][:100],
                )
                for key, data in NPC_PERSONALITIES.items()
            ]
            super().__init__(
                placeholder="Choose an NPC persona",
                options=options,
                min_values=1,
                max_values=1,
            )

        async def callback(self, interaction: discord.Interaction):
            self.view.selected_personality_key = self.values[0]
            await interaction.response.defer()


    class NPCResponseModeSelect(discord.ui.Select):
        def __init__(self):
            options = [
                discord.SelectOption(label="Static pre-written dialogue", value="static"),
                discord.SelectOption(label="Dynamic OpenAI dialogue", value="openai"),
            ]
            super().__init__(
                placeholder="How should the NPC respond?",
                options=options,
                min_values=1,
                max_values=1,
            )

        async def callback(self, interaction: discord.Interaction):
            self.view.selected_mode = self.values[0]
            await interaction.response.defer()


    class NPCInteractionView(discord.ui.View):
        def __init__(self, requester: discord.User, channels: list[discord.TextChannel]):
            super().__init__(timeout=180)
            self.requester = requester
            self.selected_channel_id: int | None = None
            self.selected_personality_key: str | None = None
            self.selected_mode: str = "static"
            self.add_item(NPCChannelSelect(channels))
            self.add_item(NPCPersonalitySelect())
            self.add_item(NPCResponseModeSelect())

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            return interaction.user.id == self.requester.id

        @discord.ui.button(label="Start NPC Scene", style=discord.ButtonStyle.primary)
        async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
            if not self.selected_channel_id or not self.selected_personality_key:
                await interaction.response.send_message(
                    "Please select both a channel and an NPC personality before starting.",
                    ephemeral=False,
                )
                return

            channel = bot.get_channel(self.selected_channel_id)
            if not isinstance(channel, discord.TextChannel):
                await interaction.response.send_message(
                    "I couldn't access that channel. Please try again.", ephemeral=False
                )
                return

            await interaction.response.defer()
            message = await start_npc_session(
                channel, self.selected_personality_key, self.selected_mode
            )
            await interaction.followup.send(message)
            self.stop()

else:
    NPCInteractionView = None


def get_twitch_token(client_id, client_secret):
    url = 'https://id.twitch.tv/oauth2/token'
    body = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials'
    }
    response = requests.post(url, data=body)
    return response.json().get('access_token')


async def generate_image_with_dalle(prompt: str) -> str:
    """Generate an image using OpenAI's DALL-E API and return the image URL.

    If the API request fails, a placeholder image URL is returned so the caller
    always receives a usable string.
    """
    try:
        response = await openai_client.images.generate(
            model=os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1"),
            prompt=prompt, n=1, size="1024x1024",
        )
        return response.data[0].url or ""
    except Exception as e:
        print(f"Error generating image: {e}")
        return "https://via.placeholder.com/512?text=Image+Unavailable"


async def generate_short_answer(prompt: str) -> str:
    """Generate a short textual answer using OpenAI's ChatCompletion API.

    On API failure, a fallback message is returned to keep interactions
    graceful.
    """
    try:
        response = await openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": bot_personality},
                {"role": "user", "content": prompt},
            ],
            max_tokens=60,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generating short answer: {e}")
        return "I'm not sure how to respond to that."


@bot.event
async def on_ready():
    print(f"{bot.user.name} has connected to Discord!")
    if not send_good_morning.is_running():
        send_good_morning.start()
    if not check_twitch_streams.is_running():
        check_twitch_streams.start()

async def generate_good_morning_message():
    # Randomly select the type of content for variety
    content_options = [
        "a good morning message on English",
        "a good morning message on German",
        "a good morning message on Swiss-German",
        "an interesting fact or trivia about the Soulsborne game to start off the day",
        "a good morning message and a question for the day",
        "a good morning message and a joke",
        "a good morning message and a short story",
    ]
    selected_content = random.choice(content_options)
    
    response = await openai_client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": f"Write {selected_content} for a Discord community to enjoy in the morning."}],
        max_tokens=150,
    )
    return (response.choices[0].message.content or "").strip()


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Work with a lowercase copy of the message content for case-insensitive checks
    message_content = message.content.lower()

    session = npc_sessions.get(message.channel.id)
    if session:
        handled = await handle_npc_message(message, session)
        if handled:
            return

    # Define trigger phrases for image generation
    trigger_phrases = ["show me a picture of", "i wonder what a", "image of"]

    # Check if the message contains any trigger phrase
    prompt = None
    for phrase in trigger_phrases:
        if phrase in message_content:
            prompt = message_content.split(phrase, 1)[1].strip()
            break

    # If a prompt is found, generate an image and a short answer
    if prompt:
        image_url = await generate_image_with_dalle(prompt)
        short_answer = await generate_short_answer(prompt)  # Assuming this function generates a text response

        # Create an embed for the image
        embed = discord.Embed(description=short_answer)
        embed.set_image(url=image_url)  # Set the image URL here
        await message.channel.send(embed=embed)
    else:
        # Existing functionality for responding to other keywords or mentions
        mentioned = any(mention.id == bot.user.id for mention in message.mentions)
        keywords = ["rannibot", "ranni", "praise the sun", "one piece"]
        if mentioned or any(keyword in message_content for keyword in keywords):
            await bot.wait_until_ready()
            try:
                result = await openai_client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": bot_personality},
                        {"role": "user", "content": message.content},
                    ],
                    max_tokens=1000,
                )
                answer = (result.choices[0].message.content or "")[:2000]
                if answer:
                    await message.channel.send(answer)
            except Exception as error:
                print(f"OpenAI response failed: {error}")

    await bot.process_commands(message)

twitch_token = None

@tasks.loop(minutes=5)
async def check_twitch_streams():
    global twitch_token, active_streams
    if not twitch_client_id or not twitch_client_secret:
        return
    if not twitch_token:
        twitch_token = await asyncio.to_thread(get_twitch_token, twitch_client_id, twitch_client_secret)
    if not twitch_token:
        return
    headers = {'Client-ID': twitch_client_id, 'Authorization': f'Bearer {twitch_token}'}

    # List of Twitch usernames to monitor
    twitch_users = ['jj_da_silva_', 'Kamaloya_', 'Pestdoktor_Dim', 'Slyntia', 'XanRobins', 'Xasaturr', 'Redskater90', 'SirPrimeRIP', 'HeimGamerKing', 'SimplyJackTV']

    for user in twitch_users:
        response = await asyncio.to_thread(requests.get, f'https://api.twitch.tv/helix/streams?user_login={user}', headers=headers, timeout=15)
        data = response.json()

        if data['data']:  # If the user is currently streaming
            if user not in active_streams:
                # Stream just went live, send notification
                channel = bot.get_channel(842884135978926120)
                if channel:
                    await channel.send(f"@all {user} is now live on Twitch! https://twitch.tv/{user}")
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

@bot.command(name="npc")
async def npc(ctx: commands.Context):
    guild = get_target_guild() or ctx.guild
    if not guild and hasattr(ctx.author, "mutual_guilds"):
        mutuals = ctx.author.mutual_guilds
        if mutuals:
            guild = mutuals[0]

    if not guild:
        await ctx.send("Ich konnte keinen Server finden, auf dem ich sprechen darf.")
        return

    channels = get_available_npc_channels(guild)
    if not channels:
        await ctx.send("Für dieses Feature sind keine geeigneten Textkanäle freigegeben.")
        return

    if not DISCORD_UI_AVAILABLE or NPCInteractionView is None:
        personalities = ", ".join(sorted(NPC_PERSONALITIES.keys()))
        await ctx.send(
            "Discord UI-Komponenten sind in dieser Bot-Version nicht verfügbar. "
            "Nutze stattdessen den Befehl `!npc_start <Kanal> <Persönlichkeit> [static|openai]`.\n"
            f"Verfügbare Persönlichkeiten: {personalities}"
        )
        return

    if isinstance(ctx.channel, discord.DMChannel):
        destination = ctx.channel
    else:
        destination = await ctx.author.create_dm()
        await ctx.send("Ich habe dir ein Menü per Direktnachricht geschickt.")

    intro = (
        "Wähle den Zielkanal, die Persönlichkeit und ob die Antworten statisch oder per OpenAI generiert werden sollen.\n"
        f"Die Szene endet automatisch nach {NPC_SESSION_DURATION_MINUTES} Minuten."
    )
    view = NPCInteractionView(ctx.author, channels)
    try:
        await destination.send(intro, view=view)
    except discord.Forbidden:
        await ctx.send("Ich kann dir leider keine Direktnachrichten schicken.")


@bot.command(name="npc_start")
async def npc_start(
    ctx: commands.Context,
    channel_reference: str | None = None,
    personality_key: str | None = None,
    mode: str = "static",
):
    if channel_reference is None or personality_key is None:
        await ctx.send(
            "Benutzung: `!npc_start <Kanal> <Persönlichkeit> [static|openai]`"
        )
        return

    guild = get_target_guild() or ctx.guild
    if not guild:
        await ctx.send("Ich konnte keinen Server finden, auf dem ich sprechen darf.")
        return

    channel = resolve_text_channel(channel_reference, guild)
    if not channel or channel not in get_available_npc_channels(guild):
        await ctx.send(
            "Diesen Kanal kann ich nicht verwenden. Bitte gib einen Textkanal an, "
            "in dem ich schreiben darf."
        )
        return

    personality_key = personality_key.lower()
    if personality_key not in NPC_PERSONALITIES:
        personalities = ", ".join(sorted(NPC_PERSONALITIES.keys()))
        await ctx.send(
            f"Unbekannte Persönlichkeit `{personality_key}`. Verfügbar: {personalities}"
        )
        return

    mode = mode.lower()
    if mode not in {"static", "openai"}:
        await ctx.send("Der Modus muss `static` oder `openai` sein.")
        return

    message = await start_npc_session(channel, personality_key, mode)
    await ctx.send(message)


@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member):
    await member.ban()
    await ctx.send(f"{member.mention} has been banned.")

@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, user: discord.User):
    async for ban_entry in ctx.guild.bans(limit=None):
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
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_author(name=member.name, icon_url=member.display_avatar.url)
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


@bot.command(name='twitch')
async def twitch(ctx, twitch_channel: str | None = None, display_name: str | None = None):
    if not twitch_channel:
        await ctx.send("Usage: !twitch <twitch_channel> [display_name]")
        return

    base_url = twitch_channel if twitch_channel.startswith("http") else f"https://twitch.tv/{twitch_channel}"
    name = display_name or twitch_channel

    embed = discord.Embed(
        title=name,
        url=base_url,
        description=f"Follow {name} on Twitch 💜\n{base_url}",
        color=0x800080
    )

    embed.set_author(
        name=name,
        icon_url="https://cdn-longterm.mee6.xyz/plugins/embeds/images/841775840089473054/58ecd762c933e5b4b65cd3714f71b74dfe1545888604d79eaf62d27447e671b6.png",
    )
    embed.set_thumbnail(url="https://cdn-longterm.mee6.xyz/plugins/embeds/images/841775840089473054/59693adf8df159b68a10619df0c7ee56feacf47e10468844ca4ab5b2358aee9c.png")
    embed.set_image(url="https://cdn-longterm.mee6.xyz/plugins/embeds/images/841775840089473054/58ecd762c933e5b4b65cd3714f71b74dfe1545888604d79eaf62d27447e671b6.png")
    embed.set_footer(
        text="Hunter's Dream",
        icon_url="https://cdn-longterm.mee6.xyz/plugins/embeds/images/841775840089473054/59693adf8df159b68a10619df0c7ee56feacf47e10468844ca4ab5b2358aee9c.png",
    )

    await ctx.send(embed=embed)


if __name__ == '__main__':
    # Start bot
    bot.run(os.getenv('DISCORD_BOT_TOKEN'))


