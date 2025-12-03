# utils.py
import cv2
import urllib.request
import numpy as np
import threading
import config
import time

# Variable global para comandos
last_command = ""

def enviar_comando(comando):
    """Envía la orden al ESP32 de forma asíncrona"""
    global last_command
    def _send():
        try:
            urllib.request.urlopen(f"{config.CONTROL_URL}{comando}", timeout=0.1)
        except: pass
    threading.Thread(target=_send).start()
    last_command = comando

# --- CLASE DE VIDEO OPTIMIZADA (Salto de Frames) ---
class VideoStream:
    def __init__(self):
        self.url = config.STREAM_URL
        self.stream = None
        self.bytes = b''
        self.stopped = False
        self.frame = None
        self.lock = threading.Lock()
        self.conectar()

    def conectar(self):
        print(f"📡 Conectando al stream: {self.url}...")
        try:
            self.stream = urllib.request.urlopen(self.url, timeout=5)
            print("✅ Conexión establecida.")
        except Exception as e:
            print(f"❌ Error fatal: {e}")
            exit()

    def start(self):
        t = threading.Thread(target=self.update, args=())
        t.daemon = True
        t.start()
        return self

    def update(self):
        while not self.stopped:
            try:
                # Leemos un bloque grande de datos (4k o más)  8192
                chunk = self.stream.read(4096) # Aumentamos el buffer de lectura
                if len(chunk) == 0:
                    continue
                
                self.bytes += chunk
                
                # --- LÓGICA DE SALTO DE FRAMES (FRAME SKIPPING) ---
                # Buscamos el inicio y fin de un JPEG
                a = self.bytes.find(b'\xff\xd8')
                b = self.bytes.find(b'\xff\xd9')
                
                # Si tenemos un frame completo...
                if a != -1 and b != -1:
                    # TRUCO: ¿Hay MÁS frames esperando en la cola?
                    # Buscamos el ÚLTIMO inicio de frame en todo el buffer
                    last_a = self.bytes.rfind(b'\xff\xd8')
                    last_b = self.bytes.rfind(b'\xff\xd9')

                    if last_a > a and last_b > last_a:
                        # ¡Si hay uno más nuevo, saltamos directamente a ese!
                        # Descartamos todo lo anterior (frames viejos que causan lag)
                        a = last_a
                        b = last_b
                        
                    # Extraemos la imagen (la más nueva encontrada)
                    jpg = self.bytes[a:b+2]
                    
                    # Limpiamos el buffer hasta el final de este frame
                    self.bytes = self.bytes[b+2:]
                    
                    # Decodificamos
                    if len(jpg) > 0:
                        decoded = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                        if decoded is not None:
                            with self.lock:
                                self.frame = decoded
            except Exception as e:
                print(f"⚠️ Stream error: {e}")
                time.sleep(0.1) # Pequeña pausa para no saturar si falla

    def read(self):
        with self.lock:
            return self.frame

    def stop(self):
        self.stopped = True

# --- PREPROCESAMIENTO UNIFICADO ---
def preprocesar_imagen(frame):
    """240x320 RGB Normalizado"""
    # 1. Resize (Ancho=320, Alto=240)
    # Asegúrate que en config.py IMG_WIDTH=320 y IMG_HEIGHT=240
    img = cv2.resize(frame, (config.IMG_WIDTH, config.IMG_HEIGHT))
    
    # 2. Convertir a RGB
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # 3. Batch
    img = img.astype("float32")
    return np.expand_dims(img, axis=0)