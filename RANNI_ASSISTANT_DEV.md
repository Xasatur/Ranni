# Ranni Assistant — development MVP

This is experimental and does **not** change the production `Procfile`, `master` branch, or deploy automatically.

## First command

`!pc status` displays **demo** device information. No Home Assistant access, Wake-on-LAN, or real online check is performed.

## Testing

1. Create a **separate Discord test bot** and use its token, not the production Ranni token.
2. Clone this branch and set `DISCORD_BOT_TOKEN`, `OPENAI_API_KEY`, and `RANNI_OWNER_DISCORD_ID` in your local environment. Keep secrets out of Git.
3. Install the existing dependencies in a compatible Python virtual environment. The pinned dependencies are outdated and might need modernization before the bot can start on current Python.
4. Start `python assistant_bootstrap.py`. Invite the test bot to a private test Discord server.
5. Enter `!pc status` from the configured Discord account. The response says DEMO, not online.
6. Run pure unit tests without Discord or API credentials using `python -m unittest discover -s tests`.

**Note:** This version uses a prefix command, not a Discord slash command. The repository currently pins `discord.py==1.7.3`; slash commands will be introduced during the separate dependency-modernization phase.

## Follow-up modernization

- Upgrade `discord.py`, `openai`, `aiohttp` and remove the unnecessary `asyncio` PyPI dependency in a **separate PR**.
- Migrate obsolete OpenAI completion/image calls; update Discord intents, interactions, and command sync.
- Stop blocking the event loop with synchronous `requests` calls.
- Move secrets and configuration to environment variables, update tests/CI, and preserve existing NPC/Twitch functionality.
- Later replace demo status with authenticated Home Assistant or network monitoring; restrict actions to owner ID and explicit allowlisted operations.

The default Heroku `Procfile` remains `worker: python Ranni.py` on this branch, too. To test on Heroku, use a separate app/worker command and a separate Discord bot token.
