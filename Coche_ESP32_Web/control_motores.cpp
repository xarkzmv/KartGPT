#include <Arduino.h>
#include "control_motores.h" // Incluimos su propio archivo de cabecera

// --- Configuración de Hardware ---
#define PWM_FREQ 5000
#define PWM_RESOLUTION 8
const int MIN_MOTOR_SPEED = 150;

// --- Definición de Pines ---
// Motor A (Propulsión)
const int pin_A_adelante = 13; // in 1
const int pin_A_atras = 12; // in 2
// Motor B (Dirección)
const int pin_B_derecha = 15; // in 3
const int pin_B_izquierda = 14; // in 4

// --- Implementación de Funciones ---

/**
 * @brief Calcula el valor PWM real basado en la velocidad mínima
 */
int calcularPWM(int vel) {
  if (vel == 0) return 0;
  return map(vel, 1, 255, MIN_MOTOR_SPEED, 255);
}

/**
 * @brief Configura todos los pines y el PWM para los motores
 */
void setupMotores() {
  ledcAttach(pin_A_adelante, PWM_FREQ, PWM_RESOLUTION);
  ledcAttach(pin_A_atras, PWM_FREQ, PWM_RESOLUTION);
  ledcAttach(pin_B_derecha, PWM_FREQ, PWM_RESOLUTION);
  ledcAttach(pin_B_izquierda, PWM_FREQ, PWM_RESOLUTION);
  parar_propulsion();
  parar_direccion();
}

void avanzar(int vel) {
  int motorPWM = calcularPWM(vel);
  ledcWrite(pin_A_adelante, motorPWM);
  ledcWrite(pin_A_atras, 0);
}

void retroceder(int vel) {
  int motorPWM = calcularPWM(vel);
  ledcWrite(pin_A_adelante, 0);
  ledcWrite(pin_A_atras, motorPWM);
}

void parar_propulsion() {
  ledcWrite(pin_A_adelante, 0);
  ledcWrite(pin_A_atras, 0);
}

void girar_direccion(int vel, int dir) {
  int motorPWM = calcularPWM(vel);
  if (dir == DER) {
    ledcWrite(pin_B_derecha, motorPWM);
    ledcWrite(pin_B_izquierda, 0);
  } else if (dir == IZQ) {
    ledcWrite(pin_B_derecha, 0);
    ledcWrite(pin_B_izquierda, motorPWM);
  }
}

void parar_direccion() {
  ledcWrite(pin_B_derecha, 0);
  ledcWrite(pin_B_izquierda, 0);
}