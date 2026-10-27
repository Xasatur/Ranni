"""Owner-only experimental commands for Ranni."""
import os
from .pc_status import get_pc_status, format_pc_status
from .pc_wake import wake_pc
from .bridge_state import get_status as get_bridge_status
from .wake_queue import request_wake


def install(bot):
    @bot.group(name="pc", invoke_without_command=True)
    async def pc(ctx):
        await ctx.send("Verwendung: `!pc status` oder `!pc wake`")

    @pc.command(name="status")
    async def pc_status(ctx):
        owner_id = os.getenv("RANNI_OWNER_DISCORD_ID", "").strip()
        if not owner_id or str(ctx.author.id) != owner_id:
            await ctx.send("Dieser Befehl ist nur für den konfigurierten Besitzer verfügbar.")
            return
        if os.getenv("RANNI_BRIDGE_MODE") == "push":
            await ctx.send(format_pc_status(get_bridge_status()))
        else:
            await ctx.send(format_pc_status(await get_pc_status()))

    @pc.command(name="wake")
    async def pc_wake(ctx, *, arguments=""):
        owner_id = os.getenv("RANNI_OWNER_DISCORD_ID", "").strip()
        if not owner_id or str(ctx.author.id) != owner_id:
            await ctx.send("Dieser Befehl ist nur für den konfigurierten Besitzer verfügbar.")
            return
        if arguments:
            await ctx.send("Verwendung: `!pc wake` ohne Argumente.")
            return
        if os.getenv("RANNI_BRIDGE_MODE") == "push":
            _, message = request_wake()
            await ctx.send(message)
            return
        await ctx.send(await wake_pc())
