#ifndef CONTROL_MOTORES_H
#define CONTROL_MOTORES_H

// --- Constantes de Control ---
#define IZQ -1
#define DER 1

// --- Declaración de Funciones ---
// (Estas son las funciones que el .ino principal podrá llamar)

void setupMotores();
void avanzar(int vel);
void retroceder(int vel);
void parar_propulsion();
void girar_direccion(int vel, int dir);
void parar_direccion();

#endif