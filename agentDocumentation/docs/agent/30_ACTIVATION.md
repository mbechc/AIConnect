# Activation

Activation means preparing AI Connect so an operator or MCP-enabled agent can manage organizations, sites, pending Bridge onboarding registrations, device health, and serial sessions.

## Activation Order

1. Confirm environment type.
2. Confirm state files exist or create them from examples after approval.
3. Validate backend prerequisites.
4. Validate MCP access.
5. Configure installation settings if required.
6. Confirm or rotate installation provisioning credential only after approval.
7. Create organization and site if missing and approved.
8. Configure and build Bridge firmware with local ignored provisioning credentials.
9. Guide Bridge setup UI through backend registration.
10. Claim the pending onboarding registration into the selected site after approval.
11. Validate claimed heartbeat and device presence.

## Sensitive Actions

Ask for explicit approval before:

- starting or changing production backend services
- changing provisioning credentials
- exposing MCP, API, dashboard, or MQTT endpoints
- claiming a device into a site
- requesting factory reset
- opening or transmitting in a serial session

## Evidence Required

Do not mark activation complete until there is evidence for:

- Backend health or readiness.
- MCP tool availability or REST fallback availability.
- Organization and site existence.
- Bridge pending registration or claimed device record.
- Claimed device heartbeat or last-seen update.
