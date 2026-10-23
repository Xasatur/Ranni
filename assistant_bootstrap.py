"""Development launcher: original Ranni with opt-in experimental features.

Run this file only for testing; production Procfile remains unchanged.
Requires the existing Ranni dependencies and DISCORD_BOT_TOKEN.
"""
import os
import Ranni
from ranni_assistant.commands import install

install(Ranni.bot)

if __name__ == "__main__":
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise SystemExit("DISCORD_BOT_TOKEN fehlt.")
    Ranni.bot.run(token)
