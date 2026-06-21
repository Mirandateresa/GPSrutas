# app.py
from flask import Flask
from configuracion import Configuracion
from routes import registrar_rutas
import os
import logging

# Configurar logging para ver errores
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def crear_aplicacion(configuracion_prueba=None):
    aplicacion = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    aplicacion.config.from_object(Configuracion)

    # Configuración para Netlify
    if os.environ.get('NETLIFY'):
        aplicacion.config['DEPURACION'] = False
        if os.environ.get('GOOGLE_MAPS_API_KEY'):
            aplicacion.config['CLAVE_API_GOOGLE'] = os.environ['GOOGLE_MAPS_API_KEY']

    if configuracion_prueba:
        aplicacion.config.update(configuracion_prueba)

    registrar_rutas(aplicacion)
    return aplicacion

# Para Netlify Functions - DEBE llamarse "app"
app = crear_aplicacion()

# Para ejecución local
if __name__ == "__main__":
    port = int(os.environ.get("PORT", app.config.get("PUERTO", 5000)))
    debug = os.environ.get("DEBUG", "False").lower() == "true"
    
    logger.info(f"🚀 Iniciando servidor en puerto {port}, debug={debug}")
    app.run(
        host="0.0.0.0",
        port=port,
        debug=debug,
    )