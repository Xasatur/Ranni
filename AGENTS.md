# Ranni Assistant — Codex handoff (2026-10-24)

This is the authoritative **development handoff** for Codex working in this repository. Read it alongside actual source code; inspect and validate code rather than assuming this document is always current.

## Goal
Evolve a legacy Discord bot, **Ranni**, into a personal assistant that coordinates a Home Assistant Green device, a Windows gaming/ML workstation, a laptop/mobile clients and eventually an authenticated Windows worker. The assistant should support remote PC status, wake-on-LAN, job dispatch, and later OpenAI-assisted workflows. Avoid implementing all of that in one step. Current next task is strictly **Wake-on-LAN through Home Assistant**.

## Repository and branch safety
- Repository: https://github.com/Xasatur/Ranni
- Default/production branch: `master`; existing Heroku production bot uses `Procfile` (`worker: python Ranni.py`).
- Working development branch: `feature/ranni-assistant`; draft PR: https://github.com/Xasatur/Ranni/pull/16
- Do not edit `master`, deploy to Heroku or change the production `Procfile` without explicit approval.
- Development entrypoint: `python assistant_bootstrap.py` using a **separate Discord application: Ranni Dev** and a private test server.
- `Ranni.py` was migrated to discord.py 2.x and OpenAI async SDK 2.x but its legacy NPC/Twitch/image features have **not** all been regression-tested. Requirements are in `requirements.txt`.
- `assistant_bootstrap.py` loads local `.env` with `load_dotenv(".env", override=True)` **before** importing `Ranni`, intentionally taking precedence over stale inherited environment variables.

## Confirmed working state
- Local `!pc status` from the Discord owner-only command successfully replies with the real Ping state (user confirmed Oct 24).
- `ranni_assistant/commands.py`: owner check via `RANNI_OWNER_DISCORD_ID`, command group `!pc`, status command.
- `ranni_assistant/pc_status.py`: async-to-thread, authenticated GET `/api/states/<entity_id>`; `on` -> ONLINE, `off` -> OFFLINE.
- Home Assistant Green: LAN address was `192.168.0.150:8123`, and PC ping entity `binary_sensor.192_168_0_44` (PC LAN `192.168.0.44`). These are environment-specific facts, not values to hardcode.
- Troubleshooting history: `HTTP 404` occurred until correct .env values were loaded; direct authenticated endpoint returned HTTP 200 and `on`; loading .env with override in bootstrap resolved the issue.
- Home Assistant runs Tailscale, and desktop uses Tailscale + Sunshine; laptop Moonlight + Tailscale. Remote Heroku access to HA is **not** currently established.
- Never ask for or print tokens: Discord, OpenAI and Home Assistant secrets were exposed in a screenshot earlier; user was advised to revoke/rotate them. Keep secrets out of code/logs/commits/chat.

## Workstation / environment hazards
- Two computers have different Python versions (laptop had 3.13, desktop 3.11). They use a OneDrive-synced project directory and previously had a broken `.venv` referencing the other computer's Python executable. Ideally move to per-device Git clones with independent local virtual environments. Never commit/sync virtualenv contents.
- Run commands using PowerShell syntax only when in PowerShell; CMD differs. For interactive python snippets, prefer standalone `python -c` or project-local scripts.
- No assumption that Ranni can wake its *own host* after it sleeps; while desktop sleeps the desktop-hosted Discord process is offline. Long-term wake needs an always-online bot deployment or separate relay.

## Wake milestone update (2026-10-24)
- Implemented owner-only `!pc wake` with rejected Discord arguments and a fixed `HOME_ASSISTANT_WAKE_ENTITY` script target.
- Shared REST transport in `ranni_assistant/home_assistant.py`: off-thread I/O, six-second socket timeout, eight-second wake caller deadline, rejected redirects, sanitized failures and no automatic retries. Status remains available.
- User created the Home Assistant script and confirmed the request-accepted reply after configuring the entity in local `.env` and restarting Ranni Dev. Updating `.env.example` alone does not configure the bot.
- API acceptance is confirmed; script trace success and physical wake from sleep remain unverified. Test the script from Home Assistant on another device while the gaming PC sleeps.
- Ranni Dev cannot receive commands while its own host sleeps. Always-on hosting and secure remote access remain future work; do not deploy or change production networking without authorization.
- Setup instructions: `RANNI_ASSISTANT_DEV.md`. Verification: `python -m unittest discover -s tests -v` (13 tests passed).

## Original wake implementation checklist (historical)
1. Inspect existing commands, HA integration, tests and user-defined configuration.
2. Confirm the Home Assistant **wake-on-LAN integration/service** is configured and enabled; when possible use a Home Assistant script for an explicitly allowlisted wake action instead of accepting arbitrary addresses or service arguments from Discord. The existing Ping sensor is only a status sensor and **cannot itself wake the PC**.
3. Add a new **owner-only** `!pc wake` command alongside `!pc status`. Keep the command nonblocking. POST to HA REST `/api/services/<domain>/<service>` authenticated with Bearer token and JSON for an explicitly configured service/script. Do not expose arbitrary HA service calls or arbitrary shell commands to Discord.
4. Favor `HOME_ASSISTANT_WAKE_ENTITY` for a fixed HA script entity, e.g. `script.wake_gaming_pc`, and call `POST /api/services/script/turn_on` with `{"entity_id": "..."}`. This requires user to create/configure the script in HA and ensures the Discord bot never receives a MAC address. Validate entity prefix, URL and secrets. Alternatively use HA WoL service only with explicit fixed MAC configured locally.
5. Reply with accurate wording: request accepted vs PC confirmed online. Optionally poll the existing Ping sensor with bounded retry and respond when online; never declare boot success merely on HTTP 200.
6. Keep existing `!pc status` behavior and branch isolation. Add unit tests (mock HTTP calls, unauthorized Discord user, invalid config, errors/timeouts). Update `.env.example` and `RANNI_ASSISTANT_DEV.md` to reflect real status and wake. Do not modify local `.env` or include token values.
7. Test `python -m unittest discover -s tests -v` and manually test `!pc wake` on the local development bot with user approval/when HA script is ready.
8. Important operational limitation: `Ranni Dev` currently runs on the gaming desktop. It cannot receive Discord wake commands while the computer is powered off. This first iteration proves the API action while running; later run the bot on an always-on platform with secure HA access (do **not** publicly expose HA unauthenticated).

## Security / quality
- Restrict wake command to configured owner ID; fail closed if missing.
- Use only fixed allowlisted home assistant script/entity; no user-supplied MACs, entity IDs, IPs, service names or arbitrary commands.
- Use short request timeouts and sanitized error messages, no auth header/log dump.
- Preserve `!pc status` and production behavior; add tests and documentation.
- Before touching `master`, production credentials, Tailscale routing or public ingress, get explicit approval.

## Useful environment variables (names ONLY)
`DISCORD_BOT_TOKEN`, `OPENAI_API_KEY`, `RANNI_OWNER_DISCORD_ID`, `RANNI_PC_NAME`, `HOME_ASSISTANT_URL`, `HOME_ASSISTANT_TOKEN`, `HOME_ASSISTANT_PC_ENTITY`; next `HOME_ASSISTANT_WAKE_ENTITY`.
