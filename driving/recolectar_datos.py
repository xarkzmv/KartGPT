import cv2
import urllib.request
import numpy as np
import os
import datetime
import threading
import time
from pynput import keyboard

# ==========================================
# ⚙️ CONFIGURACIÓN
# ==========================================
ESP_IP = "coche-esp32.local" 
STREAM_URL = f"http://{ESP_IP}:81/stream"
CONTROL_URL = f"http://{ESP_IP}"

DATASET_FOLDER = 'dataset_pista_vectorial'
# OpenCV usa (Ancho, Alto). Tu entrenamiento espera (Alto=320, Ancho=240).
SAVE_SIZE = (320, 240) 

# Clases (Carpetas)
CLASES = ['avanzar', 'avanzar_izquierda', 'avanzar_derecha']

for label in CLASES:
    os.makedirs(os.path.join(DATASET_FOLDER, label), exist_ok=True)

counts = {label: len(os.listdir(os.path.join(DATASET_FOLDER, label))) for label in CLASES}

# Estado de teclas físicas
keys_pressed = {'w': False, 'a': False, 's': False, 'd': False}

# --- MEMORIA DE ESTADO DE LAS RUEDAS ---
# -1: Izquierda | 0: Centro | 1: Derecha
# Empieza en 0 (asumimos que lo pones recto al inicio)
wheel_state = 0 

# Mutex para evitar colisiones de comandos
lock = threading.Lock()

def enviar_comando_async(comando):
    """Envío asíncrono para no congelar video"""
    def _req():
        try: urllib.request.urlopen(f"{CONTROL_URL}{comando}", timeout=0.1)
        except: pass
    threading.Thread(target=_req).start()

def gestionar_logica(frame):
    """
    Decide qué guardar basado en el ESTADO PERSISTENTE (wheel_state)
    """
    global wheel_state
    
    accion = None
    texto = "PARADO"
    color = (0, 0, 255)

    # 1. ACTUALIZAR ESTADO DE DIRECCIÓN (Si se presionan teclas)
    if keys_pressed['a']:
        # Si presiono A, el estado pasa a IZQUIERDA
        if wheel_state != -1:
            enviar_comando_async("/izquierda")
            wheel_state = -1
    elif keys_pressed['d']:
        # Si presiono D, el estado pasa a DERECHA
        if wheel_state != 1:
            enviar_comando_async("/derecha")
            wheel_state = 1
    
    # 2. AVANCE Y GRABACIÓN (Depende del estado, no de si aprietas A o D ahora mismo)
    if keys_pressed['w']:
        enviar_comando_async("/avanzar")
        
        # Clasificamos según la MEMORIA de donde quedaron las ruedas
        if wheel_state == -1:
            accion = 'avanzar_izquierda'
            texto = "REC: IZQ ↖️ (Memoria)"
            color = (255, 0, 0)
        elif wheel_state == 1:
            accion = 'avanzar_derecha'
            texto = "REC: DER ↗️ (Memoria)"
            color = (0, 0, 255)
        else: # wheel_state == 0
            accion = 'avanzar'
            texto = "REC: RECTO ⬆️"
            color = (0, 255, 0)
            
    elif keys_pressed['s']:
        enviar_comando_async("/atras")
        texto = "ATRAS ⬇️"
        color = (0, 255, 255)
    else:
        # Si no avanza, paramos motor principal
        enviar_comando_async("/parar_propulsion")
    if accion:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{DATASET_FOLDER}/{accion}/img_{timestamp}.jpg"
        # Redimensionar correctamente antes de guardar
        frame_resized = cv2.resize(frame, SAVE_SIZE)
        cv2.imwrite(filename, frame_resized)
        counts[accion] += 1
    
    return texto, color


# --- TECLADO ---
def on_press(key):
    try:
        if hasattr(key, 'char'):
            char = key.char
            if char in keys_pressed:
                keys_pressed[char] = True
            
            # TECLA 'C' PARA RESETEAR ESTADO A CENTRO MANUALMENTE
            if char == 'c':
                global wheel_state
                print("🔄 Estado reseteado a CENTRO")
                wheel_state = 0
                
    except AttributeError: pass

def on_release(key):
    try:
        if hasattr(key, 'char') and key.char in keys_pressed:
            keys_pressed[key.char] = False
            
            # AL SOLTAR 'A' o 'D':
            # Solo paramos el motor para que no sufra, 
            # PERO NO CAMBIAMOS 'wheel_state'. El código recuerda que quedó doblado.
            if key.char == 'a' or key.char == 'd':
                enviar_comando_async("/parar_direccion")
                
    except AttributeError: pass

listener = keyboard.Listener(on_press=on_press, on_release=on_release)
listener.start()

# --- VIDEO ---
print(f"Conectando a {STREAM_URL}...")
try:
    stream = urllib.request.urlopen(STREAM_URL, timeout=5)
    print("✅ Conectado.")
    print("-------------------------------------------------")
    print(" CONTROLES:")
    print(" [W] Avanzar y Grabar (Según dirección actual)")
    print(" [A] Girar Izquierda (El estado queda en IZQ)")
    print(" [D] Girar Derecha   (El estado queda en DER)")
    print(" [C] Resetear Estado a CENTRO (Úsalo al enderezar)")
    print("-------------------------------------------------")

except Exception as e:
    print(f"❌ Error: {e}")
    exit()

bytes_data = b''

while True:
    try:
        bytes_data += stream.read(4096)
        a = bytes_data.find(b'\xff\xd8')
        if a != -1:
            b = bytes_data.find(b'\xff\xd9', a)
            if b != -1:
                jpg = bytes_data[a:b+2]
                bytes_data = bytes_data[b+2:]
                if len(jpg) > 0:
                    frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                    if frame is not None:
                        display = frame.copy()
                        txt, col = gestionar_logica(frame)
                        cv2.putText(display, txt, (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, col, 2)
                        cv2.imshow('Recolector', display)
                        if cv2.waitKey(1) & 0xFF == ord('q'): break
    except: break

listener.stop()
cv2.destroyAllWindows()