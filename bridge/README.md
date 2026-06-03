# AI Connect Bridge

The AI Connect Bridge firmware runs on an M5Atom Lite with an M5Stack Atomic RS232 Base. It connects to a serial console port, joins Wi-Fi, and maintains an outbound MQTT-over-TLS connection to the AI Connect backend.

The Bridge identifies itself with hardware identity such as `device_id` and eFuse MAC, but it never chooses organisation or site ownership. The backend operator assigns that during claim.

## Folder Layout

```text
bridge/
  platformio.ini                 PlatformIO build/upload configuration
  platformio.sh                  Wrapper that runs PlatformIO inside this folder
  src/main.cpp                   Firmware source
  include/aiconnect_version.h    Firmware, contract, and hardware constants
  include/aiconnect_secrets.h    Local provisioning credential, not committed
  include/aiconnect_secrets.example.h
  claim-process/README.md        Detailed onboarding/claim contract
  firmware-configuration.md      Provisioning credential notes
```

Generated PlatformIO files also live inside `bridge/`:

```text
bridge/.pio/
bridge/.platformio-core/
```

## Claim Process

Read the claim workflow before changing onboarding behavior:

[claim-process/README.md](claim-process/README.md)

Short version:

- unclaimed Bridge uses provisioning MQTT credentials
- Bridge registers a locally generated claim code with the backend
- local UI shows the claim code only after backend registration succeeds
- operator enters the claim code in the backend and assigns organisation/site
- backend returns per-device MQTT credentials
- Bridge enters claimed mode and starts heartbeat/status/session behavior

## Configure Secrets

Before building, create the local secrets file from the template:

```sh
cp bridge/include/aiconnect_secrets.example.h bridge/include/aiconnect_secrets.h
```

Set the provisioning credential:

```cpp
#define AICONNECT_PROVISIONING_USERNAME "aiconnect-provisioning"
#define AICONNECT_PROVISIONING_PASSWORD "change-me-provisioning-mqtt-password"
```

The password is burned into the compiled ESP32 image. If the backend provisioning password changes, rebuild and reflash the Bridge.

## Versioning

Firmware version is defined here:

```text
bridge/include/aiconnect_version.h
```

Before building a new release, update:

```cpp
#define AICONNECT_FIRMWARE_VERSION "0.2.9"
```

Keep `AICONNECT_CONTRACT_VERSION` aligned with the backend MQTT contract, currently:

```cpp
#define AICONNECT_CONTRACT_VERSION "aic/v1"
```

## Build

From the repository root:

```sh
./bridge/platformio.sh run
```

The wrapper automatically changes into `bridge/`. To run it from outside the repository root, use the absolute path:

```sh
/Users/morchris/Documents/Codex/AI\ Connect/bridge/platformio.sh run
```

Build output is written under:

```text
bridge/.pio/build/m5stack-atom/
```

Important files:

```text
bridge/.pio/build/m5stack-atom/firmware.bin
bridge/.pio/build/m5stack-atom/firmware.elf
```

## Find The ESP32 Serial Port

On macOS, connect the M5Atom Lite by USB-C and list serial devices:

```sh
ls /dev/cu.*
```

This project currently uses this port in `bridge/platformio.ini`:

```ini
upload_port = /dev/cu.usbserial-6D528A1346
monitor_port = /dev/cu.usbserial-6D528A1346
```

If your ESP32 appears on another port, either update `bridge/platformio.ini` or pass the port at upload time:

```sh
./bridge/platformio.sh run -t upload --upload-port /dev/cu.usbserial-XXXX
```

## Flash The ESP32

Build and flash:

```sh
./bridge/platformio.sh run -t upload
```

Serial monitor:

```sh
./bridge/platformio.sh device monitor
```

Exit the serial monitor with `Ctrl-C`.

## Multiple ESP32 Boards Or Image Variants

Use one PlatformIO environment per board/image variant in `bridge/platformio.ini`.

Current environment:

```ini
[env:m5stack-atom]
platform = espressif32
board = m5stack-atom
framework = arduino
```

For another board or firmware image, add a new environment:

```ini
[env:m5stack-atom-lab]
platform = espressif32
board = m5stack-atom
framework = arduino
upload_port = /dev/cu.usbserial-LAB
monitor_port = /dev/cu.usbserial-LAB
build_flags =
  -DAICONNECT_IMAGE_FLAVOR=\"lab\"
```

Build a specific environment:

```sh
./bridge/platformio.sh run -e m5stack-atom-lab
```

Flash a specific environment:

```sh
./bridge/platformio.sh run -e m5stack-atom-lab -t upload
```

Recommended variant rules:

- Keep production and lab provisioning credentials separate.
- Put shared constants in `bridge/include/aiconnect_version.h`.
- Put per-installation secrets in `bridge/include/aiconnect_secrets.h`.
- Do not commit compiled images unless there is a deliberate release process.
- Name environments by hardware and purpose, for example `m5stack-atom-prod`, `m5stack-atom-lab`, or `m5stack-atom-dev`.

## Release Checklist

1. Update `AICONNECT_FIRMWARE_VERSION`.
2. Confirm `bridge/include/aiconnect_secrets.h` matches the target backend.
3. Build with `./bridge/platformio.sh run`.
4. Flash with `./bridge/platformio.sh run -t upload`.
5. Open serial monitor with `./bridge/platformio.sh device monitor`.
6. Confirm AP SSID appears as `AICONNECT_<device suffix>` after factory reset.
7. Configure Wi-Fi and controller in the local setup UI.
8. Confirm the UI reaches `Ready for operator claim`.
9. Confirm the claim code appears in Identity and Diagnostics.
10. Claim the Bridge in the backend.
11. Confirm claimed status, heartbeat, and last successful backend contact.
12. Commit the source/docs changes after a successful build.

## Factory Reset

Hold the M5Atom button for 15 seconds to wipe local state. Factory reset clears:

- Wi-Fi credentials
- backend/controller host
- local claim code
- claimed state
- issued MQTT username/password
- topic/session state

After reboot, the Bridge returns to setup AP mode.

## Security Notes

- The Bridge must never send organisation or site assignment.
- The local claim code proves physical/local access to the Bridge UI.
- The authenticated backend operator decides organisation/site.
- Claim codes and issued MQTT passwords must not be logged.
- Factory reset must erase Wi-Fi/backend setup, claim code, issued MQTT credentials, and claimed state.
