#pragma once

// Copy this file to bridge/include/aiconnect_secrets.h before compiling firmware.
// The password is burned into the compiled ESP32 image and must match the
// backend installation's MQTT provisioning credential.
#define AICONNECT_PROVISIONING_USERNAME "aiconnect-provisioning"
#define AICONNECT_PROVISIONING_PASSWORD "replace-with-installation-provisioning-password"
