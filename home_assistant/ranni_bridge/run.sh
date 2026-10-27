#!/command/with-contenv bashio
# Ranni Bridge v0.4.0: push PC state and poll for a single allowed wake action.
# Configure bridge_url as https://YOUR-APP.herokuapp.com/bridge/status.
set -u
BRIDGE_URL="$(bashio::config 'bridge_url')"
BRIDGE_SECRET="$(bashio::config 'bridge_secret')"
WAKE_BUTTON="button.wake_on_lan_3c_18_a0_1e_e6_1a"
SENSOR="binary_sensor.192_168_0_44"
if [[ "$BRIDGE_URL" != https://*/bridge/status || -z "$BRIDGE_SECRET" ]]; then
  bashio::log.error "Configure HTTPS bridge_url ending in /bridge/status and bridge_secret"
  exit 1
fi
NEXT_URL="${BRIDGE_URL%/bridge/status}/bridge/next"
bashio::log.info "Ranni Bridge 0.4.0 started"
while true; do
  sensor_response="$(curl --silent --show-error --fail --max-time 10 --noproxy '*' \
    -H "Authorization: Bearer ${SUPERVISOR_TOKEN}" \
    "http://supervisor/core/api/states/${SENSOR}")"
  if [[ $? -eq 0 ]]; then
    state="$(printf '%s' "$sensor_response" | grep -oE '"state"[[:space:]]*:[[:space:]]*"[^"]+"' | head -1 | cut -d '"' -f 4)"
    case "$state" in
      on|off|unknown|unavailable)
        status_code="$(curl --silent --show-error --max-time 10 \
          -o /dev/null -w '%{http_code}' -X POST \
          -H "Authorization: Bearer ${BRIDGE_SECRET}" \
          -H 'Content-Type: application/json' \
          --data "{\"state\":\"${state}\"}" "$BRIDGE_URL")"
        if [[ "$status_code" == 200 ]]; then
          bashio::log.info "PC status sent: $state"
        else
          bashio::log.warning "Status delivery HTTP $status_code"
        fi
        ;;
      *) bashio::log.warning "Unexpected sensor state" ;;
    esac
  else
    state="unknown"
    bashio::log.warning "Home Assistant sensor not readable"
  fi

  # Poll only a fixed, authenticated endpoint. No arbitrary commands.
  next_file="$(mktemp)"
  poll_code="$(curl --silent --show-error --max-time 10 -o "$next_file" -w '%{http_code}' \
    -H "Authorization: Bearer ${BRIDGE_SECRET}" "$NEXT_URL")"
  if [[ "$poll_code" == 200 ]] && grep -Eq '"action"[[:space:]]*:[[:space:]]*"wake"' "$next_file"; then
    if [[ "$state" == "off" ]]; then
      action_code="$(curl --silent --show-error --max-time 10 -o /dev/null -w '%{http_code}' \
        -X POST -H "Authorization: Bearer ${SUPERVISOR_TOKEN}" \
        -H 'Content-Type: application/json' \
        --data "{\"entity_id\":\"${WAKE_BUTTON}\"}" \
        'http://supervisor/core/api/services/button/press')"
      if [[ "$action_code" == "200" ]]; then
        bashio::log.info "Wake-on-LAN button pressed (boot not yet confirmed)"
      else
        bashio::log.warning "Wake action failed HTTP $action_code"
      fi
    else
      bashio::log.info "Wake skipped: last known PC state is not off"
    fi
  elif [[ "$poll_code" != 200 ]]; then
    bashio::log.warning "Wake polling HTTP $poll_code"
  fi
  rm -f "$next_file"
  sleep 30
done
