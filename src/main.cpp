#include <Arduino.h>
#include <DNSServer.h>
#include <WebServer.h>
#include <WiFi.h>

namespace {
constexpr uint8_t kLedPin = 27;
constexpr uint8_t kButtonPin = 39;
constexpr uint8_t kDnsPort = 53;

DNSServer dnsServer;
WebServer server(80);

String deviceId;
String apSsid;
uint32_t lastBlinkMs = 0;
bool ledOn = false;

String htmlPage() {
  String page;
  page.reserve(5200);
  page += F("<!doctype html><html lang='en'><head><meta charset='utf-8'>");
  page += F("<meta name='viewport' content='width=device-width,initial-scale=1'>");
  page += F("<title>AI Connect Setup</title><style>");
  page += F(":root{color-scheme:dark;--bg:#101418;--panel:#171d22;--line:#2b353d;--text:#eef4f8;--muted:#9fb0bb;--accent:#28c7a7;--blue:#4aa3ff}");
  page += F("*{box-sizing:border-box}body{margin:0;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;background:linear-gradient(135deg,#101418,#1b2228);color:var(--text)}");
  page += F("main{width:min(960px,100%);margin:0 auto;padding:28px 18px 42px}.top{display:flex;justify-content:space-between;gap:16px;align-items:center;margin-bottom:22px}");
  page += F("h1{font-size:28px;margin:0;letter-spacing:0}.sub{color:var(--muted);margin-top:6px}.pill{border:1px solid var(--line);border-radius:999px;padding:8px 12px;color:var(--accent);white-space:nowrap;background:#11191d}");
  page += F(".layout{display:grid;grid-template-columns:220px 1fr;gap:18px}.nav{border-right:1px solid var(--line);padding-right:14px}.nav div{padding:12px 10px;border-radius:8px;color:var(--muted)}.nav .active{background:#1f2a30;color:var(--text)}");
  page += F(".panel{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:18px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}");
  page += F("label{display:block;color:var(--muted);font-size:13px;margin:0 0 7px}input{width:100%;padding:12px;border-radius:8px;border:1px solid var(--line);background:#0f1418;color:var(--text);font-size:15px}");
  page += F("button{border:0;border-radius:8px;background:var(--accent);color:#03110e;font-weight:700;padding:12px 14px;font-size:15px;cursor:pointer}.secondary{background:#22303a;color:var(--text)}");
  page += F(".actions{display:flex;gap:10px;margin-top:16px;flex-wrap:wrap}.status{margin-top:18px;border-top:1px solid var(--line);padding-top:16px;color:var(--muted);line-height:1.55}.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--blue)}");
  page += F("@media(max-width:720px){.top{display:block}.pill{display:inline-block;margin-top:12px}.layout{grid-template-columns:1fr}.nav{border-right:0;border-bottom:1px solid var(--line);padding:0 0 12px}.grid{grid-template-columns:1fr}}");
  page += F("</style></head><body><main><div class='top'><div><h1>AI Connect</h1><div class='sub'>Field console bridge setup</div></div><div class='pill'>Setup AP Active</div></div>");
  page += F("<div class='layout'><aside class='nav'><div class='active'>Settings / Wireless</div><div>Controller</div><div>Identity</div><div>Serial</div><div>Diagnostics</div></aside>");
  page += F("<section class='panel'><h2 style='margin-top:0'>Wireless</h2><div class='grid'><div><label>Wi-Fi SSID</label><input placeholder='Network name'></div><div><label>Wi-Fi Password</label><input type='password' placeholder='Password'></div></div>");
  page += F("<div class='actions'><button disabled>Save Wi-Fi</button><button class='secondary' onclick='location.reload()'>Refresh</button></div>");
  page += F("<div class='status'><div>Device ID: <span class='mono'>");
  page += deviceId;
  page += F("</span></div><div>Setup SSID: <span class='mono'>");
  page += apSsid;
  page += F("</span></div><div>AP address: <span class='mono'>192.168.4.1</span></div><div>This first firmware only proves setup AP, captive DNS, LED, and hardware identity naming. Wi-Fi saving and claim flow come next.</div></div>");
  page += F("</section></div></main></body></html>");
  return page;
}

void setLed(uint8_t red, uint8_t green, uint8_t blue) {
  neopixelWrite(kLedPin, red, green, blue);
}

void handleRoot() {
  server.send(200, "text/html", htmlPage());
}

void handleNotFound() {
  server.sendHeader("Location", "http://192.168.4.1/", true);
  server.send(302, "text/plain", "");
}

String buildDeviceId() {
  uint64_t mac = ESP.getEfuseMac();
  char id[13];
  snprintf(id, sizeof(id), "%04X%08X", static_cast<uint16_t>(mac >> 32),
           static_cast<uint32_t>(mac));
  return String(id);
}

void startSetupAp() {
  deviceId = buildDeviceId();
  apSsid = "AICONNECT_" + deviceId.substring(deviceId.length() - 6);

  WiFi.mode(WIFI_AP);
  WiFi.softAP(apSsid.c_str());

  dnsServer.start(kDnsPort, "*", WiFi.softAPIP());
  server.on("/", handleRoot);
  server.on("/generate_204", handleRoot);
  server.on("/hotspot-detect.html", handleRoot);
  server.onNotFound(handleNotFound);
  server.begin();

  Serial.printf("\nAI Connect setup AP started\n");
  Serial.printf("Device ID: %s\n", deviceId.c_str());
  Serial.printf("SSID: %s\n", apSsid.c_str());
  Serial.printf("URL: http://%s/\n", WiFi.softAPIP().toString().c_str());
}
}  // namespace

void setup() {
  pinMode(kButtonPin, INPUT);
  Serial.begin(115200);
  delay(300);
  startSetupAp();
}

void loop() {
  dnsServer.processNextRequest();
  server.handleClient();

  const uint32_t now = millis();
  if (now - lastBlinkMs >= 350) {
    lastBlinkMs = now;
    ledOn = !ledOn;
    if (ledOn) {
      setLed(0, 0, 48);
    } else {
      setLed(0, 0, 0);
    }
  }
}
