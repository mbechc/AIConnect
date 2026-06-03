# Prechecks

Run prechecks before activation, upgrades, or production-impacting operations.

## Repository Checks

- Confirm `backend/compose.yaml` exists.
- Confirm `backend/.env.example` exists.
- Confirm `bridge/platformio.ini` exists.
- Confirm `bridge/include/aiconnect_secrets.example.h` exists.
- Confirm `bridge/include/aiconnect_version.h` defines the firmware and contract versions.

## Backend Checks

- Confirm required `.env` values are not left as `change-me` before starting services.
- Confirm PostgreSQL is not intentionally exposed unless the customer has approved it.
- Confirm API and MCP bind hosts match the intended environment.
- Confirm MQTT TLS files exist before field use.
- Confirm Caddy and EMQX certificate responsibilities are understood.

## MCP Checks

- Confirm the MCP endpoint is reachable.
- Confirm the agent can inspect available MCP tools.
- Confirm at minimum that `platform_summary` is available before relying on MCP health.

## Bridge Checks

- Confirm target hardware is M5Atom Lite with M5Stack Atomic RS232 Base.
- Confirm provisioning credential is available through the approved secret path.
- Confirm `bridge/include/aiconnect_secrets.h` is local and not committed.
- Confirm the Bridge can be built with `./bridge/platformio.sh run`.

## Stop Conditions

Stop and ask for the next missing input when:

- The environment type is unknown.
- The secret store is unknown.
- The backend host or MCP endpoint is unknown.
- A required sensitive action lacks approval.
- Tool access is missing for a requested operation.
