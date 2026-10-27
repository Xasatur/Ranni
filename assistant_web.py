"""One Heroku web dyno hosts Discord and a minimal authenticated status inbox.

No Home Assistant token is transferred to Heroku. No remote commands are accepted.
"""
import asyncio
import hmac
import os

from aiohttp import web
from dotenv import load_dotenv

load_dotenv(".env", override=True)

from ranni_assistant.bridge_state import set_state
from ranni_assistant.wake_queue import claim_wake
import Ranni
from ranni_assistant.commands import install

install(Ranni.bot)


async def health(request):
    return web.json_response({"ok": True})


async def status_push(request):
    expected = os.environ["RANNI_BRIDGE_SECRET"]
    provided = request.headers.get("Authorization", "")
    if not hmac.compare_digest(provided, "Bearer " + expected):
        raise web.HTTPUnauthorized()
    if request.content_length is not None and request.content_length > 512:
        raise web.HTTPRequestEntityTooLarge(max_size=512, actual_size=request.content_length)
    try:
        payload = await request.json()
        state = payload["state"]
        if not isinstance(state, str):
            raise ValueError()
        set_state(state)
    except (ValueError, KeyError, TypeError, web.HTTPBadRequest):
        raise web.HTTPBadRequest(text="Invalid sensor state")
    return web.json_response({"ok": True})


async def wake_poll(request):
    expected = os.environ["RANNI_BRIDGE_SECRET"]
    if not hmac.compare_digest(request.headers.get("Authorization", ""), "Bearer " + expected):
        raise web.HTTPUnauthorized()
    task = claim_wake()
    return web.json_response(task or {"action": "none"})


async def main():
    for key in ("DISCORD_BOT_TOKEN", "RANNI_BRIDGE_SECRET", "RANNI_OWNER_DISCORD_ID"):
        if not os.getenv(key):
            raise SystemExit(key + " fehlt")
    os.environ["RANNI_BRIDGE_MODE"] = "push"
    app = web.Application(client_max_size=512)
    app.router.add_get("/health", health)
    app.router.add_post("/bridge/status", status_push)
    app.router.add_get("/bridge/next", wake_poll)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=int(os.environ["PORT"]))
    await site.start()
    try:
        await Ranni.bot.start(os.environ["DISCORD_BOT_TOKEN"])
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
