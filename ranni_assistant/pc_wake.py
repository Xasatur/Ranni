"""Request only the locally configured wake script, without Discord arguments."""
import asyncio
import os
import re
from urllib.error import HTTPError, URLError

from .home_assistant import request_json, valid_url


async def wake_pc():
    base_url = os.getenv("HOME_ASSISTANT_URL", "").strip()
    token = os.getenv("HOME_ASSISTANT_TOKEN", "").strip()
    entity = os.getenv("HOME_ASSISTANT_WAKE_ENTITY", "").strip()
    if not all((base_url, token, entity)):
        return "Wake nicht konfiguriert: HOME_ASSISTANT_URL, HOME_ASSISTANT_TOKEN oder HOME_ASSISTANT_WAKE_ENTITY fehlt."
    if (not valid_url(base_url) or not re.fullmatch(r"script\.[a-z0-9_]+", entity)
            or any(char.isspace() for char in token)):
        return "Wake-Konfigurationsfehler: Home-Assistant-URL, Token oder Skript-Entitäts-ID ungültig."
    try:
        # Socket timeout bounds individual I/O; wait_for also bounds the caller.
        # A timed-out request may already have reached HA. Never retry automatically.
        await asyncio.wait_for(asyncio.to_thread(
            request_json, base_url, token, "/api/services/script/turn_on",
            {"entity_id": entity}), timeout=8)
    except TimeoutError:
        return "Zeitüberschreitung bei Home Assistant. Ob die Wake-Anfrage ankam, ist unklar. Prüfe `!pc status`."
    except (HTTPError, URLError, OSError, ValueError):
        return "Home-Assistant-API- oder Verbindungsfehler. Wake-Anfrage nicht bestätigt; prüfe `!pc status` und die Home-Assistant-Konfiguration."
    return "Home Assistant hat die Wake-Anfrage angenommen. Das bestätigt noch keinen PC-Start. Prüfe anschließend `!pc status`."
