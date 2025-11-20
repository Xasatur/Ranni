# Ranni Discord Bot

A Discord bot that blends community utilities with playful NPC interactions, Twitch notifications, and AI-powered responses.

## Prerequisites
- Python 3.11+
- A Discord bot token with message/content intents enabled
- OpenAI API key
- Twitch client credentials (for live notifications)

## Configuration
Set the following environment variables before running the bot:

| Variable | Purpose |
| --- | --- |
| `DISCORD_BOT_TOKEN` | Token for the Discord bot account. |
| `OPENAI_API_KEY` | API key for OpenAI completions and image generation. |
| `TWITCH_CLIENT_ID` / `TWITCH_CLIENT_SECRET` | Credentials used to poll Twitch streams. |
| `DISCORD_GUILD_ID` | Optional guild ID to prefer for NPC interactions. |
| `NPC_CHANNEL_IDS` | Comma-separated list of channel IDs where NPC sessions are allowed. If empty, any text channel the bot can write to is used. |
| `NPC_SESSION_DURATION` | Minutes before an NPC session automatically ends (default: 5). |

The bot personality used for general replies is loaded from `ranni personality.txt`. Update that file to change the persona.

## Running the bot
Install dependencies and start the bot:

```bash
pip install -r requirements.txt
python Ranni.py
```

## Bot behaviour
- **NPC conversations:** Users can start short-lived NPC roleplay sessions that reply with either static lines or OpenAI-generated text.
- **Direct mentions:** If the bot is mentioned or certain keywords are used, it replies in character using OpenAI chat completions.
- **Image requests:** Messages containing phrases like "show me a picture of" trigger a DALL·E image and a short textual answer.
- **Scheduled posts:** The bot sends a daily morning message with varied content options.
- **Twitch alerts:** Every five minutes it checks configured Twitch channels and announces when they go live.
- **Reaction onboarding:** Reacting with ✅ on a specific message grants the `Hollow` role.

## Command reference
| Command | Usage | Description |
| --- | --- | --- |
| `!npc` | `!npc` | Sends a DM with a UI to choose the target channel, NPC personality, and reply mode when Discord UI components are available. Falls back to a text hint if UI components are disabled. |
| `!npc_start` | `!npc_start <channel> <personality> [static\|openai]` | Starts an NPC session in the given text channel using either static scripted replies or OpenAI-generated responses. Ends automatically after the configured session duration. |
| `!ban` | `!ban @user` | Bans the mentioned user. Requires the `ban_members` permission. |
| `!unban` | `!unban <user_id>` | Unbans the specified user if they are currently banned. Requires the `ban_members` permission. |
| `!poll` | `!poll Question | Option 1 | Option 2 | ...` | Creates a reaction-based poll with up to 20 options, assigning numbered/lettered emoji to each choice. |
| `!jojo` | `!jojo` | Posts a preconfigured embed promoting the Twitch streamer **XanRobins**. |
| `!twitch` | `!twitch <channel_or_url> [display_name]` | Generates a Twitch follow embed for the provided channel, optionally overriding the display name. |

## Notes on NPC personalities
NPC personalities are defined in `Ranni.py` under `NPC_PERSONALITIES`. Each entry controls the label, description, prompts, and static replies used when running sessions. Add or edit entries there to customize available characters.
