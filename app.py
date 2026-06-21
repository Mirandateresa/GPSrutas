from flask import Flask
from configuracion import Configuracion
from routes import registrar_rutas
import os


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
    app.run(
        host=app.config.get("SERVIDOR", "0.0.0.0"),
        port=app.config.get("PUERTO", 5000),
        debug=app.config.get("DEPURACION", True),
    )