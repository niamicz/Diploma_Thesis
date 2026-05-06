#include <WiFi.h>
#include <WebServer.h>
#include <Wire.h>
#include <Adafruit_BMP280.h>
#include <esp_cpu.h>

// --- Konfigurace geometrie ---
// Výchozí hodnoty se po zavolání /zero přepočítají podle reálného kusu
float LY = 0.1766; 
float LX = 0.1939; 

// --- Definice Pinů (dle tvého schématu) ---
#define TRIG_P 33
#define ECHO_P 34
#define TRIG_Z 27
#define ECHO_Z 35
#define TRIG_L 25
#define ECHO_L 36
#define TRIG_PR 26
#define ECHO_PR 39

Adafruit_BMP280 bmp;
WebServer server(80);

// --- Proměnné pro filtraci a kalibraci ---
float filt_vx = 0, filt_vy = 0;
float offset_vx = 0, offset_vy = 0;
const float alpha = 0.20; // Koeficient exponenciálního klouzavého průměru

// --- Buffery pro 30s průměrování ---
float avg_vx = 0, avg_vy = 0;
float sum_vx = 0, sum_vy = 0;
int avg_count = 0;
unsigned long last_avg_time = 0;

// Výpočet rychlosti zvuku v závislosti na teplotě
float getC(float t) { return 331.3 * sqrt(1 + t / 273.15); }

/**
 * Měření Time-of-Flight s rozlišením na cykly procesoru (4.16 ns při 240 MHz).
 * Nahrazuje pulseIn(), čímž zvyšuje rozlišení cca 240x.
 */
float getToF_Ultra(int t1, int t2, int echoTarget) {
    delay(20); // Pauza pro útlum akustických odrazů
    digitalWrite(t1, LOW); digitalWrite(t2, LOW);
    delayMicroseconds(2);
    digitalWrite(t1, HIGH); digitalWrite(t2, HIGH); // Simultánní buzení
    delayMicroseconds(10);
    digitalWrite(t1, LOW); digitalWrite(t2, LOW);

    uint32_t start_wait = micros();
    // Čekání na náběžnou hranu ECHO signálu
    while (digitalRead(echoTarget) == LOW) {
        if (micros() - start_wait > 25000) return 0; // Timeout
    }
    
    uint32_t start_cycles = esp_cpu_get_cycle_count(); // Start "stopek" v cyklech

    // Čekání na sestupnou hranu ECHO signálu
    while (digitalRead(echoTarget) == HIGH) {
        if (micros() - start_wait > 30000) return 0; // Timeout
    }
    
    uint32_t end_cycles = esp_cpu_get_cycle_count(); // Konec "stopek"

    // Převod cyklů na mikrosekundy (CPU Freq je typicky 240 MHz)
    float freqMHz = (float)ESP.getCpuFreqMHz();
    return (float)(end_cycles - start_cycles) / freqMHz; 
}

// Funkce pro automatickou kalibraci v bezvětří
void handleZero() {
    offset_vx = filt_vx;
    offset_vy = filt_vy;

    float temp = bmp.readTemperature();
    float c = getC(temp);
    
    // Změříme reálné časy pro výpočet přesných délek ramen
    float tp = getToF_Ultra(TRIG_P, TRIG_Z, ECHO_Z);
    float tz = getToF_Ultra(TRIG_P, TRIG_Z, ECHO_P);
    float tl = getToF_Ultra(TRIG_L, TRIG_PR, ECHO_PR);
    float tpr = getToF_Ultra(TRIG_L, TRIG_PR, ECHO_L);

    if(tp > 0 && tz > 0) LY = (c * (tp + tz) / 2.0) / 1000000.0;
    if(tl > 0 && tpr > 0) LX = (c * (tl + tpr) / 2.0) / 1000000.0;

    server.send(200, "text/plain", "Zkalibrovano: LX=" + String(LX,4) + " LY=" + String(LY,4));
}

// Hlavní smyčka sběru a zpracování dat
void handleData() {
    float tp = getToF_Ultra(TRIG_P, TRIG_Z, ECHO_Z);
    float tz = getToF_Ultra(TRIG_P, TRIG_Z, ECHO_P);
    float tl = getToF_Ultra(TRIG_L, TRIG_PR, ECHO_PR);
    float tpr = getToF_Ultra(TRIG_L, TRIG_PR, ECHO_L);

    float inst_vx = 0, inst_vy = 0;

    // Výpočet složek vektoru rychlosti
    if (tp > 100 && tz > 100) {
        inst_vy = (LY / 2.0) * ((1.0 / (tp / 1000000.0)) - (1.0 / (tz / 1000000.0)));
    }
    if (tl > 100 && tpr > 100) {
        inst_vx = (LX / 2.0) * ((1.0 / (tl / 1000000.0)) - (1.0 / (tpr / 1000000.0)));
    }

    // Filtrace šumu
    filt_vx = (inst_vx * alpha) + (filt_vx * (1.0 - alpha));
    filt_vy = (inst_vy * alpha) + (filt_vy * (1.0 - alpha));

    float out_vx = filt_vx - offset_vx;
    float out_vy = filt_vy - offset_vy;

    // Výpočet azimutu a celkové rychlosti
    float speed_raw = sqrt(out_vx * out_vx + out_vy * out_vy);
    float deg = atan2(out_vx, out_vy) * 180.0 / PI;
    if (deg < 0) deg += 360.0;

    // --- Kompenzace stínění věží (Gaussian Wake Model) ---
    float corr = 1.0;
    for(int i=0; i<4; i++) {
        float tower_angle = 45.0 + (i * 90.0); // Věže jsou na 45°, 135°, 225°, 315°
        float diff = abs(deg - tower_angle);
        if(diff > 180) diff = 360 - diff;
        if(diff < 20.0) {
            corr = 1.0 + (0.18 * exp(-pow(diff/10.0, 2))); // Gaussova korekce
        }
    }
    
    float final_vx = out_vx * corr;
    float final_vy = out_vy * corr;
    float speed = speed_raw * corr;

    // --- 30s Agregace pro meteorologické účely ---
    sum_vx += final_vx; sum_vy += final_vy; avg_count++;
    if (millis() - last_avg_time > 30000) {
        avg_vx = sum_vx / avg_count;
        avg_vy = sum_vy / avg_count;
        sum_vx = 0; sum_vy = 0; avg_count = 0;
        last_avg_time = millis();
    }

    // Sestavení JSON odpovědi pro UI
    String json = "{";
    json += "\"speed\":" + String(speed, 3) + ",";
    json += "\"vx\":" + String(final_vx, 3) + ",\"vy\":" + String(final_vy, 3) + ",";
    json += "\"avx\":" + String(avg_vx, 3) + ",\"avy\":" + String(avg_vy, 3) + ",";
    json += "\"as\":" + String(sqrt(avg_vx*avg_vx + avg_vy*avg_vy), 3) + ",";
    json += "\"deg\":" + String(deg, 1) + ",";
    json += "\"temp\":" + String(bmp.readTemperature(), 1);
    json += "}";
    server.send(200, "application/json", json);
}

// Servírování HTML stránky
void handleRoot() {
    String html = "<html><head><meta charset='UTF-8'><title>Sonic V4</title>";
    html += "<style>body{background:#000;color:#0fc;font-family:sans-serif;text-align:center;}";
    html += "#viz{background:#111;border:2px solid #333;border-radius:50%;margin:20px;}";
    html += ".val{font-size:3em;font-weight:bold;}</style></head><body>";
    html += "<h1>SONIC ANEMOMETER V4</h1>";
    html += "<div class='val'><span id='s'>0.00</span> m/s</div>";
    html += "<canvas id='viz' width='400' height='400'></canvas><br>";
    html += "<button style='padding:15px;cursor:pointer' onclick='zero()'>VYNULOVAT (ZERO)</button>";
    html += "<script>const ctx=document.getElementById('viz').getContext('2d');";
    html += "function drawArrow(vx,vy,color,w){ctx.strokeStyle=color;ctx.lineWidth=w;ctx.beginPath();";
    html += "ctx.moveTo(200,200);ctx.lineTo(200+vx*20,200-vy*20);ctx.stroke();}";
    html += "function zero(){fetch('/zero').then(r=>r.text()).then(t=>alert(t));}";
    html += "setInterval(()=>{fetch('/data').then(r=>r.json()).then(d=>{";
    html += "document.getElementById('s').innerText=d.speed.toFixed(2);";
    html += "ctx.clearRect(0,0,400,400);ctx.strokeStyle='#222';[50,100,150].forEach(r=>{ctx.beginPath();ctx.arc(200,200,r,0,7);ctx.stroke();});";
    html += "drawArrow(d.vx,d.vy,'#0fc',4);drawArrow(d.avx,d.avy,'#f30',2);})},250);</script></body></html>";
    server.send(200, "text/html", html);
}

void setup() {
    // Inicializace pinů
    pinMode(TRIG_P, OUTPUT); pinMode(TRIG_Z, OUTPUT); pinMode(TRIG_L, OUTPUT); pinMode(TRIG_PR, OUTPUT);
    pinMode(ECHO_P, INPUT); pinMode(ECHO_Z, INPUT); pinMode(ECHO_L, INPUT); pinMode(ECHO_PR, INPUT);
    
    Wire.begin(32, 14); // I2C pro BMP280
    if (!bmp.begin(0x76)) { /* Error handling */ }

    // Vytvoření AP hotspotu
    WiFi.softAP("Anemometr_V4", "12345678");

    server.on("/", handleRoot);
    server.on("/data", handleData);
    server.on("/zero", handleZero);
    server.begin();
}

void loop() {
    server.handleClient(); // Obsluha webových požadavků
}
