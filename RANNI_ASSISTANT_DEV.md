# Ranni Assistant development

Development branch: `feature/ranni-assistant`. Launch with `python assistant_bootstrap.py`
using the separate **Ranni Dev** Discord application. The production Procfile and
Heroku deployment are unchanged. The bootstrap loads `.env` before importing Ranni,
with local values taking precedence over inherited environment variables.

## Commands and configuration

Copy the variable names from `.env.example` into your local `.env`; never commit
or share secrets. Configure `RANNI_OWNER_DISCORD_ID` to your numeric Discord user ID.
Both commands fail closed when the owner ID is absent or does not match.

- `!pc status`: reads the real `HOME_ASSISTANT_PC_ENTITY` Ping binary sensor.
  `on` means ONLINE; `off` means OFFLINE; errors mean unknown. No Ping response
  does not distinguish sleep from a network failure.
- `!pc wake`: starts only `HOME_ASSISTANT_WAKE_ENTITY`, a fixed `script.*` entity.
  Arguments are rejected. No MAC, target, script variables or service name can be
  supplied through Discord. The bot does not need the PC's MAC address.

The existing `HOME_ASSISTANT_URL` and `HOME_ASSISTANT_TOKEN` are reused. Use an
HTTP(S) origin such as `http://YOUR_HOME_ASSISTANT_IP:8123` without credentials,
query parameters or a path. The token must be a valid Home Assistant long-lived
access token belonging to a user permitted to run the script. Never paste it into
Discord. Requests run in a worker thread with a six-second socket timeout; wake
also has an eight-second caller deadline. Redirects are rejected. No automatic
retry occurs: a failed or timed-out response may follow an action already accepted.

The fixed request is `POST /api/services/script/turn_on` with JSON
`{"entity_id": "script.wake_gaming_pc"}` (using your configured script ID).
Acceptance confirms only the API request; it does not confirm that the script
finished, that a packet was delivered, or that the PC booted. Check the script trace
in Home Assistant and then `!pc status`.

## Configure Home Assistant Green

The repository cannot establish which integrations/scripts are installed on your
Green. The existing Ping sensor only reads status; it cannot wake the PC.

1. In Home Assistant, open **Settings > Devices & services > Add integration**,
   choose **Wake on LAN**, and configure the gaming PC's wired network adapter.
   Enter its MAC address only in Home Assistant. On Windows, find it locally with
   `Get-NetAdapter` (Physical Address/MacAddress); do not paste the output into chat.
   Use the Ethernet adapter connected to the same LAN as Green. Configure a LAN
   broadcast address if your network requires one.
2. Find the created wake button under the integration's entities, or in
   **Developer tools > States**, filtering for `button.`. Copy its entity ID.
3. Open **Settings > Automations & scenes > Scripts > Add script > Create new
   script**. Add a **Button: Press** action targeting only that wake button.
   Save as **Wake Gaming PC**. Do not add script fields or caller-supplied targets.
   The script editor's YAML should look like the example below, replacing the
   placeholder button ID with the actual entity ID:

   ```yaml
   alias: Wake Gaming PC
   mode: single
   sequence:
     - action: button.press
       target:
         entity_id: button.YOUR_WAKE_BUTTON
   ```

4. Find the script in **Developer tools > States**, filtering for `script.` and
   matching its friendly name. Copy the actual entity ID; the display name does
   not guarantee `script.wake_gaming_pc`. Put that ID in your local `.env`:
   `HOME_ASSISTANT_WAKE_ENTITY=script.wake_gaming_pc` (replace if different).
5. Alternatively, if the `wake_on_lan.send_magic_packet` action is already enabled,
   create a script with that action and a fixed MAC in Home Assistant's script
   editor. For action-only YAML setup, add `wake_on_lan:` to HA's
   `configuration.yaml`, check configuration, and restart HA. Select the action
   in **Developer tools > Actions** to confirm it exists. Keep its MAC and optional
   broadcast settings entirely in HA; the bot still calls only the fixed script.
6. Enable Wake-on-LAN in the PC's firmware and Ethernet driver/power settings.
   Test the script directly from Home Assistant using another device while the
   PC sleeps. Check the script trace if it fails; API acceptance alone cannot
   detect firmware, driver, broadcast, or script execution failures.

References: [Wake on LAN](https://www.home-assistant.io/integrations/wake_on_lan/),
[Scripts](https://www.home-assistant.io/integrations/script/), and
[REST actions](https://contributors.home-assistant.io/core/internals/rest-api/#post-apiservicesdomainservice).

## Tests and manual validation

Run `python -m unittest discover -s tests -v`. Tests use mocked HTTP and Discord
contexts and require no tokens, network or running bot. They cover status, owner
access, argument rejection, fixed POST/authentication, config validation, sanitized
failures, deadlines, off-thread I/O, and redirect rejection.

For a live test after configuring the script, restart **Ranni Dev** with
`python assistant_bootstrap.py`, run `!pc status`, then `!pc wake` as the configured
owner with no arguments. Check HA's script trace and run `!pc status` again. Test
from another Discord account to confirm denial. Use only the development token.
No live wake action was sent during repository implementation. The user subsequently
created the HA script, configured the wake entity in local `.env`, restarted Ranni
Dev, and confirmed the request-accepted Discord response. Physical wake and script
trace verification remain pending.

**Host limitation:** Ranni Dev currently runs on the gaming PC. Once the PC is
asleep, the bot cannot receive Discord commands. Test wake from Home Assistant on
another device first; an awake-host Discord test proves API dispatch. An always-on
assistant with secure remote access is a later milestone. Do not expose Home
Assistant publicly without authentication or change production networking here.
