import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
import os

# ==========================================
#  CONFIGURACIÓN
# ==========================================

# Carpeta con tus fotos (W, W+A, W+D)
DATA_DIR = 'driving/dataset_pista_vectorial'

# Dimensiones originales de la cámara (Coincide con config.py)
IMG_HEIGHT = 240
IMG_WIDTH = 320

# Recorte: Quitamos 100 pixeles de arriba
CROP_TOP = 100
INPUT_HEIGHT = IMG_HEIGHT - CROP_TOP  # 140

BATCH_SIZE = 32
EPOCHS = 5  # Unas 20 épocas está bien

print(f"--- CONFIGURACIÓN DE ENTRENAMIENTO ---")
print(f"Entrada original: {IMG_WIDTH}x{IMG_HEIGHT}")
print(f"Entrada a la IA:  {IMG_WIDTH}x{INPUT_HEIGHT}")

# ==========================================
# 1. CARGAR DATASET 
# ==========================================
print("\nCargando imágenes...")

# Entrenamiento (80%)
train_ds = tf.keras.utils.image_dataset_from_directory(
  DATA_DIR,
  validation_split=0.2,
  subset="training",
  seed=123,
  image_size=(IMG_HEIGHT, IMG_WIDTH),
  batch_size=BATCH_SIZE,
  label_mode='categorical' 
)

# Validación (20%)
val_ds = tf.keras.utils.image_dataset_from_directory(
  DATA_DIR,
  validation_split=0.2,
  subset="validation",
  seed=123,
  image_size=(IMG_HEIGHT, IMG_WIDTH),
  batch_size=BATCH_SIZE,
  label_mode='categorical' 
)

class_names = train_ds.class_names
print(f"Clases detectadas: {class_names}")

# ==========================================
# 2. PREPROCESAMIENTO (RECORTE)
# ==========================================
def process_data(img, label):
    """Recorta la parte superior de la imagen"""
    img_cropped = tf.image.crop_to_bounding_box(img, CROP_TOP, 0, INPUT_HEIGHT, IMG_WIDTH)
    return img_cropped, label

# Aplicar recorte
train_ds = train_ds.map(process_data)
val_ds = val_ds.map(process_data)

# Optimización de carga
AUTOTUNE = tf.data.AUTOTUNE
train_ds = train_ds.cache().shuffle(1000).prefetch(buffer_size=AUTOTUNE)
val_ds = val_ds.cache().prefetch(buffer_size=AUTOTUNE)

# ==========================================
# 3. MODELO (Arquitectura Turbo)
# ==========================================
num_classes = len(class_names)

model = keras.Sequential([
  # Entrada explícita (140, 320, 3)
  layers.InputLayer(input_shape=(INPUT_HEIGHT, IMG_WIDTH, 3)),
  
  layers.Rescaling(1./255),
  layers.RandomZoom(0.1),
  layers.RandomContrast(0.1),

  # Bloques convolucionales
  layers.Conv2D(16, 3, padding='same', activation='relu'),
  layers.MaxPooling2D(),
  layers.Conv2D(32, 3, padding='same', activation='relu'),
  layers.MaxPooling2D(),
  layers.Conv2D(32, 3, padding='same', activation='relu'),
  layers.MaxPooling2D(),
  
  # Clasificación
  layers.Flatten(),
  layers.Dense(64, activation='relu'),
  layers.Dropout(0.5),
  layers.Dense(num_classes, activation='softmax')
])

model.compile(optimizer='adam',
              loss='categorical_crossentropy', # Funciona con label_mode='categorical'
              metrics=['accuracy'])

model.summary()

# ==========================================
# 4. ENTRENAR Y GUARDAR
# ==========================================
print("\nIniciando entrenamiento...")
history = model.fit(
  train_ds,
  validation_data=val_ds,
  epochs=EPOCHS
)

print("\nGuardando modelo...")
model.save('driving/modelo_pista_vectorial.h5')
print(" ¡Modelo guardado exitosamente!")

# Gráficos
acc = history.history['accuracy']
val_acc = history.history['val_accuracy']
loss = history.history['loss']
val_loss = history.history['val_loss']
epochs_range = range(EPOCHS)

plt.figure(figsize=(8, 8))
plt.subplot(1, 2, 1)
plt.plot(epochs_range, acc, label='Training Accuracy')
plt.plot(epochs_range, val_acc, label='Validation Accuracy')
plt.legend(loc='lower right')
plt.title('Precisión')

plt.subplot(1, 2, 2)
plt.plot(epochs_range, loss, label='Training Loss')
plt.plot(epochs_range, val_loss, label='Validation Loss')
plt.legend(loc='upper right')
plt.title('Pérdida')
plt.show()