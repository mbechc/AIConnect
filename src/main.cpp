#include <Arduino.h>
#include <DNSServer.h>
#include <Preferences.h>
#include <WebServer.h>
#include <WiFi.h>

namespace {
constexpr uint8_t kLedPin = 27;
constexpr uint8_t kButtonPin = 39;
constexpr uint8_t kDnsPort = 53;

DNSServer dnsServer;
WebServer server(80);
Preferences preferences;

String deviceId;
String apSsid;
String savedSsid;
String savedController;
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
  page += F(".layout{display:grid;grid-template-columns:220px 1fr;gap:18px}.nav{border-right:1px solid var(--line);padding-right:14px}.nav button{width:100%;text-align:left;margin-bottom:4px;background:transparent;color:var(--muted);font-weight:600}.nav button.active{background:#1f2a30;color:var(--text)}");
  page += F(".panel{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:18px}.panel[hidden]{display:none}.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}");
  page += F("label{display:block;color:var(--muted);font-size:13px;margin:0 0 7px}input,select{width:100%;padding:12px;border-radius:8px;border:1px solid var(--line);background:#0f1418;color:var(--text);font-size:15px}");
  page += F("button{border:0;border-radius:8px;background:var(--accent);color:#03110e;font-weight:700;padding:12px 14px;font-size:15px;cursor:pointer}.secondary{background:#22303a;color:var(--text)}.danger{background:#ff6b6b;color:#210505}");
  page += F(".actions{display:flex;gap:10px;margin-top:16px;flex-wrap:wrap}.status{margin-top:18px;border-top:1px solid var(--line);padding-top:16px;color:var(--muted);line-height:1.55}.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--blue)}.msg{min-height:24px;margin-top:14px;color:var(--accent)}");
  page += F("@media(max-width:720px){.top{display:block}.pill{display:inline-block;margin-top:12px}.layout{grid-template-columns:1fr}.nav{border-right:0;border-bottom:1px solid var(--line);padding:0 0 12px}.grid{grid-template-columns:1fr}}");
  page += F("</style></head><body><main><div class='top'><div><h1>AI Connect</h1><div class='sub'>Field console bridge setup</div></div><div class='pill'>Setup AP Active</div></div>");
  page += F("<div class='layout'><aside class='nav'><button class='active' data-tab='wireless'>Settings / Wireless</button><button data-tab='controller'>Controller</button><button data-tab='identity'>Identity</button><button data-tab='serial'>Serial</button><button data-tab='diagnostics'>Diagnostics</button></aside>");
  page += F("<section class='panel' id='wireless'><h2 style='margin-top:0'>Wireless</h2><div class='grid'><div><label>Wi-Fi SSID</label><select id='ssid'><option value=''>Scan to choose network</option></select></div><div><label>Wi-Fi Password</label><input id='pass' type='password' placeholder='Password'></div></div>");
  page += F("<div class='actions'><button id='scan'>Scan</button><button id='saveWifi'>Save Wi-Fi</button><button class='secondary' onclick='location.reload()'>Refresh</button></div><div class='msg' id='wifiMsg'></div>");
  page += F("<div class='status'><div>Saved SSID: <span class='mono'>");
  page += savedSsid.length() ? savedSsid : String("none");
  page += F("</span></div></div></section>");
  page += F("<section class='panel' id='controller' hidden><h2 style='margin-top:0'>Controller</h2><label>MQTT Controller Host</label><input id='controllerHost' placeholder='mqtts://controller.example:8883' value='");
  page += savedController;
  page += F("'><div class='actions'><button id='saveController'>Save Controller</button></div><div class='msg' id='controllerMsg'></div></section>");
  page += F("<section class='panel' id='identity' hidden><h2 style='margin-top:0'>Identity</h2><label>Claim Code</label><input id='claimCode' placeholder='Claim code'><div class='actions'><button id='saveClaim'>Store Claim Code</button></div><div class='msg' id='identityMsg'></div></section>");
  page += F("<section class='panel' id='serial' hidden><h2 style='margin-top:0'>Serial</h2><div class='grid'><div><label>Baud</label><input value='9600' disabled></div><div><label>Mode</label><input value='8N1, no flow control' disabled></div></div></section>");
  page += F("<section class='panel' id='diagnostics' hidden><h2 style='margin-top:0'>Diagnostics</h2>");
  page += F("<div class='status'><div>Device ID: <span class='mono'>");
  page += deviceId;
  page += F("</span></div><div>Setup SSID: <span class='mono'>");
  page += apSsid;
  page += F("</span></div><div>AP address: <span class='mono'>192.168.4.1</span></div></div></section>");
  page += F("</div></main><script>");
  page += F("const $=s=>document.querySelector(s);document.querySelectorAll('.nav button').forEach(b=>b.onclick=()=>{document.querySelectorAll('.nav button').forEach(x=>x.classList.remove('active'));document.querySelectorAll('.panel').forEach(p=>p.hidden=true);b.classList.add('active');$('#'+b.dataset.tab).hidden=false;});");
  page += F("async function post(url,data){const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams(data)});return r.text();}");
  page += F("$('#scan').onclick=async()=>{const m=$('#wifiMsg');m.textContent='Scanning...';const nets=await fetch('/api/wifi/scan').then(r=>r.json());const s=$('#ssid');s.innerHTML='<option value=\"\">Choose network</option>';nets.forEach(n=>{const o=document.createElement('option');o.value=n.ssid;o.textContent=n.ssid+' ('+n.rssi+' dBm)';s.appendChild(o)});m.textContent=nets.length?'Select a network and save.':'No networks found.'};");
  page += F("$('#saveWifi').onclick=async()=>{$('#wifiMsg').textContent=await post('/api/wifi/save',{ssid:$('#ssid').value,pass:$('#pass').value});};");
  page += F("$('#saveController').onclick=async()=>{$('#controllerMsg').textContent=await post('/api/controller/save',{controller:$('#controllerHost').value});};");
  page += F("$('#saveClaim').onclick=async()=>{$('#identityMsg').textContent=await post('/api/claim/save',{claim:$('#claimCode').value});};");
  page += F("</script></body></html>");
  return page;
}

void setLed(uint8_t red, uint8_t green, uint8_t blue) {
  neopixelWrite(kLedPin, red, green, blue);
}

void handleRoot() {
  server.send(200, "text/html", htmlPage());
}

void handleWifiScan() {
  int count = WiFi.scanNetworks(false, true);
  String body = "[";
  for (int i = 0; i < count; i++) {
    if (i > 0) {
      body += ",";
    }
    body += "{\"ssid\":\"";
    body += WiFi.SSID(i);
    body += "\",\"rssi\":";
    body += WiFi.RSSI(i);
    body += "}";
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

  WiFi.begin(ssid.c_str(), pass.c_str());
  uint32_t started = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - started < 10000) {
    delay(250);
  }

  if (WiFi.status() == WL_CONNECTED) {
    server.send(200, "text/plain", "Saved and connected: " + WiFi.localIP().toString());
  } else {
    WiFi.disconnect(false);
    server.send(200, "text/plain", "Saved. Could not connect yet; check password or signal.");
  }
}

void handleControllerSave() {
  String controller = server.arg("controller");
  preferences.begin("aiconnect", false);
  preferences.putString("controller", controller);
  preferences.end();
  savedController = controller;
  server.send(200, "text/plain", "Controller saved.");
}

void handleClaimSave() {
  String claim = server.arg("claim");
  preferences.begin("aiconnect", false);
  preferences.putString("claim_code", claim);
  preferences.end();
  server.send(200, "text/plain", claim.isEmpty() ? "Claim code cleared." : "Claim code stored.");
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

  preferences.begin("aiconnect", true);
  savedSsid = preferences.getString("wifi_ssid", "");
  savedController = preferences.getString("controller", "");
  preferences.end();

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
