"""Safe simulated PC status. No device access or credentials required."""
import os

def get_pc_status():
    """Return a deterministic demo result until real monitoring is configured."""
    return {
        "name": os.getenv("RANNI_PC_NAME", "Gaming Desktop"),
        "state": "DEMO",
        "detail": "Noch keine Verbindung zu Home Assistant. Kein echter PC-Status.",
    }

def format_pc_status(status):
    return (
        f"🖥️ **{status['name']}** — {status['state']}\n"
        f"{status['detail']}"
    )
