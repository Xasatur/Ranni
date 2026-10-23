"""Opt-in experimental commands for the existing discord.py bot."""
import os
from discord.ext import commands
from .pc_status import get_pc_status, format_pc_status

def install(bot):
    @bot.group(name="pc", invoke_without_command=True)
    async def pc(ctx):
        await ctx.send("Verwendung: `!pc status`")

    @pc.command(name="status")
    async def pc_status(ctx):
        allowed = os.getenv("RANNI_OWNER_DISCORD_ID", "").strip()
        if not allowed or str(ctx.author.id) != allowed:
            await ctx.send("Dieser Befehl ist nur für den konfigurierten Besitzer verfügbar.")
            return
        await ctx.send(format_pc_status(get_pc_status()))
