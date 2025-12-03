import cv2
import urllib.request
import numpy as np

# --- CONFIGURACIÓN ---
url = 'http://192.168.1.113:81/stream'  # TU IP CORRECTA

print(f"Conectando a {url}...")

try:
    stream = urllib.request.urlopen(url, timeout=5)
    print("✅ ¡Conexión establecida! (Ignora el aviso de Wayland)")
except Exception as e:
    print(f"❌ Error fatal al conectar: {e}")
    exit()

bytes_data = b''

while True:
    try:
        # Leemos en bloques (4096 es buen tamaño)
        bytes_data += stream.read(4096)
        
        # 1. Buscamos el inicio del frame (0xFF 0xD8)
        a = bytes_data.find(b'\xff\xd8')
        
        if a != -1:
            # 2. Si encontramos inicio, buscamos el final (0xFF 0xD9)
            # IMPORTANTE: Buscamos el final A PARTIR del inicio (a)
            b = bytes_data.find(b'\xff\xd9', a)
            
            if b != -1:
                # Tenemos un frame completo desde 'a' hasta 'b+2'
                jpg = bytes_data[a:b+2]
                
                # Actualizamos el buffer: borramos lo viejo y dejamos lo que sobre
                # para el siguiente frame
                bytes_data = bytes_data[b+2:]
                
                # Decodificamos
                if len(jpg) > 0:
                    frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                    
                    if frame is not None:
                        # --- AQUÍ VA TU LÓGICA DE IA ---
                        
                        # Mostramos el frame
                        cv2.imshow('Video ESP32', frame)
                
                # Si presionas 'q' sales
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            else:
                # Tenemos inicio pero no final. 
                # No hacemos nada, esperamos a leer más datos en la siguiente vuelta.
                pass
        else:
            # No hay inicio de frame en todo el buffer.
            # Podemos limpiar el buffer para que no crezca infinito si hay basura.
            # (Pero dejamos los últimos bytes por si el header se cortó a la mitad)
            if len(bytes_data) > 100000: # Seguridad
                bytes_data = b''
                
    except Exception as e:
        print(f"Error en el bucle: {e}")
        break

cv2.destroyAllWindows()