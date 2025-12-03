#include <WiFi.h>
#include <ESPAsyncWebServer.h>
#include <ESPmDNS.h>

#include "esp_camera.h"
#include "camera_pins.h"
#include "stream_server.h"
#include "control_motores.h"

#define PIN_FLASH 2    // Flash LED (Asegúrate que es el 4 en tu placa, a veces es el 2)
//#define LED_PIN       // LED de estado (rojo trasero, suele ser 33 invertido)

// --- WI-FI ---
const char *ssid = "TU_RED_WIFI";
const char *password = "TU_CONTRASEÑA";


const int VELOCIDAD_BASE = 150; 
const int VELOCIDAD_GIRO = 120;

AsyncWebServer server(80);

// --- HTML GAME BOY CON LÓGICA RESTAURADA ---
const char index_html[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
  <title>KartGPT Controller</title>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <style>
    /* --- CSS ESTILO GAMEBOY (LIGERO) --- */
    body {
      background-color: #202020;
      color: white;
      font-family: sans-serif;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      margin: 0;
      touch-action: manipulation;
      user-select: none;
    }

    /* Carcasa */
    .gb-body {
      background-color: #9DBBE3; /* Teal GBC */
      width: 320px;
      height: 580px;
      border-radius: 10px 10px 50px 10px;
      box-shadow: 5px 5px 15px rgba(0,0,0,0.5), inset 2px 2px 5px rgba(255,255,255,0.3);
      padding: 20px;
      display: flex;
      flex-direction: column;
      align-items: center;
      position: relative;
    }

    /* Marco Pantalla */
    .screen-lens {
      background-color: #555;
      width: 100%;
      padding: 15px 0 30px 0;
      border-radius: 10px 10px 40px 10px;
      box-shadow: inset 2px 2px 5px rgba(0,0,0,0.5);
      display: flex;
      flex-direction: column;
      align-items: center;
      margin-bottom: 20px;
    }
    
    /* LCD */
    .screen-container {
        width: 240px; height: 180px;
        background: #000;
        border: 4px solid #444;
        display: flex; align-items: center; justify-content: center;
        box-shadow: inset 2px 2px 5px rgba(0,0,0,0.6);
        overflow: hidden;
    }
    img#stream { width: 100%; height: 100%; object-fit: cover; }
    
    /* Mensaje de Estado (ID restaurado a auto-msg) */
    #auto-msg { 
        display: none; 
        color: #0f0; 
        font-family: monospace; 
        font-weight: bold; 
        text-align: center; 
    }

    .power-led {
        position: absolute; top: 80px; left: 15px;
        width: 8px; height: 8px; border-radius: 50%;
        background-color: #333;
    }
    .power-led.on { background-color: red; box-shadow: 0 0 5px red; }

    /* Área Controles */
    .controls-area { width: 100%; display: flex; justify-content: space-between; margin-top: 20px; }

    /* Cruceta */
    .dpad { width: 100px; height: 100px; position: relative; }
    .d-btn { position: absolute; background: #222; border: none; cursor: pointer; }
    .d-btn:active, .d-btn.active-key { background: #444; }
    
    #btn-fwd { top: 0; left: 33px; width: 34px; height: 34px; border-radius: 3px 3px 0 0; }
    #btn-bwd { bottom: 0; left: 33px; width: 34px; height: 34px; border-radius: 0 0 3px 3px; }
    #btn-left { top: 33px; left: 0; width: 34px; height: 34px; border-radius: 3px 0 0 3px; }
    #btn-right { top: 33px; right: 0; width: 34px; height: 34px; border-radius: 0 3px 3px 0; }
    .d-center { position: absolute; top: 33px; left: 33px; width: 34px; height: 34px; background: #222; z-index: 1; }

    /* Botones A/B */
    .action-group { transform: rotate(-20deg); margin-top: 10px; }
    .round-btn {
        width: 45px; height: 45px; border-radius: 50%; border: none;
        color: #333; font-weight: bold; font-size: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.3); cursor: pointer;
        margin-left: 10px; display: flex; justify-content: center; align-items: center;
    }
    .round-btn:active { transform: scale(0.95); box-shadow: inset 1px 1px 3px rgba(0,0,0,0.4); }
    
    /* Botón LED (E) */
    #btn-led { background: #a0a; margin-bottom: 15px; } 
    #btn-led.active { background: #d0d; box-shadow: 0 0 10px #fff; color: white; }

    /* Botón MODO (Espacio) */
    #btn-mode { background: #555; color: white; } 
    #btn-mode.mode-auto { background: #4caf50; box-shadow: 0 0 10px #4caf50; }

    .label { font-size: 10px; color: #333; font-weight: bold; text-align: center; margin-top: 2px;}
    
  </style>
</head>
<body>

  <div class="gb-body">
    <div class="screen-lens">
      <div class="power-led on"></div>
      <div class="screen-container">
        <img id="stream" src="">
        <div id="auto-msg">ESPERANDO<br>PYTHON...</div>
      </div>
      <div style="margin-top:5px; font-size:12px; font-weight:bold; color:#ccc; letter-spacing:1px;">KART<span style="color:#d0d">GPT</span></div>
    </div>

    <div class="controls-area">
      
      <div class="dpad" id="manual-controls">
        <div class="d-center"></div>
        <button class="d-btn" id="btn-fwd" onmousedown="startMove('/avanzar')" onmouseup="stopPropulsion()" ontouchstart="startMove('/avanzar')" ontouchend="stopPropulsion()"></button>
        <button class="d-btn" id="btn-left" onmousedown="startMove('/izquierda')" onmouseup="stopDireccion()" ontouchstart="startMove('/izquierda')" ontouchend="stopDireccion()"></button>
        <button class="d-btn" id="btn-right" onmousedown="startMove('/derecha')" onmouseup="stopDireccion()" ontouchstart="startMove('/derecha')" ontouchend="stopDireccion()"></button>
        <button class="d-btn" id="btn-bwd" onmousedown="startMove('/atras')" onmouseup="stopPropulsion()" ontouchstart="startMove('/atras')" ontouchend="stopPropulsion()"></button>
      </div>

      <div class="action-group">
        <div style="text-align:center;">
            <button id="btn-led" class="round-btn" onclick="toggleLed()">LED (E)</button>
        </div>
        <div style="text-align:center; margin-right: 30px;">
            <button id="btn-mode" class="round-btn" onclick="toggleMode()">MANUAL</button>
        </div>
      </div>

    </div>
  </div>

  <script> 
     let isAutoMode = false; 
     let isLedOn = false; 
     const streamImg = document.getElementById('stream'); 
     const autoMsg = document.getElementById('auto-msg'); 
     const modeBtn = document.getElementById('btn-mode'); 
     const ledBtn = document.getElementById('btn-led'); 
     const manualControls = document.getElementById('manual-controls'); 

     // Al cargar, iniciamos en manual (Video ON) 
     window.onload = function() { 
       startVideo(); 
     }; 

     function startVideo() { 
       streamImg.style.display = 'block'; 
       autoMsg.style.display = 'none'; 
       streamImg.src = 'http://' + window.location.hostname + ':81/stream'; 
     } 

     function stopVideo() { 
       streamImg.src = ""; // ESTO ES CLAVE: Libera el socket
       streamImg.style.display = 'none'; 
       autoMsg.style.display = 'block'; 
     } 

     function toggleMode() { 
       isAutoMode = !isAutoMode; 
        
       if (isAutoMode) { 
         // --- ACTIVAR MODO AUTOMÁTICO --- 
         stopVideo(); 
         stopAll(); 
         // Cambiar UI 
         modeBtn.innerText = "AUTO"; 
         modeBtn.className = "round-btn mode-auto";  
         manualControls.style.opacity = "0.3";  
         manualControls.style.pointerEvents = "none"; 
          
       } else { 
         // --- VOLVER A MODO MANUAL --- 
         startVideo(); 
         // Cambiar UI 
         modeBtn.innerText = "MANUAL"; 
         modeBtn.className = "round-btn mode-manual";  
         manualControls.style.opacity = "1"; 
         manualControls.style.pointerEvents = "auto"; 
       } 
     } 
      
     function toggleLed() { 
         isLedOn = !isLedOn; 
         // Arreglo de rutas: El C++ espera /flash_on o /flash_off
         sendCommand(isLedOn ? '/flash_on' : '/flash_off'); 

         if (isLedOn) { 
             ledBtn.classList.add('active'); 
         } else { 
             ledBtn.classList.remove('active'); 
         } 
     } 

     // --- Funciones de Control --- 
     function sendCommand(url) { 
       fetch(url, { method: 'GET' }).catch(err => console.error('Error:', err)); 
     } 
     function startMove(dir) { sendCommand(dir); } 
     function stopPropulsion() { sendCommand('/parar_propulsion'); } 
     function stopDireccion() { sendCommand('/parar_direccion'); } 
     function stopAll() { sendCommand('/parar_todo'); } 

     // --- Control por Teclado --- 
     const keyActions = { 
       'w': { start: '/avanzar', stop: '/parar_propulsion', btnId: 'btn-fwd' }, 
       's': { start: '/atras', stop: '/parar_propulsion', btnId: 'btn-bwd' }, 
       'a': { start: '/izquierda', stop: '/parar_direccion', btnId: 'btn-left' }, 
       'd': { start: '/derecha', stop: '/parar_direccion', btnId: 'btn-right' }, 
       ' ': { action: 'mode_toggle' },  // Espacio -> Modo
       'e': { action: 'led_toggle', btnId: 'btn-led' } // E -> LED
     }; 
      
     document.addEventListener('keydown', (event) => { 
       if (event.repeat) return; 
       const key = event.key.toLowerCase(); 
       const action = keyActions[key]; 
        
       if (action) { 
           // Prevenir scroll con espacio
           if (key === ' ') event.preventDefault();

           if (action.action === 'led_toggle') { 
               toggleLed(); 
           } else if (action.action === 'mode_toggle') {
               toggleMode();
           } else if (!isAutoMode) { 
               // Comandos de movimiento (solo si no está en auto)
               sendCommand(action.start); 
               if (action.btnId) document.getElementById(action.btnId).classList.add('active-key'); 
           } 
       } 
     }); 

     document.addEventListener('keyup', (event) => { 
       if (isAutoMode) return; 
       const key = event.key.toLowerCase(); 
       const action = keyActions[key]; 
        
       if (action && action.stop) { 
         sendCommand(action.stop); 
         if (action.btnId) document.getElementById(action.btnId).classList.remove('active-key'); 
       } 
     }); 
      
     document.oncontextmenu = function(event) { event.preventDefault(); return false; }; 
   </script> 
</body>
</html>
)rawliteral";

// --- SETUP CÁMARA ---
void setupCamara(){
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.frame_size = FRAMESIZE_QVGA; 
  config.pixel_format = PIXFORMAT_JPEG;
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.jpeg_quality = 12; 
  config.fb_count = 1;

  if (esp_camera_init(&config) != ESP_OK) {
    Serial.println("Error al iniciar cámara");
    return;
  }
  sensor_t * s = esp_camera_sensor_get();
  s->set_hmirror(s, 1);
  s->set_vflip(s, 1);
}

// --- RUTAS ---
void setupServerRoutes() {
  server.on("/", HTTP_GET, [](AsyncWebServerRequest *request){
    request->send_P(200, "text/html", index_html);
  });
  
  // Rutas de Movimiento
  server.on("/avanzar", HTTP_GET, [](AsyncWebServerRequest *request){
    avanzar(VELOCIDAD_BASE); request->send(200, "text/plain", "OK");
  });
  server.on("/atras", HTTP_GET, [](AsyncWebServerRequest *request){
    retroceder(VELOCIDAD_BASE); request->send(200, "text/plain", "OK");
  });
  server.on("/parar_propulsion", HTTP_GET, [](AsyncWebServerRequest *request){
    parar_propulsion(); request->send(200, "text/plain", "OK");
  });
  server.on("/izquierda", HTTP_GET, [](AsyncWebServerRequest *request){
    girar_direccion(VELOCIDAD_GIRO, IZQ); request->send(200, "text/plain", "OK");
  });
  server.on("/derecha", HTTP_GET, [](AsyncWebServerRequest *request){
    girar_direccion(VELOCIDAD_GIRO, DER); request->send(200, "text/plain", "OK");
  });
  server.on("/parar_direccion", HTTP_GET, [](AsyncWebServerRequest *request){
    parar_direccion(); request->send(200, "text/plain", "OK");
  });
  server.on("/parar_todo", HTTP_GET, [](AsyncWebServerRequest *request){
    parar_propulsion(); parar_direccion(); request->send(200, "text/plain", "OK");
  });

  // --- RUTAS LED ---
  server.on("/flash_on", HTTP_GET, [](AsyncWebServerRequest *request){
    digitalWrite(PIN_FLASH, HIGH);
    request->send(200, "text/plain", "LED ON");
  });
  server.on("/flash_off", HTTP_GET, [](AsyncWebServerRequest *request){
    digitalWrite(PIN_FLASH, LOW);
    request->send(200, "text/plain", "LED OFF");
  });
}

// --- SETUP ---
void setup() {
  Serial.begin(115200);
  
  // Configuración de Pines LED
  pinMode(PIN_FLASH, OUTPUT);
  digitalWrite(PIN_FLASH, LOW);
 // pinMode(LED_PIN, OUTPUT); // LED rojo trasero (opcional)
//  digitalWrite(LED_PIN, HIGH); // Apagado (lógica inversa en algunos modelos)

  setupCamara();
  setupMotores();

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nIP: ");
  Serial.println(WiFi.localIP());

  if (MDNS.begin("coche-esp32")) {
    MDNS.addService("http", "tcp", 80);
  }

  setupServerRoutes();
  server.begin();
  startCameraStreamServer();
}

void loop() {}