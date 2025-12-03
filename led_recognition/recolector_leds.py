import cv2
import urllib.request
import numpy as np
import os
import sys
import datetime

current_dir = os.path.dirname(os.path.abspath(__file__))

# 2. Obtiene la ruta de la carpeta PADRE (donde está config.py)
parent_dir = os.path.dirname(current_dir)

# 3. Agrega la carpeta padre a la lista de rutas donde Python busca módulos
sys.path.append(parent_dir)
import config# Importamos la config para usar la IP

# Carpeta para el nuevo dataset
DATASET_FOLDER = 'dataset/validation'
CLASES = ['blue_on', 'off', 'red_on']
SAVE_SIZE = (320, 240) # (Ancho, Alto) para OpenCV

# Crear carpetas
for clase in CLASES:
    os.makedirs(os.path.join(DATASET_FOLDER, clase), exist_ok=True)

counts = {c: len(os.listdir(os.path.join(DATASET_FOLDER, c))) for c in CLASES}

def guardar_foto(frame, clase):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{DATASET_FOLDER}/{clase}/img_{timestamp}.jpg"
    frame_resized = cv2.resize(frame, SAVE_SIZE)
    cv2.imwrite(filename, frame_resized)
    counts[clase] += 1
    print(".", end="", flush=True)

print(f"Conectando a {config.STREAM_URL}...")
try:
    stream = urllib.request.urlopen(config.STREAM_URL, timeout=5)
    print("✅ ¡Conectado! CONTROLES:")
    print(" [B] Blue ON (Avanzar)")
    print(" [R] Red ON  (Parar)")
    print(" [ESPACIO] Off (Neutro/Apagados)")
    print(" [Q] Salir")
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
                        key = cv2.waitKey(1) & 0xFF
                        
                        txt = "ESPERANDO..."
                        color = (200, 200, 200)

                        if key == ord('b'):
                            guardar_foto(frame, 'blue_on')
                            txt = "GRABANDO BLUE 🔵"
                            color = (255, 0, 0)
                        elif key == ord('r'):
                            guardar_foto(frame, 'red_on')
                            txt = "GRABANDO RED 🔴"
                            color = (0, 0, 255)
                        elif key == ord(' '): # Espacio
                            guardar_foto(frame, 'off')
                            txt = "GRABANDO OFF ⚫"
                            color = (100, 100, 100)
                        elif key == ord('q'):
                            break

                        # Info en pantalla
                        y = 20
                        for c in CLASES:
                            cv2.putText(display, f"{c}: {counts[c]}", (10, y), 
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 1)
                            y += 20
                        cv2.putText(display, txt, (10, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                        cv2.imshow('Recolector Semaforo', display)
    except Exception as e:
        print(e)
        break

cv2.destroyAllWindows()