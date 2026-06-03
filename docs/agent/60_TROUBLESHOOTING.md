# Troubleshooting

Use this file when the customer reports errors, failed onboarding, missing devices, health failures, or serial-session issues.

## First Response

1. Identify the affected area: backend, MCP, MQTT, Bridge, claim flow, device presence, serial session, GitHub, or certificates.
2. Read the relevant README and runbook.
3. Ask for the exact error or observed state.
4. Check read-only evidence before proposing a change.

## Common AI Connect Problems

| Symptom | Likely area | First check |
|---|---|---|
| MCP unavailable | Backend or bind host | `backend/README.md` MCP endpoint and Compose config |
| Bridge shows `Authentication failed` | Provisioning MQTT credential | `bridge/include/aiconnect_secrets.h` local value and backend provisioning credential metadata |
| Bridge waits for backend registration | MQTT connectivity or backend worker | MQTT TLS endpoint, onboarding worker, pending registrations |
| No claim code visible | Registration has not succeeded or Bridge already claimed | Bridge UI state table in `bridge/claim-process/README.md` |
| Claim rejected | Registration/site/state mismatch | Pending registration status and selected site |
| Device not online | Heartbeat freshness | Device `last_seen_at`, MQTT auth/ACL, heartbeat topic |
| Serial session missing output | Device session path | Session state, tx/rx audit logs, device online state |

## Escalation Rules

Create or update a GitHub issue when:

- A step is blocked by missing tool access.
- A production-impacting risk is found.
- A repository capability is missing.
- Validation cannot prove success.
- A customer decision is required later.
