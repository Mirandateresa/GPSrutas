# configuracion.py
from pathlib import Path
import os

DIRECTORIO_BASE = Path(__file__).resolve().parent

class Configuracion:
    # Leer clave desde variable de entorno
    CLAVE_API_GOOGLE = os.environ.get(
        "GOOGLE_MAPS_API_KEY",
        "AIzaSyBI7-JK1Ll0OQGwG7n0tTdkQAYRDN4f094"
    )

    TIPO_VEHICULO_PREDETERMINADO = "GASOLINE"
    PRECIO_GASOLINA_MXN = 23.99
    RENDIMIENTO_PREDETERMINADO_KM_L = 14.0

    ARCHIVO_ZONAS = DIRECTORIO_BASE / "data" / "zonas_rojas.json"
    
    # 🔥 REDUCIDO DE 35 A 25 SEGUNDOS
    TIEMPO_ESPERA_GOOGLE_SEGUNDOS = int(os.environ.get("TIEMPO_ESPERA_GOOGLE_SEGUNDOS", 25))

    SERVIDOR = "0.0.0.0"
    PUERTO = int(os.environ.get("PORT", 5000))
    DEPURACION = os.environ.get("DEBUG", "True").lower() == "true"

    JSON_SORT_KEYS = False
    JSON_AS_ASCII = False

    OPTIMIZACION_ACTIVADA = True
    OPTIMIZACION_ITERACIONES = 50
    OPTIMIZACION_PENALIZACION_ZONA = 100.0
    OPTIMIZACION_PESO_DISTANCIA = 1.0
    OPTIMIZACION_PESO_PEAJE = 0.5
    OPTIMIZACION_PESO_TIEMPO = 0.1