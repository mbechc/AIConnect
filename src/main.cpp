#include <Arduino.h>
#include <ArduinoJson.h>
#include <DNSServer.h>
#include <Preferences.h>
#include <PubSubClient.h>
#include <WebServer.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <base64.h>
#include "aiconnect_version.h"
#include <mbedtls/base64.h>

namespace {
constexpr uint8_t kLedPin = 27;
constexpr uint8_t kButtonPin = 39;
constexpr uint8_t kDnsPort = 53;
constexpr uint8_t kRs232RxPin = 22;
constexpr uint8_t kRs232TxPin = 19;
constexpr uint32_t kWifiConnectTimeoutMs = 15000;
constexpr uint32_t kMqttKeepAliveSeconds = 45;
constexpr uint32_t kMqttReconnectMinMs = 5000;
constexpr uint32_t kMqttReconnectMaxMs = 60000;
constexpr uint32_t kHeartbeatMs = 30000;
constexpr uint32_t kClaimRetryMs = 10000;
constexpr uint32_t kResetHoldMs = 15000;
constexpr const char *kTopicPrefix = AICONNECT_CONTRACT_VERSION;
constexpr const char *kFirmwareVersion = AICONNECT_FIRMWARE_VERSION;
constexpr const char *kHardwareModel = AICONNECT_HARDWARE_MODEL;

enum class Mode { Setup, Claimed };
enum class LedState { Setup, Wifi, Claiming, Online, Offline, Error, Reset };

struct ControllerEndpoint {
  String host;
  uint16_t port = 8883;
  bool tls = true;
  bool valid = false;
};

DNSServer dnsServer;
WebServer server(80);
Preferences preferences;
WiFiClientSecure secureClient;
PubSubClient mqttClient(secureClient);

Mode mode = Mode::Setup;
LedState ledState = LedState::Setup;
String deviceId;
String apSsid;
String savedSsid;
String savedPass;
String savedController;
String savedClaimCode;
String savedCaPem;
String claimStatus = "Not claimed";
String mqttHost;
String mqttUsername;
String mqttPassword;
String mqttTopicPrefix = kTopicPrefix;
uint16_t mqttPort = 8883;
bool mqttTls = true;
bool claimed = false;
bool serialOpen = false;
String activeSessionId;
String backendConnectionState = "Claim required";
String lastMqttError = "none";
uint32_t lastBlinkMs = 0;
uint32_t lastWifiAttemptMs = 0;
uint32_t lastMqttAttemptMs = 0;
uint32_t mqttReconnectDelayMs = kMqttReconnectMinMs;
uint32_t lastBackendContactMs = 0;
uint32_t lastHeartbeatMs = 0;
uint32_t lastClaimPublishMs = 0;
uint32_t heartbeatSeq = 0;
uint32_t resetStartedMs = 0;
bool ledOn = false;
bool wasMqttConnected = false;

String htmlEscape(const String &value) {
  String escaped;
  escaped.reserve(value.length());
  for (char ch : value) {
    if (ch == '&') escaped += F("&amp;");
    else if (ch == '<') escaped += F("&lt;");
    else if (ch == '>') escaped += F("&gt;");
    else if (ch == '"') escaped += F("&quot;");
    else escaped += ch;
  }
  return escaped;
}

String jsonEscape(const String &value) {
  String escaped;
  escaped.reserve(value.length());
  for (char ch : value) {
    if (ch == '"' || ch == '\\') {
      escaped += '\\';
    }
    if (ch >= 0 && ch < 32) {
      continue;
    }
    escaped += ch;
  }
  return escaped;
}

String buildDeviceId() {
  uint64_t mac = ESP.getEfuseMac();
  char id[13];
  snprintf(id, sizeof(id), "%04X%08X", static_cast<uint16_t>(mac >> 32),
           static_cast<uint32_t>(mac));
  return String(id);
}

String claimResponseTopic() {
  return String(kTopicPrefix) + "/claim/response/" + deviceId;
}

String claimRequestTopic() {
  return String(kTopicPrefix) + "/claim/request";
}

String deviceTopic(const String &suffix) {
  return mqttTopicPrefix + "/devices/" + deviceId + "/" + suffix;
}

String commandTopic(const String &command) {
  return mqttTopicPrefix + "/devices/" + deviceId + "/commands/" + command;
}

String sessionPrefix() {
  return mqttTopicPrefix + "/devices/" + deviceId + "/sessions/";
}

String mqttStateText(int state) {
  switch (state) {
    case MQTT_CONNECTION_TIMEOUT: return "connection timeout";
    case MQTT_CONNECTION_LOST: return "connection lost";
    case MQTT_CONNECT_FAILED: return "connect failed";
    case MQTT_DISCONNECTED: return "disconnected";
    case MQTT_CONNECTED: return "connected";
    case MQTT_CONNECT_BAD_PROTOCOL: return "bad protocol";
    case MQTT_CONNECT_BAD_CLIENT_ID: return "bad client id";
    case MQTT_CONNECT_UNAVAILABLE: return "server unavailable";
    case MQTT_CONNECT_BAD_CREDENTIALS: return "bad credentials";
    case MQTT_CONNECT_UNAUTHORIZED: return "unauthorized";
    default: return "mqtt state " + String(state);
  }
}

void markBackendContact() {
  lastBackendContactMs = millis();
  lastMqttError = "none";
  backendConnectionState = "Connected to Backend";
}

String lastBackendContactText() {
  if (lastBackendContactMs == 0) {
    return "never";
  }
  uint32_t ageSeconds = (millis() - lastBackendContactMs) / 1000;
  if (ageSeconds == 0) {
    return "just now";
  }
  return String(ageSeconds) + "s ago";
}

void refreshMqttConnectionState() {
  bool connectedNow = mqttClient.connected();
  if (wasMqttConnected && !connectedNow) {
    backendConnectionState = "Disconnected from Backend";
    lastMqttError = mqttStateText(mqttClient.state());
    ledState = LedState::Offline;
  }
  wasMqttConnected = connectedNow;
}

bool parseController(const String &raw, ControllerEndpoint &endpoint) {
  String value = raw;
  value.trim();
  endpoint = ControllerEndpoint{};
  if (value.isEmpty()) {
    return false;
  }

  if (value.startsWith("mqtts://")) {
    endpoint.tls = true;
    value.remove(0, 8);
  } else if (value.startsWith("mqtt://")) {
    endpoint.tls = false;
    value.remove(0, 7);
  }

  int slash = value.indexOf('/');
  if (slash >= 0) {
    value = value.substring(0, slash);
  }
  int colon = value.lastIndexOf(':');
  if (colon > 0) {
    endpoint.host = value.substring(0, colon);
    endpoint.port = static_cast<uint16_t>(value.substring(colon + 1).toInt());
  } else {
    endpoint.host = value;
    endpoint.port = endpoint.tls ? 8883 : 1883;
  }
  endpoint.host.trim();
  endpoint.valid = endpoint.host.length() > 0 && endpoint.port > 0;
  return endpoint.valid;
}

void setLed(uint8_t red, uint8_t green, uint8_t blue) {
  neopixelWrite(kLedPin, red, green, blue);
}

void loadConfig() {
  preferences.begin("aiconnect", true);
  savedSsid = preferences.getString("wifi_ssid", "");
  savedPass = preferences.getString("wifi_pass", "");
  savedController = preferences.getString("controller", "");
  savedClaimCode = preferences.getString("claim_code", "");
  savedCaPem = preferences.getString("mqtt_ca", "");
  claimStatus = preferences.getString("claim_status", "Not claimed");
  claimed = preferences.getBool("claimed", false);
  mqttHost = preferences.getString("mqtt_host", "");
  mqttPort = preferences.getUShort("mqtt_port", 8883);
  mqttTls = preferences.getBool("mqtt_tls", true);
  mqttUsername = preferences.getString("mqtt_user", "");
  mqttPassword = preferences.getString("mqtt_pass", "");
  mqttTopicPrefix = preferences.getString("topic_prefix", kTopicPrefix);
  preferences.end();
}

void saveText(const char *key, const String &value) {
  preferences.begin("aiconnect", false);
  preferences.putString(key, value);
  preferences.end();
}

void saveClaimStatus(const String &value) {
  claimStatus = value;
  saveText("claim_status", value);
  if (value.startsWith("Rejected:")) {
    backendConnectionState = "Claim rejected";
  }
}

void wipeDeviceState() {
  backendConnectionState = "Factory reset requested";
  claimStatus = "Factory reset requested";
  ledState = LedState::Reset;
  preferences.begin("aiconnect", false);
  preferences.clear();
  preferences.end();
  mqttClient.disconnect();
  WiFi.disconnect(true, true);
  delay(100);
  ESP.restart();
}

void connectWifiIfNeeded() {
  if (savedSsid.isEmpty() || WiFi.status() == WL_CONNECTED) {
    return;
  }
  uint32_t now = millis();
  if (lastWifiAttemptMs != 0 && now - lastWifiAttemptMs < kWifiConnectTimeoutMs) {
    return;
  }
  lastWifiAttemptMs = now;
  ledState = LedState::Wifi;
  WiFi.begin(savedSsid.c_str(), savedPass.c_str());
}

void configureTls() {
  if (savedCaPem.length() > 0) {
    secureClient.setCACert(savedCaPem.c_str());
  } else {
    secureClient.setInsecure();
  }
}

void saveAcceptedClaim(JsonDocument &doc) {
  JsonObject mqtt = doc["mqtt"];
  preferences.begin("aiconnect", false);
  preferences.putBool("claimed", true);
  preferences.putString("claim_status", "Accepted");
  preferences.putString("mqtt_host", mqtt["host"].as<const char *>());
  preferences.putUShort("mqtt_port", mqtt["port"].as<uint16_t>());
  preferences.putBool("mqtt_tls", mqtt["tls"].as<bool>());
  preferences.putString("mqtt_user", mqtt["username"].as<const char *>());
  preferences.putString("mqtt_pass", mqtt["password"].as<const char *>());
  preferences.putString("topic_prefix", mqtt["topic_prefix"].as<const char *>());
  preferences.remove("claim_code");
  preferences.end();
}

String claimPayload() {
  JsonDocument doc;
  doc["device_id"] = deviceId;
  doc["efuse_mac"] = deviceId;
  doc["claim_code"] = savedClaimCode;
  doc["firmware_version"] = kFirmwareVersion;
  doc["hardware_model"] = kHardwareModel;
  String payload;
  serializeJson(doc, payload);
  return payload;
}

void publishStatus(const char *state) {
  if (!mqttClient.connected()) {
    return;
  }
  JsonDocument doc;
  doc["device_id"] = deviceId;
  doc["state"] = state;
  doc["firmware_version"] = kFirmwareVersion;
  doc["hardware_model"] = kHardwareModel;
  doc["serial_open"] = serialOpen;
  doc["uptime_ms"] = millis();
  String payload;
  serializeJson(doc, payload);
  if (mqttClient.publish(deviceTopic("status").c_str(), payload.c_str(), true)) {
    markBackendContact();
  }
}

void publishHeartbeat() {
  JsonDocument doc;
  doc["device_id"] = deviceId;
  doc["seq"] = ++heartbeatSeq;
  doc["uptime_ms"] = millis();
  doc["wifi_rssi"] = WiFi.RSSI();
  doc["firmware_version"] = kFirmwareVersion;
  doc["state"] = "claimed";
  String payload;
  serializeJson(doc, payload);
  if (mqttClient.publish(deviceTopic("heartbeat").c_str(), payload.c_str(), false)) {
    markBackendContact();
  }
}

void publishFactoryResetAck(const String &reason) {
  if (!mqttClient.connected()) {
    return;
  }
  JsonDocument doc;
  doc["device_id"] = deviceId;
  doc["event"] = "factory_reset_ack";
  doc["reason"] = reason;
  doc["uptime_ms"] = millis();
  String payload;
  serializeJson(doc, payload);
  mqttClient.publish(deviceTopic("events").c_str(), payload.c_str(), false);
}

bool decodeBase64(const String &encoded, uint8_t *out, size_t outSize, size_t &written) {
  written = 0;
  return mbedtls_base64_decode(out, outSize, &written,
                               reinterpret_cast<const unsigned char *>(encoded.c_str()),
                               encoded.length()) == 0;
}

void publishSerialRx() {
  if (!serialOpen || activeSessionId.isEmpty() || !mqttClient.connected()) {
    return;
  }

  uint8_t buffer[192];
  size_t count = 0;
  while (Serial2.available() && count < sizeof(buffer)) {
    buffer[count++] = static_cast<uint8_t>(Serial2.read());
  }
  if (count == 0) {
    return;
  }

  JsonDocument doc;
  doc["device_id"] = deviceId;
  doc["session_id"] = activeSessionId;
  doc["data_base64"] = base64::encode(buffer, count);
  doc["byte_count"] = count;
  String payload;
  serializeJson(doc, payload);
  String topic = sessionPrefix() + activeSessionId + "/rx";
  if (mqttClient.publish(topic.c_str(), payload.c_str(), false)) {
    markBackendContact();
  }
}

String topicAction(const String &topic, String &sessionId) {
  String prefix = sessionPrefix();
  if (!topic.startsWith(prefix)) {
    return "";
  }
  String rest = topic.substring(prefix.length());
  int slash = rest.indexOf('/');
  if (slash <= 0) {
    return "";
  }
  sessionId = rest.substring(0, slash);
  return rest.substring(slash + 1);
}

void handleSessionMessage(const String &topic, byte *payload, unsigned int length) {
  String sessionId;
  String action = topicAction(topic, sessionId);
  if (sessionId.isEmpty() || action.isEmpty()) {
    return;
  }

  JsonDocument doc;
  DeserializationError err = deserializeJson(doc, payload, length);
  if (action == "open") {
    int baud = doc["baud"].as<int>();
    if (baud <= 0) {
      baud = 9600;
    }
    Serial2.begin(baud, SERIAL_8N1, kRs232RxPin, kRs232TxPin);
    activeSessionId = sessionId;
    serialOpen = true;
    String openedTopic = sessionPrefix() + sessionId + "/opened";
    if (mqttClient.publish(openedTopic.c_str(), "{\"status\":\"opened\"}", false)) {
      markBackendContact();
    }
    publishStatus("serial-open");
  } else if (action == "tx" && serialOpen && sessionId == activeSessionId) {
    if (err) {
      Serial2.write(payload, length);
      return;
    }
    String encoded = doc["data_base64"].as<String>();
    if (encoded.isEmpty()) {
      String data = doc["data"].as<String>();
      Serial2.write(reinterpret_cast<const uint8_t *>(data.c_str()), data.length());
      return;
    }
    uint8_t decoded[256];
    size_t written = 0;
    if (decodeBase64(encoded, decoded, sizeof(decoded), written)) {
      Serial2.write(decoded, written);
    }
  } else if (action == "close" && serialOpen && sessionId == activeSessionId) {
    Serial2.end();
    serialOpen = false;
    activeSessionId = "";
    String closedTopic = sessionPrefix() + sessionId + "/closed";
    if (mqttClient.publish(closedTopic.c_str(), "{\"status\":\"closed\"}", false)) {
      markBackendContact();
    }
    publishStatus("serial-closed");
  }
}

void handleFactoryResetMessage(byte *payload, unsigned int length) {
  JsonDocument doc;
  DeserializationError err = deserializeJson(doc, payload, length);
  if (err) {
    lastMqttError = "invalid factory reset payload";
    return;
  }

  String command = doc["command"].as<String>();
  String payloadDeviceId = doc["device_id"].as<String>();
  if (command != "factory_reset") {
    lastMqttError = "ignored factory reset: invalid command";
    return;
  }
  if (payloadDeviceId != deviceId) {
    lastMqttError = "ignored factory reset: device_id mismatch";
    return;
  }

  String reason = doc["reason"].as<String>();
  backendConnectionState = "Factory reset requested";
  publishFactoryResetAck(reason);
  delay(250);
  wipeDeviceState();
}

void mqttCallback(char *topicRaw, byte *payload, unsigned int length) {
  markBackendContact();
  String topic(topicRaw);
  if (mode == Mode::Setup && topic == claimResponseTopic()) {
    JsonDocument doc;
    DeserializationError err = deserializeJson(doc, payload, length);
    if (err) {
      saveClaimStatus("Rejected: invalid claim response");
      lastMqttError = "invalid claim response";
      ledState = LedState::Error;
      return;
    }
    String status = doc["status"].as<String>();
    if (status == "accepted") {
      saveAcceptedClaim(doc);
      delay(250);
      ESP.restart();
    }
    String reason = doc["reason"].as<String>();
    lastMqttError = reason.length() ? reason : String("claim rejected");
    saveClaimStatus("Rejected: " + (reason.length() ? reason : String("unknown")));
    ledState = LedState::Error;
    return;
  }
  if (mode == Mode::Claimed) {
    if (topic == commandTopic("factory-reset")) {
      handleFactoryResetMessage(payload, length);
      return;
    }
    handleSessionMessage(topic, payload, length);
  }
}

bool connectMqtt(const ControllerEndpoint &endpoint, bool bootstrap) {
  if (mqttClient.connected()) {
    return true;
  }
  uint32_t now = millis();
  if (lastMqttAttemptMs != 0 && now - lastMqttAttemptMs < mqttReconnectDelayMs) {
    return false;
  }
  lastMqttAttemptMs = now;
  backendConnectionState = "Connecting to Backend";
  configureTls();
  mqttClient.setServer(endpoint.host.c_str(), endpoint.port);
  mqttClient.setCallback(mqttCallback);
  mqttClient.setBufferSize(1536);
  mqttClient.setKeepAlive(kMqttKeepAliveSeconds);
  mqttClient.setSocketTimeout(15);

  bool ok = false;
  if (bootstrap) {
    ok = mqttClient.connect(deviceId.c_str());
  } else {
    ok = mqttClient.connect(deviceId.c_str(), mqttUsername.c_str(), mqttPassword.c_str());
  }
  if (!ok) {
    int state = mqttClient.state();
    lastMqttError = mqttStateText(state);
    backendConnectionState = "Disconnected from Backend";
    mqttReconnectDelayMs = min<uint32_t>(mqttReconnectDelayMs * 2, kMqttReconnectMaxMs);
    ledState = LedState::Offline;
    return false;
  }

  wasMqttConnected = true;
  mqttReconnectDelayMs = kMqttReconnectMinMs;
  markBackendContact();
  if (bootstrap) {
    if (!mqttClient.subscribe(claimResponseTopic().c_str(), 1)) {
      lastMqttError = "claim response subscribe failed";
      backendConnectionState = "Disconnected from Backend";
      return false;
    }
  } else {
    String subscribeTopic = sessionPrefix() + "+/+";
    if (!mqttClient.subscribe(subscribeTopic.c_str(), 1)) {
      lastMqttError = "session subscribe failed";
      backendConnectionState = "Disconnected from Backend";
      return false;
    }
    if (!mqttClient.subscribe(commandTopic("factory-reset").c_str(), 1)) {
      lastMqttError = "factory reset subscribe failed";
      backendConnectionState = "Disconnected from Backend";
      return false;
    }
    publishStatus("online");
  }
  ledState = bootstrap ? LedState::Claiming : LedState::Online;
  return true;
}

void runClaimLoop() {
  if (savedController.isEmpty()) {
    backendConnectionState = "Backend not configured";
    return;
  }
  if (savedClaimCode.isEmpty()) {
    backendConnectionState = "Claim required";
    return;
  }
  if (WiFi.status() != WL_CONNECTED) {
    backendConnectionState = "Connecting to Backend";
    return;
  }
  ControllerEndpoint endpoint;
  if (!parseController(savedController, endpoint) || !endpoint.tls) {
    saveClaimStatus("Controller must be mqtts://host:port");
    backendConnectionState = "Backend not configured";
    lastMqttError = "controller must be mqtts://host:port";
    ledState = LedState::Error;
    return;
  }
  if (!connectMqtt(endpoint, true)) {
    return;
  }

  uint32_t now = millis();
  if (lastClaimPublishMs == 0 || now - lastClaimPublishMs >= kClaimRetryMs) {
    lastClaimPublishMs = now;
    String payload = claimPayload();
    if (mqttClient.publish(claimRequestTopic().c_str(), payload.c_str(), false)) {
      markBackendContact();
      saveClaimStatus("Claim request sent");
      backendConnectionState = "Connecting to Backend";
    } else {
      lastMqttError = "claim request publish failed";
      backendConnectionState = "Disconnected from Backend";
    }
  }
}

void runClaimedLoop() {
  connectWifiIfNeeded();
  if (WiFi.status() != WL_CONNECTED) {
    ledState = LedState::Wifi;
    backendConnectionState = "Connecting to Backend";
    return;
  }
  ControllerEndpoint endpoint;
  endpoint.host = mqttHost;
  endpoint.port = mqttPort;
  endpoint.tls = mqttTls;
  endpoint.valid = mqttHost.length() > 0;
  if (!endpoint.valid || !endpoint.tls || mqttUsername.isEmpty() || mqttPassword.isEmpty()) {
    backendConnectionState = endpoint.valid ? "Claim required" : "Backend not configured";
    lastMqttError = "missing claimed MQTT settings";
    ledState = LedState::Error;
    return;
  }
  if (connectMqtt(endpoint, false)) {
    uint32_t now = millis();
    if (lastHeartbeatMs == 0 || now - lastHeartbeatMs >= kHeartbeatMs) {
      lastHeartbeatMs = now;
      publishHeartbeat();
    }
    publishSerialRx();
  }
}

String htmlPage() {
  String page;
  page.reserve(8200);
  page += F("<!doctype html><html lang='en'><head><meta charset='utf-8'>");
  page += F("<meta name='viewport' content='width=device-width,initial-scale=1'>");
  page += F("<title>AI Connect Setup</title><style>");
  page += F(":root{color-scheme:dark;--panel:#171d22;--line:#2b353d;--text:#eef4f8;--muted:#9fb0bb;--accent:#28c7a7;--blue:#4aa3ff}");
  page += F("*{box-sizing:border-box}body{margin:0;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;background:#101418;color:var(--text)}");
  page += F("main{width:min(980px,100%);margin:0 auto;padding:28px 18px 42px}.top{display:flex;justify-content:space-between;gap:16px;align-items:center;margin-bottom:22px}");
  page += F("h1{font-size:28px;margin:0;letter-spacing:0}h2{margin-top:0}.sub{color:var(--muted);margin-top:6px}.pill{border:1px solid var(--line);border-radius:999px;padding:8px 12px;color:var(--accent);white-space:nowrap;background:#11191d}");
  page += F(".layout{display:grid;grid-template-columns:220px 1fr;gap:18px}.nav{border-right:1px solid var(--line);padding-right:14px}.nav button{width:100%;text-align:left;margin-bottom:4px;background:transparent;color:var(--muted);font-weight:600}");
  page += F(".nav button.active{background:#1f2a30;color:var(--text)}.panel{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:18px}.panel[hidden]{display:none}.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}");
  page += F("label{display:block;color:var(--muted);font-size:13px;margin:0 0 7px}input,select,textarea{width:100%;padding:12px;border-radius:8px;border:1px solid var(--line);background:#0f1418;color:var(--text);font-size:15px}");
  page += F("textarea{min-height:160px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}button{border:0;border-radius:8px;background:var(--accent);color:#03110e;font-weight:700;padding:12px 14px;font-size:15px;cursor:pointer}.secondary{background:#22303a;color:var(--text)}");
  page += F(".actions{display:flex;gap:10px;margin-top:16px;flex-wrap:wrap}.status{margin-top:18px;border-top:1px solid var(--line);padding-top:16px;color:var(--muted);line-height:1.55}.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--blue);overflow-wrap:anywhere}.msg{min-height:24px;margin-top:14px;color:var(--accent)}");
  page += F("@media(max-width:720px){.top{display:block}.pill{display:inline-block;margin-top:12px}.layout{grid-template-columns:1fr}.nav{border-right:0;border-bottom:1px solid var(--line);padding:0 0 12px}.grid{grid-template-columns:1fr}}");
  page += F("</style></head><body><main><div class='top'><div><h1>AI Connect</h1><div class='sub'>Field console bridge setup</div></div><div class='pill'>Firmware ");
  page += kFirmwareVersion;
  page += F("</div></div>");
  page += F("<div class='layout'><aside class='nav'><button class='active' data-tab='wireless'>Settings / Wireless</button><button data-tab='controller'>Controller</button><button data-tab='identity'>Identity</button><button data-tab='serial'>Serial</button><button data-tab='diagnostics'>Diagnostics</button></aside>");
  page += F("<section class='panel' id='wireless'><h2>Wireless</h2><div class='grid'><div><label>Wi-Fi SSID</label><select id='ssid'><option value=''>Scan to choose network</option></select></div><div><label>Wi-Fi Password</label><input id='pass' type='password' placeholder='Password'></div></div>");
  page += F("<div class='actions'><button id='scan'>Scan</button><button id='saveWifi'>Save Wi-Fi</button><button class='secondary' onclick='location.reload()'>Refresh</button></div><div class='msg' id='wifiMsg'></div><div class='status'>Saved SSID: <span class='mono'>");
  page += htmlEscape(savedSsid.length() ? savedSsid : String("none"));
  page += F("</span></div></section>");
  page += F("<section class='panel' id='controller' hidden><h2>Controller</h2><label>MQTT bootstrap endpoint</label><input id='controllerHost' placeholder='mqtts://mqtts.itego.dk:8883' value='");
  page += htmlEscape(savedController);
  page += F("'><label style='margin-top:14px'>MQTT CA PEM</label><textarea id='mqttCa' placeholder='Paste CA certificate PEM for production TLS validation'>");
  page += htmlEscape(savedCaPem);
  page += F("</textarea><div class='actions'><button id='saveController'>Save Controller</button></div><div class='msg' id='controllerMsg'></div></section>");
  page += F("<section class='panel' id='identity' hidden><h2>Identity</h2><label>Claim Code</label><input id='claimCode' placeholder='Claim code'><div class='actions'><button id='saveClaim'>Save Claim Code</button></div><div class='msg' id='identityMsg'></div><div class='status'>Claim status: <span class='mono' id='claimStatus'>");
  page += htmlEscape(claimStatus);
  page += F("</span></div></section>");
  page += F("<section class='panel' id='serial' hidden><h2>Serial</h2><div class='grid'><div><label>Baud</label><input value='9600' disabled></div><div><label>Mode</label><input value='8N1, no flow control' disabled></div></div></section>");
  page += F("<section class='panel' id='diagnostics' hidden><h2>Diagnostics</h2><div class='status'><div>Device ID: <span class='mono'>");
  page += deviceId;
  page += F("</span></div><div>Controller: <span class='mono' id='diagController'>");
  page += htmlEscape(savedController.length() ? savedController : String("not configured"));
  page += F("</span></div><div>Claim state: <span class='mono' id='diagClaim'>");
  page += htmlEscape(claimed ? String("claimed") : claimStatus);
  page += F("</span></div><div>Backend: <span class='mono' id='diagBackend'>");
  page += htmlEscape(backendConnectionState);
  page += F("</span></div><div>Last backend contact: <span class='mono' id='diagContact'>");
  page += lastBackendContactText();
  page += F("</span></div><div>Last MQTT error: <span class='mono' id='diagError'>");
  page += htmlEscape(lastMqttError);
  page += F("</span></div><div>Setup SSID: <span class='mono'>");
  page += apSsid;
  page += F("</span></div><div>AP address: <span class='mono'>192.168.4.1</span></div><div>Firmware: <span class='mono'>");
  page += kFirmwareVersion;
  page += F("</span></div><div>Contract: <span class='mono'>");
  page += kTopicPrefix;
  page += F("</span></div><div>Hardware: <span class='mono'>");
  page += kHardwareModel;
  page += F("</span></div></div></section></div></main><script>");
  page += F("const $=s=>document.querySelector(s);document.querySelectorAll('.nav button').forEach(b=>b.onclick=()=>{document.querySelectorAll('.nav button').forEach(x=>x.classList.remove('active'));document.querySelectorAll('.panel').forEach(p=>p.hidden=true);b.classList.add('active');$('#'+b.dataset.tab).hidden=false;});");
  page += F("async function post(url,data){const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams(data)});return r.text();}");
  page += F("$('#scan').onclick=async()=>{const m=$('#wifiMsg');m.textContent='Scanning...';const nets=await fetch('/api/wifi/scan').then(r=>r.json());const s=$('#ssid');s.innerHTML='<option value=\"\">Choose network</option>';nets.forEach(n=>{const o=document.createElement('option');o.value=n.ssid;o.textContent=n.ssid+' ('+n.rssi+' dBm)';s.appendChild(o)});m.textContent=nets.length?'Select a network and save.':'No networks found.'};");
  page += F("$('#saveWifi').onclick=async()=>{$('#wifiMsg').textContent=await post('/api/wifi/save',{ssid:$('#ssid').value,pass:$('#pass').value});};");
  page += F("$('#saveController').onclick=async()=>{$('#controllerMsg').textContent=await post('/api/controller/save',{controller:$('#controllerHost').value,ca:$('#mqttCa').value});};");
  page += F("$('#saveClaim').onclick=async()=>{const text=await post('/api/claim/save',{claim:$('#claimCode').value});$('#identityMsg').textContent=text;$('#claimStatus').textContent=text;};");
  page += F("async function refreshDiag(){try{const d=await fetch('/api/diagnostics').then(r=>r.json());$('#claimStatus').textContent=d.claim_state;$('#diagController').textContent=d.controller;$('#diagClaim').textContent=d.claim_state;$('#diagBackend').textContent=d.backend_connection_state;$('#diagContact').textContent=d.last_backend_contact;$('#diagError').textContent=d.last_mqtt_error;}catch(e){}}");
  page += F("setInterval(refreshDiag,3000);refreshDiag();");
  page += F("</script></body></html>");
  return page;
}

void handleRoot() {
  server.send(200, "text/html", htmlPage());
}

void handleWifiScan() {
  int count = WiFi.scanNetworks(false, true);
  String body = "[";
  for (int i = 0; i < count; i++) {
    if (i > 0) body += ",";
    body += "{\"ssid\":\"" + jsonEscape(WiFi.SSID(i)) + "\",\"rssi\":" + String(WiFi.RSSI(i)) + "}";
  }
  body += "]";
  WiFi.scanDelete();
  server.send(200, "application/json", body);
}

void handleWifiSave() {
  String ssid = server.arg("ssid");
  String pass = server.arg("pass");
  if (ssid.isEmpty()) {
    server.send(400, "text/plain", "Choose a Wi-Fi network first.");
    return;
  }
  preferences.begin("aiconnect", false);
  preferences.putString("wifi_ssid", ssid);
  preferences.putString("wifi_pass", pass);
  preferences.end();
  savedSsid = ssid;
  savedPass = pass;
  lastWifiAttemptMs = 0;
  connectWifiIfNeeded();
  uint32_t started = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - started < kWifiConnectTimeoutMs) {
    delay(250);
  }
  if (WiFi.status() == WL_CONNECTED) {
    server.send(200, "text/plain", "Saved and connected: " + WiFi.localIP().toString());
  } else {
    server.send(200, "text/plain", "Saved. Could not connect yet; check password or signal.");
  }
}

void handleControllerSave() {
  String controller = server.arg("controller");
  String ca = server.arg("ca");
  ControllerEndpoint endpoint;
  if (!parseController(controller, endpoint) || !endpoint.tls) {
    server.send(400, "text/plain", "Controller must be mqtts://host:port");
    return;
  }
  preferences.begin("aiconnect", false);
  preferences.putString("controller", controller);
  preferences.putString("mqtt_ca", ca);
  preferences.end();
  savedController = controller;
  savedCaPem = ca;
  lastMqttAttemptMs = 0;
  server.send(200, "text/plain", "Controller saved.");
}

void handleClaimSave() {
  String claim = server.arg("claim");
  claim.trim();
  preferences.begin("aiconnect", false);
  preferences.putString("claim_code", claim);
  preferences.putString("claim_status", claim.isEmpty() ? "Claim code cleared" : "Claim code saved");
  preferences.end();
  savedClaimCode = claim;
  claimStatus = claim.isEmpty() ? "Claim code cleared" : "Claim code saved";
  lastClaimPublishMs = 0;
  server.send(200, "text/plain", claimStatus);
}

void handleClaimStatus() {
  server.send(200, "text/plain", claimStatus);
}

void handleDiagnostics() {
  String body = "{";
  body += "\"device_id\":\"" + jsonEscape(deviceId) + "\",";
  body += "\"controller\":\"" + jsonEscape(savedController.length() ? savedController : String("not configured")) + "\",";
  body += "\"claim_state\":\"" + jsonEscape(claimed ? String("claimed") : claimStatus) + "\",";
  body += "\"backend_connection_state\":\"" + jsonEscape(backendConnectionState) + "\",";
  body += "\"last_backend_contact\":\"" + jsonEscape(lastBackendContactText()) + "\",";
  body += "\"last_backend_contact_ms\":" + String(lastBackendContactMs) + ",";
  body += "\"last_mqtt_error\":\"" + jsonEscape(lastMqttError) + "\",";
  body += "\"firmware_version\":\"" + String(kFirmwareVersion) + "\",";
  body += "\"contract_version\":\"" + String(kTopicPrefix) + "\"";
  body += "}";
  server.send(200, "application/json", body);
}

void handleNotFound() {
  server.sendHeader("Location", "http://192.168.4.1/", true);
  server.send(302, "text/plain", "");
}

void startSetupAp() {
  apSsid = "AICONNECT_" + deviceId.substring(deviceId.length() - 6);
  WiFi.mode(WIFI_AP_STA);
  WiFi.softAP(apSsid.c_str());
  dnsServer.start(kDnsPort, "*", WiFi.softAPIP());
  server.on("/", handleRoot);
  server.on("/generate_204", handleRoot);
  server.on("/hotspot-detect.html", handleRoot);
  server.on("/api/wifi/scan", HTTP_GET, handleWifiScan);
  server.on("/api/wifi/save", HTTP_POST, handleWifiSave);
  server.on("/api/controller/save", HTTP_POST, handleControllerSave);
  server.on("/api/claim/save", HTTP_POST, handleClaimSave);
  server.on("/api/claim/status", HTTP_GET, handleClaimStatus);
  server.on("/api/diagnostics", HTTP_GET, handleDiagnostics);
  server.onNotFound(handleNotFound);
  server.begin();
  ledState = LedState::Setup;
  Serial.printf("\nAI Connect setup AP started\nDevice ID: %s\nSSID: %s\nURL: http://%s/\n",
                deviceId.c_str(), apSsid.c_str(), WiFi.softAPIP().toString().c_str());
}

void startClaimedMode() {
  WiFi.mode(WIFI_STA);
  ledState = LedState::Wifi;
  Serial.printf("\nAI Connect claimed mode\nDevice ID: %s\nMQTT: %s:%u\n",
                deviceId.c_str(), mqttHost.c_str(), mqttPort);
}

void updateLed() {
  uint32_t now = millis();
  if (digitalRead(kButtonPin) == LOW) {
    if (resetStartedMs == 0) {
      resetStartedMs = now;
    }
    ledState = LedState::Reset;
    if (now - resetStartedMs >= kResetHoldMs) {
      wipeDeviceState();
    }
  } else {
    resetStartedMs = 0;
  }

  uint32_t interval = 500;
  uint8_t r = 0, g = 0, b = 0;
  switch (ledState) {
    case LedState::Setup: interval = 350; b = 48; break;
    case LedState::Wifi: interval = 650; r = 48; g = 30; break;
    case LedState::Claiming: interval = 250; g = 40; b = 48; break;
    case LedState::Online: setLed(0, 48, 0); return;
    case LedState::Offline: interval = 800; r = 48; break;
    case LedState::Error: interval = 180; r = 64; break;
    case LedState::Reset: interval = 120; r = 48; g = 48; b = 48; break;
  }
  if (now - lastBlinkMs >= interval) {
    lastBlinkMs = now;
    ledOn = !ledOn;
    if (ledOn) setLed(r, g, b);
    else setLed(0, 0, 0);
  }
}
}  // namespace

void setup() {
  pinMode(kButtonPin, INPUT);
  Serial.begin(115200);
  delay(300);
  deviceId = buildDeviceId();
  loadConfig();
  mode = claimed ? Mode::Claimed : Mode::Setup;
  if (mode == Mode::Setup) {
    startSetupAp();
  } else {
    startClaimedMode();
  }
}

void loop() {
  if (mode == Mode::Setup) {
    dnsServer.processNextRequest();
    server.handleClient();
    connectWifiIfNeeded();
    runClaimLoop();
  } else {
    runClaimedLoop();
  }
  mqttClient.loop();
  refreshMqttConnectionState();
  updateLed();
}
