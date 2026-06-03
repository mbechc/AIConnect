# Add New Device

## Purpose

Guide onboarding and claim of a new AI Connect Bridge.

## When To Use

Use when the customer says "add a device", "claim a Bridge", or "connect a new serial bridge".

## Required Information

- Target organization and site.
- Confirmation that the hardware is M5Atom Lite with M5Stack Atomic RS232 Base.
- Backend/controller host.
- Whether firmware already has the correct provisioning credential.

## Preconditions

- Organization and site exist.
- Bridge can reach Wi-Fi and backend MQTT endpoint.
- Provisioning credential is configured in local ignored firmware secrets.

## Approval Required

Approval is required before claiming a device into a site, disabling a device, factory resetting a device, or opening serial sessions.

## Steps

1. Read `bridge/README.md` and `bridge/claim-process/README.md`.
2. Confirm target organization and site.
3. Confirm Bridge UI state.
4. If the Bridge shows `Authentication failed`, troubleshoot provisioning credentials without asking for secret values.
5. If the Bridge shows `Waiting for backend registration`, check MQTT/backend registration path.
6. If the Bridge shows `Ready for operator claim`, list pending onboarding registrations.
7. Ask approval to claim the matching registration into the selected site.
8. Claim the registration.
9. Validate claimed state and heartbeat.

## Validation

Confirm the device appears as claimed and `last_seen_at` updates from heartbeat or status messages.

## Failure Handling

If claim fails, check registration status, expiry, selected site, and device state. Do not retry destructive actions without approval.

## State Update

Record device ID, site, non-sensitive status, and validation evidence. Do not store claim codes or MQTT credentials.

## Completion Message

Summarize the device, assigned site, validation evidence, and any follow-up work.
