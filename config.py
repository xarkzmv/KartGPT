# Todas las constantes IP, URL y Tamaños aquí.

# config.py
import os 

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- CONEXIÓN ---
ESP_IP = "coche-esp32.local"  # <--- PON TU IP AQUÍ
STREAM_URL = f"http://{ESP_IP}:81/stream"
CONTROL_URL = f"http://{ESP_IP}"

# --- MODELOS ---
MODEL_PATH_DRIVE = os.path.join(BASE_DIR, 'modelo_pista_vectorial.h5')
MODEL_PATH_LED = os.path.join(BASE_DIR, './', 'led_recognition','mi_modelo_leds.h5')
# MODEL_PATH_DRIVE = 'modelo_pista_vectorial.h5'
# MODEL_PATH_LED = './led_recognition/mi_modelo_leds.h5'



# # --- IMAGEN ---
# Dimensiones exactas de tus entrenamientos
IMG_HEIGHT = 240
IMG_WIDTH = 320

# --- DIMENSIONES DE RECORTE (Lo que ve la IA) ---
# Quitamos 100 pixeles de arriba (Ruido visual)
# La altura final que entra a la red será: 240 - 100 = 140 pixeles
CROP_TOP = 100

# --- CLASES ---
# Asegúrate que este orden coincida con tus entrenamientos
CLASSES_LEDS = ['blue_on', 'off', 'red_on']
CLASSES_DRIVE = ['avanzar', 'avanzar_derecha', 'avanzar_izquierda']

# --- UMBRALES ---
CONFIDENCE_LED = 0.5  # Confianza alta para arrancar
CONFIDENCE_DRIVE = 0.22  # Confianza media para conducir rápido

# --- CALIBRACIÓN DE MOVIMIENTO (DRIVING) ---
TIEMPO_PASO = 0.1
TIEMPO_PAUSA = 0.5
TIEMPO_CENTRADO = 0.15