#include "esp_http_server.h"
#include "esp_timer.h"
#include "esp_camera.h"
#include "stream_server.h"

// Define el tipo de contenido para un stream MJPEG
#define PART_BOUNDARY "123456789000000000000987654321"
static const char* _STREAM_CONTENT_TYPE = "multipart/x-mixed-replace;boundary=" PART_BOUNDARY;

// Manejador del stream: esta función se ejecuta cada vez que un navegador pide el /stream
static esp_err_t stream_handler(httpd_req_t *req){
  camera_fb_t * fb = NULL;
  esp_err_t res = ESP_OK;
  char * part_buf[64];
  
  // Envía la cabecera del stream
  res = httpd_resp_set_type(req, _STREAM_CONTENT_TYPE);
  if(res != ESP_OK){
    return res;
  }

  // Bucle infinito mientras el cliente esté conectado
  while(true){
    fb = esp_camera_fb_get(); // Obtiene un frame de la cámara
    if (!fb) {
      continue;
    }

    // Envía la cabecera de esta "parte" del stream (un frame JPG)
    res = httpd_resp_send_chunk(req, (const char *)part_buf, 
            sprintf((char *)part_buf, "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n", fb->len));

    if(res == ESP_OK){
      // Envía los datos de la imagen
      res = httpd_resp_send_chunk(req, (const char *)fb->buf, fb->len);
    }
    
    // Envía el delimitador de la "parte"
    if(res == ESP_OK){
      res = httpd_resp_send_chunk(req, "\r\n--" PART_BOUNDARY "\r\n", strlen("\r\n--" PART_BOUNDARY "\r\n"));
    }
    
    esp_camera_fb_return(fb); // Devuelve el buffer del frame
    
    if(res != ESP_OK){
      break; // Si hay un error (ej. cliente se desconectó), salimos
    }
  }
  return res;
}

// Función que inicia el servidor
void startCameraStreamServer(){
  httpd_handle_t stream_httpd = NULL;
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.server_port = 81; // Puerto 81
  config.ctrl_port = 81;   // Puerto de control (igual)

  // URI (ruta) para el stream
  httpd_uri_t stream_uri = {
    .uri       = "/stream",
    .method    = HTTP_GET,
    .handler   = stream_handler,
    .user_ctx  = NULL
  };

  // Inicia el servidor
  if (httpd_start(&stream_httpd, &config) == ESP_OK) {
    // Registra el manejador de la ruta /stream
    httpd_register_uri_handler(stream_httpd, &stream_uri);
  }
}