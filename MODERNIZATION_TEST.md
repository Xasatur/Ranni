# Ranni modernisierte Testumgebung

Der Branch `feature/ranni-assistant` enthält jetzt eine erste Modernisierung der Python-Abhängigkeiten und OpenAI-/Discord-Aufrufe. `master` und Herokus `Procfile` bleiben unverändert.

## Lokal aktualisieren (PowerShell)

```powershell
git switch feature/ranni-assistant
git pull origin feature/ranni-assistant
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install --upgrade -r requirements.txt
python -m unittest discover -s tests -v
python assistant_bootstrap.py
```

Die lokale `.env` muss einen **neuen**, nicht veröffentlichten Testbot-Token unter `DISCORD_BOT_TOKEN`, einen gültigen `OPENAI_API_KEY` und deine numerische `RANNI_OWNER_DISCORD_ID` enthalten. Für den ersten Discord-Test verwende `!pc status`. Das ist noch ein **Demo-Status**, keine Home-Assistant-Abfrage. Für Prefix-Befehle muss im Discord Developer Portal der **Message Content Intent** aktiviert sein.

## Bekannte Grenzen

- Die Image-Funktion ist noch nicht vollständig migriert: `gpt-image-1` gibt typischerweise Base64-Daten statt einer URL zurück. Das Feature braucht später einen Discord-Dateiupload.
- Die Reaktionen, NPC-Oberfläche, Twitch-Abfragen und alle OpenAI-Features wurden **nicht live auf Discord/Heroku getestet**.
- Beim Upgrade auf Discord 2.x können weitere API-Anpassungen nötig sein.
- Bei einem Crash bitte die Terminalausgabe ohne Tokens weitergeben.
- `master` vor Abschluss der Tests **nicht** mergen/deployen.
