"""Development launcher for experimental Ranni features.

Only the development entrypoint loads local .env with precedence over inherited
environment variables. The production Procfile and launcher are unchanged.
"""
import os
from dotenv import load_dotenv

load_dotenv(".env", override=True)

import Ranni
from ranni_assistant.commands import install

install(Ranni.bot)

if __name__ == "__main__":
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise SystemExit("DISCORD_BOT_TOKEN fehlt.")
    Ranni.bot.run(token)
