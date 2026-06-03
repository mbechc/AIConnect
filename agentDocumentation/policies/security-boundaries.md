# Security Boundaries

The repository must never contain secrets.

Do not commit:

- passwords
- API keys
- access tokens
- refresh tokens
- private keys
- recovery codes
- database passwords
- customer credentials
- production secrets
- claim codes
- MQTT passwords
- Wi-Fi passwords

If a secret is required, ask the customer to place it in the approved secret store or an approved ignored runtime file.

The agent may reference the name or location of a secret, but not the secret value.
