# Validation

Use validation after activation, change execution, troubleshooting, or device onboarding.

## Standard Validation Areas

| Area | Expected evidence |
|---|---|
| Backend health | `/health`, `/ready`, or MCP `platform_summary` |
| MCP access | Reachable MCP endpoint and visible AI Connect tools |
| MQTT onboarding | Pending registration or successful claim response |
| Device presence | Device appears through MCP/API with recent `last_seen_at` |
| Serial audit | Session lifecycle and tx/rx logs are present after a serial test |
| Security posture | Secrets are absent from Git and sensitive endpoints are protected |

## Validation Rules

- Use MCP tools when available.
- Use REST API checks when MCP tools are unavailable.
- Do not ask for secret values.
- Do not send serial commands to customer equipment without approval.
- Record unresolved validation gaps in a GitHub issue if GitHub issue tools are available.
