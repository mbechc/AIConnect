# Bridge Claim Process

This document describes the Bridge side of AI Connect onboarding. It is aligned with the backend/controller contract for device-generated claim codes.

## Actors

- Bridge: the M5Atom Lite RS232 console bridge.
- Backend: the AI Connect controller and MQTT broker.
- Operator: an authenticated backend user or MCP agent acting under operator authority.

## Security Model

The Bridge identifies hardware, but it does not choose ownership.

- `device_id` and `efuse_mac` identify the physical Bridge.
- The claim code proves local/physical access to the Bridge setup UI.
- Backend operator authentication proves permission to assign the Bridge to an organisation/site.
- The selected organisation/site is supplied only by the backend operator.

The Bridge must not include organisation or site fields in onboarding payloads.

## Unclaimed MQTT Access

Before claim, the Bridge connects to the backend onboarding MQTT endpoint with a restricted provisioning credential configured for the deployment.

That credential is only allowed to:

- publish `aic/v1/onboarding/register`
- subscribe `aic/v1/onboarding/response/{device_id}`

The provisioning credential is managed at the installation level by the backend operator. It sits above organisations and sites. The provisioning credential is not an ownership secret. It only allows an unclaimed Bridge to ask the backend to create a pending onboarding registration.

## Claim Code Generation And Display

When the Bridge is unclaimed, it may generate a random short-lived claim code locally before it has backend connectivity. That local value is not operator-actionable yet.

The setup UI must not display the claim code as something for the operator to use until the Bridge has successfully connected to the backend onboarding MQTT endpoint and published the pending onboarding registration.

The code must be:

- random
- short-lived
- one-time-use after backend acceptance
- regenerated after expiry or factory reset

Before backend registration succeeds, the setup UI should show a state such as:

```text
Waiting for backend registration
```

After backend registration succeeds, the setup UI displays the claim code and a state such as:

```text
Ready for operator claim
```

At that point the operator can copy the claim code from the Bridge UI into the backend UI/API and assign the Bridge to the correct organisation/site.

If the Bridge is already claimed, the setup claim-code UI is not available. Claimed mode exposes only the status page and must not display `generating` or a stale claim code.

## Pending Registration

The Bridge publishes a pending onboarding registration:

```text
Topic: aic/v1/onboarding/register
```

```json
{
  "device_id": "...",
  "efuse_mac": "...",
  "claim_code": "...",
  "firmware_version": "...",
  "hardware_model": "m5atom-lite-rs232",
  "claim_code_expires_at": "... optional ISO8601"
}
```

If this publish succeeds, the Bridge may show the claim code in local setup UI. If the publish fails, the Bridge keeps retrying and continues to show a backend registration/connectivity state instead of showing an actionable claim code.

Backend requirements:

- Store only a hash of `claim_code`.
- Enforce backend-side expiry.
- Reject claimed or disabled devices.
- Allow revoked devices to re-onboard with a fresh valid claim code.
- Audit registration attempts and outcomes.

## Operator Claim

The operator enters the displayed claim code in the backend/MCP UI and selects the correct site.

The Bridge does not know or send the site.

The backend validates:

- pending registration exists
- claim code hash matches
- registration is pending and unexpired
- device is not claimed or disabled
- selected site is valid for the operator

If accepted, the backend generates unique per-device MQTT credentials and publishes them to the Bridge.

## Claim Response

The Bridge subscribes to:

```text
aic/v1/onboarding/response/{device_id}
```

Accepted response:

```json
{
  "status": "accepted",
  "device_id": "...",
  "efuse_mac": "...",
  "mqtt": {
    "host": "...",
    "port": 8883,
    "tls": true,
    "username": "...",
    "password": "...",
    "topic_prefix": "aic/v1",
    "status_topic": "...",
    "heartbeat_topic": "..."
  }
}
```

Rejected response:

```json
{
  "status": "rejected",
  "device_id": "...",
  "reason": "..."
}
```

On `accepted`, the Bridge stores the issued MQTT credentials and enters claimed mode.

On `rejected`, the Bridge remains unclaimed and shows a clear setup UI status.

On accepted claim, the Bridge clears the local claim code and claim-code registration state from persistent storage. The status-only claimed UI must not expose claim codes, provisioning credentials, or issued MQTT credentials.

## Claimed Mode

After successful claim, the Bridge reconnects with its issued per-device MQTT credential.

It publishes its own status and heartbeat topics and bridges serial session data under its own device topic scope only.

The backend derives online/offline state from `last_seen_at`, updated server-side whenever a valid device message is received.

## Revoked vs Disabled

`revoked` invalidates old issued credentials. It does not permanently block the hardware.

A factory-reset Bridge with a revoked backend record may be claimed again through the normal physical claim-code flow. The backend audit trail should preserve both the old revoke event and the new claim event.

`disabled` is an administrative block. Disabled devices must not be claimed again unless an operator explicitly changes the backend state.

## Factory Reset

On factory reset, the Bridge must erase:

- backend configuration
- local claim code
- issued MQTT credentials
- claimed state

After reboot, it returns to setup AP mode. It may generate a fresh local claim code, but it must only display that code to the operator after a pending onboarding registration has been successfully published to the backend.
