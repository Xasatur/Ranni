"""Single-dyno, at-most-once wake handoff. No arbitrary action payloads."""
import time
import uuid

_pending = None
_last_request = 0.0
WAKE_COOLDOWN_SECONDS = 90
WAKE_EXPIRY_SECONDS = 90


def request_wake():
    global _pending, _last_request
    now = time.monotonic()
    if now - _last_request < WAKE_COOLDOWN_SECONDS:
        return False, "Wake wurde vor Kurzem angefordert. Bitte nicht mehrfach senden."
    _pending = {"id": str(uuid.uuid4()), "action": "wake", "expires": now + WAKE_EXPIRY_SECONDS}
    _last_request = now
    return True, "Wake-Auftrag zur Bridge gesendet. Start noch nicht bestätigt; später mit `!pc status` prüfen."


def claim_wake():
    global _pending
    if _pending is None:
        return None
    item = _pending
    _pending = None
    if time.monotonic() >= item["expires"]:
        return None
    return {"id": item["id"], "action": "wake"}
