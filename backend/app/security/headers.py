"""Encabezados de seguridad que se agregan a todas las respuestas de la API."""


def registrar_encabezados(app):
    @app.after_request
    def agregar_encabezados(respuesta):
        # Evita que el navegador "adivine" el tipo de contenido (ataques por MIME sniffing)
        respuesta.headers["X-Content-Type-Options"] = "nosniff"
        # Impide que la API se muestre dentro de un iframe de otro sitio (clickjacking)
        respuesta.headers["X-Frame-Options"] = "DENY"
        # Las respuestas llevan datos personales: que no queden guardadas en caches
        respuesta.headers["Cache-Control"] = "no-store"
        return respuesta