import cv2
import numpy as np
import tensorflow as tf
import time
import threading
import sys
import os

# Importación segura
try:
    import config
    import utils
except ImportError:
    print("❌ Error: Faltan config.py o utils.py")
    exit()

print("\n--- INICIANDO KART GPT (ASÍNCRONO) ---")

# ==========================================
# 1. VARIABLES COMPARTIDAS (MEMORIA GLOBAL)
# ==========================================
# Estas variables se leen/escriben desde distintos hilos
current_mode = 0  # 0: Espera (Semáforo), 1: Auto (Pista)
current_frame = None
current_text = "INICIANDO..."
current_color = (255, 255, 255)
estado_direccion = 'centro' # Memoria de ruedas
running = True # Bandera para detener todos los hilos al salir

# ==========================================
# 2. CARGA DE MODELOS
# ==========================================
print("🧠 Cargando modelos en memoria...")
try:
    model_led = tf.keras.models.load_model(config.MODEL_PATH_LED)
    model_drive = tf.keras.models.load_model(config.MODEL_PATH_DRIVE)
    print("✅ Modelos cargados.")
except Exception as e:
    print(f"❌ Error cargando modelos: {e}")
    exit()

# ==========================================
# 3. HILO DE INTELIGENCIA (CEREBRO)
# ==========================================
def control_loop():
    """
    Este hilo se dedica EXCLUSIVAMENTE a pensar y enviar comandos.
    No bloquea el video.
    """
    global current_mode, current_text, current_color, estado_direccion
    
    print("🚀 Cerebro IA iniciado.")
    
    while running:
        # 1. Obtenemos la foto más actual (sin sacarla del video, solo leemos)
        # Si el video va más rápido que la IA, la IA se salta fotos (Frame Dropping),
        # lo cual es BUENO porque siempre reacciona a lo último que pasó.
        frame = current_frame
        
        if frame is None:
            time.sleep(0.1)
            continue

        # 2. Preprocesamiento
        try:
            # Usamos la función unificada de utils (Devuelve 240x320 completo)
            input_data = utils.preprocesar_imagen(frame)
            
            # --- MODO SEMÁFORO ---
            if current_mode == 0: # MODE_WAITING_SIGNAL
                # Usamos imagen completa
                preds = model_led.predict(input_data, verbose=0)
                score = tf.nn.softmax(preds[0])
                idx = np.argmax(score)
                clase = config.CLASSES_LEDS[idx]
                confianza = 100 * np.max(score)
                
                # Lógica
                if confianza > (config.CONFIDENCE_LED * 100):
                    if clase == 'blue_on':
                        current_text = f"GO! ({confianza:.0f}%)"
                        current_color = (0, 255, 0) # Verde
                        utils.enviar_comando("/parar_propulsion")
                        current_mode = 1 # CAMBIO A AUTO
                    elif clase == 'red_on':
                        current_text = f"STOP ({confianza:.0f}%)"
                        current_color = (0, 0, 255)
                        utils.enviar_comando("/parar_propulsion")
                    else:
                        current_text = "ESPERANDO..."
                        current_color = (0, 255, 255)
                        utils.enviar_comando("/parar_propulsion")
                else:
                    current_text = "BUSCANDO SEÑAL..."
                    current_color = (200, 200, 200)
                    utils.enviar_comando("/parar_propulsion")

            # --- MODO PILOTO AUTOMÁTICO ---
            elif current_mode == 1: # MODE_AUTOPILOT
                # Recortamos el techo manualmente (CROP_TOP)
                # Input: [Batch, Alto, Ancho, Canales]
                input_recortado = input_data[:, config.CROP_TOP:, :, :]
                
                preds = model_drive.predict(input_recortado, verbose=0)
                score = tf.nn.softmax(preds[0])
                idx = np.argmax(score)
                clase = config.CLASSES_DRIVE[idx]
                confianza = 100 * np.max(score)
                
                # Tiempos desde config
                t_paso = config.TIEMPO_PASO
                t_pausa = config.TIEMPO_PAUSA

                if confianza > (config.CONFIDENCE_DRIVE * 100):
                    if clase == 'avanzar':
                        # Lógica de memoria (sin centrado activo, solo estado)
                        if estado_direccion == 'izquierda':
                            # Si quieres centrar, descomenta:
                            # utils.enviar_comando("/derecha"); time.sleep(0.1); utils.enviar_comando("/parar_direccion")
                            estado_direccion = 'centro'
                        elif estado_direccion == 'derecha':
                            # utils.enviar_comando("/izquierda"); time.sleep(0.1); utils.enviar_comando("/parar_direccion")
                            estado_direccion = 'centro'
                        
                        utils.enviar_comando("/avanzar")
                        time.sleep(t_paso)
                        utils.enviar_comando("/parar_propulsion")
                        
                        current_text = "RECTO ^"
                        current_color = (0, 255, 0)

                    elif clase == 'avanzar_izquierda':
                        if estado_direccion != 'izquierda':
                            utils.enviar_comando("/izquierda")
                            time.sleep(0.1)
                            utils.enviar_comando("/parar_direccion")
                            estado_direccion = 'izquierda'
                        
                        utils.enviar_comando("/avanzar")
                        time.sleep(t_paso)
                        utils.enviar_comando("/parar_propulsion")
                        
                        current_text = "IZQUIERDA <"
                        current_color = (255, 0, 0)

                    elif clase == 'avanzar_derecha':
                        if estado_direccion != 'derecha':
                            utils.enviar_comando("/derecha")
                            time.sleep(0.1)
                            utils.enviar_comando("/parar_direccion")
                            estado_direccion = 'derecha'
                        
                        utils.enviar_comando("/avanzar")
                        time.sleep(t_paso)
                        utils.enviar_comando("/parar_propulsion")
                        
                        current_text = "DERECHA >"
                        current_color = (0, 0, 255)
                else:
                    utils.enviar_comando("/parar_propulsion")
                    current_text = "DUDANDO..."
                    current_color = (0, 255, 255)
                
                # Pausa para que el PC "piense" o para controlar velocidad
                # Esto SOLO frena la IA, no el video.
                if t_pausa > 0:
                    time.sleep(t_pausa)

        except Exception as e:
            print(f"⚠️ Error en hilo de control: {e}")
            time.sleep(0.5) # Espera un poco si hay error

# ==========================================
# 4. BLOQUE PRINCIPAL (DISPLAY)
# ==========================================
if __name__ == '__main__':
    
    # 1. Iniciar Video (Hilo interno de utils)
    video_stream = utils.VideoStream().start()
    
    # Esperar a que llegue la primera imagen
    print("Esperando video...")
    while video_stream.read() is None:
        time.sleep(0.1)
    
    # 2. Iniciar Cerebro (Hilo definido arriba)
    thread_ia = threading.Thread(target=control_loop)
    thread_ia.daemon = True
    thread_ia.start()

    print("🏁 Sistema corriendo. Presiona 'q' para salir.")

    # 3. Bucle de Visualización (Hilo Principal)
    # Este bucle va tan rápido como pueda refrescar la pantalla (independiente de la IA)
    while True:
        try:
            # Leemos el frame del objeto video (que se actualiza solo)
            frame = video_stream.read()
            
            # Actualizamos la variable global para que la lea la IA
            if frame is not None:
                current_frame = frame.copy() # Copia para evitar conflictos de lectura/escritura

                # --- DIBUJAR HUD ---
                # Usamos las variables globales current_text, current_color que actualiza la IA
                
                # Barra superior negra
                cv2.rectangle(frame, (0, 0), (config.IMG_WIDTH, 60), (0, 0, 0), -1)
                
                # Texto de estado
                modo_str = "ESPERA" if current_mode == 0 else "AUTO"
                cv2.putText(frame, f"MODO: {modo_str}", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                cv2.putText(frame, current_text, (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, current_color, 2)

                # Líneas guía
                if current_mode == 1:
                     cv2.line(frame, (0, config.CROP_TOP), (config.IMG_WIDTH, config.CROP_TOP), (255, 0, 255), 1)
                
                cv2.imshow('KART GPT - ASINCRONO', frame)

            # Salir
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("🛑 Deteniendo...")
                running = False # Detiene el hilo de IA
                video_stream.stop() # Detiene el hilo de video
                utils.enviar_comando("/parar_todo")
                break
            
            # Pequeña pausa para no quemar la CPU en el refresco de pantalla
            time.sleep(0.01)

        except KeyboardInterrupt:
            running = False
            video_stream.stop()
            break

    cv2.destroyAllWindows()
    sys.exit()