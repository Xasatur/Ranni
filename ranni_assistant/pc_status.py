"""Read a Home Assistant binary_sensor through its authenticated REST API."""
import asyncio
import os
from urllib.error import HTTPError, URLError
from .home_assistant import request_json


def format_pc_status(status):
    return f"🖥️ **{status['name']}** — {status['state']}\n{status['detail']}"


def _fetch_state(base_url, token, entity_id):
    return request_json(base_url, token, "/api/states/" + entity_id)


async def get_pc_status():
    name = os.getenv("RANNI_PC_NAME", "Gaming Desktop")
    base_url = os.getenv("HOME_ASSISTANT_URL", "").strip()
    token = os.getenv("HOME_ASSISTANT_TOKEN", "").strip()
    entity_id = os.getenv("HOME_ASSISTANT_PC_ENTITY", "").strip()
    if not all((base_url, token, entity_id)):
        return {"name": name, "state": "NICHT KONFIGURIERT",
                "detail": "HOME_ASSISTANT_URL, HOME_ASSISTANT_TOKEN oder HOME_ASSISTANT_PC_ENTITY fehlt."}
    if not base_url.startswith(("http://", "https://")) or not entity_id.startswith("binary_sensor."):
        return {"name": name, "state": "KONFIGURATIONSFEHLER",
                "detail": "Ungültige Home-Assistant-URL oder Ping-Entitäts-ID."}
    try:
        payload = await asyncio.to_thread(_fetch_state, base_url, token, entity_id)
        state = payload.get("state")
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as error:
        return {"name": name, "state": "UNBEKANNT",
                "detail": f"Home Assistant nicht erreichbar oder API-Fehler ({type(error).__name__})."}
    if state == "on":
        return {"name": name, "state": "ONLINE", "detail": "PC antwortet auf den Home-Assistant-Ping."}
    if state == "off":
        return {"name": name, "state": "OFFLINE", "detail": "Keine Ping-Antwort; PC könnte schlafen oder nicht erreichbar sein."}
    return {"name": name, "state": "UNBEKANNT",
            "detail": "Ping-Sensor meldet: " + str(state)[:50]}
