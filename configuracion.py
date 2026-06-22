# configuracion.py
from pathlib import Path
import os

DIRECTORIO_BASE = Path(__file__).resolve().parent

class Configuracion:
    # ====== OSRM (Open Source Routing Machine) ======
    URL_OSRM = "https://router.project-osrm.org"
    
    # ====== NOMINATIM (geocodificación) ======
    URL_NOMINATIM = "https://nominatim.openstreetmap.org"
    USER_AGENT = "GPS-RutasSeguras/1.0"

    TIPO_VEHICULO_PREDETERMINADO = "GASOLINE"
    PRECIO_GASOLINA_MXN = 23.99
    RENDIMIENTO_PREDETERMINADO_KM_L = 14.0

    ARCHIVO_ZONAS = DIRECTORIO_BASE / "data" / "zonas_rojas.json"
    
    TIEMPO_ESPERA_SEGUNDOS = 30

    SERVIDOR = "0.0.0.0"
    PUERTO = int(os.environ.get("PORT", 5000))
    DEPURACION = os.environ.get("DEBUG", "True").lower() == "true"

    JSON_SORT_KEYS = False
    JSON_AS_ASCII = False

    OPTIMIZACION_ACTIVADA = False
    OPTIMIZACION_ITERACIONES = 20
    OPTIMIZACION_PENALIZACION_ZONA = 100.0
    OPTIMIZACION_PESO_DISTANCIA = 1.0
    OPTIMIZACION_PESO_PEAJE = 0.5
    OPTIMIZACION_PESO_TIEMPO = 0.1