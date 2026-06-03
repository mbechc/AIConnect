# Bridge Firmware Configuration

Before compiling the M5Atom Lite firmware, create this local file:

```text
include/aiconnect_secrets.h
```

Start from the template:

```text
include/aiconnect_secrets.example.h
```

Required definitions:

```cpp
#pragma once

#define AICONNECT_PROVISIONING_USERNAME "aiconnect-provisioning"
#define AICONNECT_PROVISIONING_PASSWORD "replace-with-installation-provisioning-password"
```

The provisioning password is burned into the compiled ESP32 image. It must match the backend installation's MQTT provisioning credential.

Security rules:

- Do not commit `include/aiconnect_secrets.h`.
- Do not show the provisioning password in UI or diagnostics.
- Do not print the provisioning password to serial logs.
- Rebuild and reflash Bridges after changing the provisioning password.
