# Análisis Comparativo de Tráfico de Red: HTTP vs. HTTPS (TLS/SSL)

## 1. Introducción y Objetivo
El objetivo de este análisis es evaluar la seguridad del tráfico de red en la aplicación **sistema-gestion-turnos-pami** mediante la captura y análisis de paquetes con **Wireshark**. Se comparan dos escenarios: transmisión en texto plano (HTTP) y transmisión cifrada mediante TLS/SSL (HTTPS).

---

## 2. Entorno y Configuración

* **Backend:** Flask ejecutándose en `127.0.0.1:5000`.
* **Seguridad:** Certificados SSL/TLS autofirmados (`cert.pem` y `key.pem`) cargados dinámicamente mediante variables de entorno (`SSL_CERT_FILE`, `SSL_KEY_FILE`).
* **Herramienta de Análisis:** Wireshark v4.x.
* **Interfaz de Captura:** `Adapter for loopback traffic capture` (tráfico local `127.0.0.1`).
* **Filtro Aplicado:** `tcp.port == 5000`.

---

## 3. Análisis de Resultados

### Escenario A: Tráfico HTTP Estándar (Sin Cifrado)
* **Estado del servidor:** SSL/TLS desactivado en `.env`.
* **Comportamiento en Wireshark:** 
  * Se interceptaron los paquetes de la transacción web en la interfaz loopback.
  * Al aplicar `Follow -> TCP Stream`, se observó el flujo completo en **texto plano**.
  * **Datos Expuestos:** Cabeceras de petición HTTP (`User-Agent`, `Host`), la solicitud `GET /`, y la respuesta del servidor (`HTTP/1.1 404 NOT FOUND` junto con la estructura del cuerpo HTML).
* **Riesgo:** Cualquier atacante con acceso a la red (vía sniffing o ataque Man-in-the-Middle) puede interceptar y leer datos sensibles como credenciales, cookies de sesión o información médica.

### Escenario B: Tráfico HTTPS (Cifrado TLS/SSL)
* **Estado del servidor:** SSL/TLS activo con `cert.pem` y `key.pem`.
* **Comportamiento en Wireshark:**
  * Se registró la negociación inicial **TLS Handshake** (`Client Hello`, `Server Hello`).
  * Los paquetes subsiguientes de la aplicación fueron clasificados como datos cifrados (`Application Data` / `TLSv1.2`/`v1.3`).
  * Al aplicar `Follow -> TCP Stream / TLS Stream`, la información transmitida resultó ser completamente **ilegible y cifrada** (bloque binario).
* **Beneficio:** Garantiza la confidencialidad e integridad de la comunicación entre el cliente y el backend.

---

## 4. Conclusión
La implementación de HTTPS en la API asegura que los datos sensibles gestionados por la plataforma (turnos médicos, datos de afiliados PAMI y credenciales de acceso) viajen protegidos por la red, mitigando ataques de interceptación y cumpliendo con los estándares de seguridad requeridos para el Sprint 3.