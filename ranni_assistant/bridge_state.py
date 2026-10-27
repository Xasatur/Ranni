"""Volatile, read-only PC state pushed by the local Home Assistant bridge."""
import time

_last = None


def set_state(state):
    global _last
    if state not in ("on", "off", "unavailable", "unknown"):
        raise ValueError("Invalid state")
    _last = (state, time.monotonic())


def get_status():
    if _last is None or time.monotonic() - _last[1] > 120:
        return {"name": "Gaming Desktop", "state": "UNBEKANNT",
                "detail": "Keine aktuelle Meldung der Ranni Bridge (max. 120 Sekunden)."}
    state = _last[0]
    if state == "on":
        return {"name": "Gaming Desktop", "state": "ONLINE",
                "detail": "Letzte Meldung der Home-Assistant-Bridge: PC erreichbar."}
    if state == "off":
        return {"name": "Gaming Desktop", "state": "OFFLINE",
                "detail": "Letzte Meldung der Home-Assistant-Bridge: keine Ping-Antwort."}
    return {"name": "Gaming Desktop", "state": "UNBEKANNT",
            "detail": "Home Assistant meldet Sensorstatus: " + state}
