Place MQTT TLS certificate files here for EMQX:

- `ca.crt`
- `server.crt`
- `server.key`

EMQX also expects these default names for its secure WebSocket listener:

- `cacert.pem`
- `cert.pem`
- `key.pem`

For the PoC, these can be copied from the Let's Encrypt certificate for
`mqtts.itego.dk`, or replaced with a dedicated certificate issued for MQTT.

The HTTP API certificate is managed separately by Caddy.
