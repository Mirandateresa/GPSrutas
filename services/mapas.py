import requests
import logging

from services.motor_rutas import seleccionar_mejor_ruta, decodificar_polilinea
from services.casetas import encontrar_peajes
from services.zonas import zonas_intersectan_ruta
from services.optimizador import OptimizadorRutas

# Configurar logging
logger = logging.getLogger(__name__)

URL_GEOCODIFICACION = "https://maps.googleapis.com/maps/api/geocode/json"
URL_RUTAS = "https://routes.googleapis.com/directions/v2:computeRoutes"
URL_DIRECTIONS = "https://maps.googleapis.com/maps/api/directions/json"  # ← NUEVO
CAMPOS_RUTAS = ",".join([
    "routes.distanceMeters",
    "routes.duration",
    "routes.polyline.encodedPolyline",
    "routes.travelAdvisory.tollInfo",
    "routes.legs.travelAdvisory.tollInfo",
    "routes.legs.steps",
])


class ErrorGoogleMaps(RuntimeError):
    pass


def _validar_clave(clave_api):
    clave = str(clave_api or "").strip()
    if not clave or clave.upper().startswith("COLOCA_AQUI"):
        raise ErrorGoogleMaps(
            "Configura CLAVE_API_GOOGLE dentro de configuracion.py antes de calcular rutas."
        )
    return clave


def _componente_direccion(componentes, tipos_aceptados):
    for componente in componentes:
        if any(elemento in componente.get("types", []) for elemento in tipos_aceptados):
            return componente.get("long_name", "")
    return ""


def geocodificar(direccion, clave_api, tiempo_espera=35):
    clave_api = _validar_clave(clave_api)
    respuesta = requests.get(
        URL_GEOCODIFICACION,
        params={
            "address": direccion,
            "region": "mx",
            "language": "es",
            "key": clave_api,
        },
        timeout=tiempo_espera,
    )
    respuesta.raise_for_status()
    contenido = respuesta.json()

    if contenido.get("status") != "OK" or not contenido.get("results"):
        detalle = contenido.get("error_message") or contenido.get("status") or "sin resultados"
        raise ErrorGoogleMaps(f"No se encontró la dirección: {detalle}.")

    resultado = contenido["results"][0]
    ubicacion = resultado.get("geometry", {}).get("location", {})
    componentes = resultado.get("address_components", [])
    ciudad = _componente_direccion(componentes, ["locality", "postal_town"])
    if not ciudad:
        ciudad = _componente_direccion(
            componentes,
            ["administrative_area_level_2", "sublocality"],
        )

    return {
        "lat": float(ubicacion["lat"]),
        "lng": float(ubicacion["lng"]),
        "address": resultado.get("formatted_address", direccion),
        "city": ciudad,
        "state": _componente_direccion(componentes, ["administrative_area_level_1"]),
        "country": _componente_direccion(componentes, ["country"]),
        "place_id": resultado.get("place_id", ""),
    }


def _duracion_segundos(valor):
    texto = str(valor or "0s").strip()
    try:
        return float(texto[:-1]) if texto.endswith("s") else 0.0
    except ValueError:
        return 0.0


def _valor_monetario(dinero):
    try:
        unidades = float(dinero.get("units", 0) or 0)
        nanos = float(dinero.get("nanos", 0) or 0)
    except (TypeError, ValueError):
        return 0.0
    return round(unidades + nanos / 1_000_000_000, 2)


def _combinar_info_peajes(ruta):
    aviso = ruta.get("travelAdvisory", {})
    peaje_ruta = aviso.get("tollInfo")
    if peaje_ruta and peaje_ruta.get("estimatedPrice"):
        return peaje_ruta, True

    totales = {}
    hay_peaje = "tollInfo" in aviso
    for tramo in ruta.get("legs", []):
        aviso_tramo = tramo.get("travelAdvisory", {})
        if "tollInfo" not in aviso_tramo:
            continue
        hay_peaje = True
        for precio in aviso_tramo.get("tollInfo", {}).get("estimatedPrice", []):
            moneda = precio.get("currencyCode", "MXN")
            totales[moneda] = totales.get(moneda, 0.0) + _valor_monetario(precio)

    if not totales:
        return {}, hay_peaje

    precios = []
    for moneda, total in totales.items():
        unidades = int(total)
        nanos = int(round((total - unidades) * 1_000_000_000))
        precios.append({
            "currencyCode": moneda,
            "units": str(unidades),
            "nanos": nanos,
        })
    return {"estimatedPrice": precios}, True


def _resumen_peajes(ruta):
    informacion_peaje, presente = _combinar_info_peajes(ruta)
    precios = informacion_peaje.get("estimatedPrice", [])
    if not precios:
        return {
            "has_tolls": presente,
            "price_available": False,
            "cost": 0.0,
            "currency": "MXN",
        }

    seleccionada = next(
        (precio for precio in precios if precio.get("currencyCode") == "MXN"),
        precios[0],
    )
    return {
        "has_tolls": True,
        "price_available": True,
        "cost": _valor_monetario(seleccionada),
        "currency": seleccionada.get("currencyCode", "MXN"),
    }


def _valores_vehiculo(tipo_vehiculo):
    solicitado = str(tipo_vehiculo or "GASOLINE").strip().upper()
    if solicitado not in {"GASOLINE", "TRUCK"}:
        raise ErrorGoogleMaps("El tipo de vehículo debe ser GASOLINE o TRUCK.")
    return solicitado, "DIESEL" if solicitado == "TRUCK" else "GASOLINE"


def calcular_rutas_google(origen, destino, tipo_vehiculo, clave_api, tiempo_espera=35):
    """Intenta Routes API primero, fallback a Directions API si falla."""
    clave_api = _validar_clave(clave_api)
    
    try:
        logger.info("🔄 Intentando Routes API...")
        return _calcular_rutas_routes_api(origen, destino, tipo_vehiculo, clave_api, tiempo_espera)
    except ErrorGoogleMaps as e:
        error_msg = str(e)
        if "no devolvió rutas" in error_msg.lower() or "404" in error_msg:
            logger.warning(f"⚠️ Routes API falló: {error_msg[:100]}. Intentando Directions API...")
            return _calcular_rutas_directions_api(origen, destino, tipo_vehiculo, clave_api, tiempo_espera)
        raise


def _calcular_rutas_routes_api(origen, destino, tipo_vehiculo, clave_api, tiempo_espera=35):
    """Calcula rutas usando Routes API (nueva)."""
    tipo_solicitado, tipo_emision = _valores_vehiculo(tipo_vehiculo)

    cuerpo = {
        "origin": {
            "location": {
                "latLng": {"latitude": origen[0], "longitude": origen[1]}
            }
        },
        "destination": {
            "location": {
                "latLng": {"latitude": destino[0], "longitude": destino[1]}
            }
        },
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_AWARE",
        "computeAlternativeRoutes": True,
        "polylineQuality": "HIGH_QUALITY",
        "polylineEncoding": "ENCODED_POLYLINE",
        "languageCode": "es-MX",
        "regionCode": "MX",
        "units": "METRIC",
        "extraComputations": ["TOLLS"],
        "routeModifiers": {
            "avoidTolls": False,
            "vehicleInfo": {"emissionType": tipo_emision},
        },
    }

    respuesta = requests.post(
        URL_RUTAS,
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": clave_api,
            "X-Goog-FieldMask": CAMPOS_RUTAS,
        },
        json=cuerpo,
        timeout=tiempo_espera,
    )

    if not respuesta.ok:
        try:
            detalle = respuesta.json()
        except ValueError:
            detalle = respuesta.text
        raise ErrorGoogleMaps(
            f"El servicio de rutas no pudo calcular la ruta ({respuesta.status_code}): {detalle}"
        )

    rutas = []
    for indice, ruta in enumerate(respuesta.json().get("routes", [])):
        distancia_m = int(ruta.get("distanceMeters", 0) or 0)
        duracion_s = _duracion_segundos(ruta.get("duration", "0s"))
        peaje = _resumen_peajes(ruta)
        advertencias = []

        if tipo_solicitado == "TRUCK":
            advertencias.append(
                "No se dispone de una tarifa comercial específica para camión; "
                "se usa DIESEL como tipo de emisión."
            )
        if peaje["has_tolls"] and not peaje["price_available"]:
            advertencias.append(
                "Se detectaron peajes, pero no se recibió un precio estimado."
            )

        rutas.append({
            "index": indice,
            "polyline": ruta.get("polyline", {}).get("encodedPolyline", ""),
            "legs": ruta.get("legs", []),
            "distance_m": distancia_m,
            "distance_km": round(distancia_m / 1000, 2),
            "duration_s": round(duracion_s),
            "duration_min": round(duracion_s / 60),
            "toll_cost": peaje["cost"],
            "toll_currency": peaje["currency"],
            "has_tolls": peaje["has_tolls"],
            "toll_price_available": peaje["price_available"],
            "vehicle_type": tipo_solicitado,
            "emission_type": tipo_emision,
            "toll_warnings": advertencias,
        })

    if not rutas:
        raise ErrorGoogleMaps("El servicio de rutas no devolvió rutas disponibles.")
    
    logger.info(f"✅ Routes API devolvió {len(rutas)} rutas")
    return rutas


def _calcular_rutas_directions_api(origen, destino, tipo_vehiculo, clave_api, tiempo_espera=35):
    """Calcula rutas usando Directions API (clásica, más compatible)."""
    tipo_solicitado, _ = _valores_vehiculo(tipo_vehiculo)
    
    params = {
        "origin": f"{origen[0]},{origen[1]}",
        "destination": f"{destino[0]},{destino[1]}",
        "key": clave_api,
        "language": "es",
        "region": "mx",
        "alternatives": "true",
        "units": "metric",
        "mode": "driving",
    }
    
    if tipo_solicitado == "TRUCK":
        params["vehicle"] = "truck"
        params["transit_routing_preference"] = "less_driving"
    
    respuesta = requests.get(
        URL_DIRECTIONS,
        params=params,
        timeout=tiempo_espera,
    )
    
    if not respuesta.ok:
        raise ErrorGoogleMaps(f"Directions API: Error HTTP {respuesta.status_code}")
    
    datos = respuesta.json()
    
    if datos.get("status") != "OK":
        raise ErrorGoogleMaps(f"Directions API: {datos.get('status')} - {datos.get('error_message', '')}")
    
    rutas = []
    for indice, ruta in enumerate(datos.get("routes", [])):
        # Extraer polilínea
        polyline = ruta.get("overview_polyline", {}).get("points", "")
        
        # Extraer distancia y duración
        legs = ruta.get("legs", [])
        distancia_m = 0
        duracion_s = 0
        has_tolls = False
        
        for leg in legs:
            distancia_m += leg.get("distance", {}).get("value", 0)
            duracion_s += leg.get("duration", {}).get("value", 0)
            # Verificar si hay peajes en los pasos
            for step in leg.get("steps", []):
                if "toll" in str(step.get("html_instructions", "")).lower():
                    has_tolls = True
        
        # Estimación de peaje (Directions API no da costo exacto)
        toll_cost = 150.0 if has_tolls else 0.0  # Estimación simple
        
        rutas.append({
            "index": indice,
            "polyline": polyline,
            "legs": legs,
            "distance_m": distancia_m,
            "distance_km": round(distancia_m / 1000, 2),
            "duration_s": round(duracion_s),
            "duration_min": round(duracion_s / 60),
            "toll_cost": toll_cost,
            "toll_currency": "MXN",
            "has_tolls": has_tolls,
            "toll_price_available": False,
            "vehicle_type": tipo_solicitado,
            "emission_type": "GASOLINE" if tipo_solicitado == "GASOLINE" else "DIESEL",
            "toll_warnings": ["Costo de peaje estimado (Directions API)"] if has_tolls else [],
            "source": "Directions API (fallback)",
        })
    
    if not rutas:
        raise ErrorGoogleMaps("Directions API no devolvió rutas disponibles.")
    
    logger.info(f"✅ Directions API devolvió {len(rutas)} rutas (fallback)")
    return rutas


def calcular_viaje(
    origen,
    destino,
    tipo_vehiculo,
    rendimiento_km_l,
    precio_gasolina_mxn,
    clave_api,
    tiempo_espera,
    zonas,
    usar_optimizacion=True,
):
    lugar_origen = geocodificar(origen, clave_api, tiempo_espera)
    lugar_destino = geocodificar(destino, clave_api, tiempo_espera)
    punto_origen = (lugar_origen["lat"], lugar_origen["lng"])
    punto_destino = (lugar_destino["lat"], lugar_destino["lng"])

    logger.info(f"🔄 Calculando ruta de {origen} a {destino}")
    rutas = calcular_rutas_google(
        punto_origen,
        punto_destino,
        tipo_vehiculo,
        clave_api,
        tiempo_espera,
    )
    
    # Optimización con Hill Climbing (solo si está activada y hay múltiples rutas)
    if usar_optimizacion and len(rutas) > 1:
        try:
            logger.info("🔄 Aplicando optimización Hill Climbing...")
            optimizador = OptimizadorRutas({
                "max_iteraciones": 20,  # Reducido para velocidad
                "penalizacion_zona_roja": 100.0,
                "peso_distancia": 1.0,
                "peso_peaje": 0.5,
                "peso_tiempo": 0.1,
            })
            
            rutas_para_optimizar = []
            for ruta in rutas:
                puntos_ruta = decodificar_polilinea(ruta.get("polyline", ""))
                if len(puntos_ruta) > 1:
                    coordenadas = [{"lat": p[0], "lng": p[1]} for p in puntos_ruta]
                    rutas_para_optimizar.append({
                        "coordinates": coordenadas,
                        "distance_km": ruta.get("distance_km", 0),
                        "duration_min": ruta.get("duration_min", 0),
                        "toll_cost": ruta.get("toll_cost", 0),
                        "polyline": ruta.get("polyline", ""),
                    })
            
            if rutas_para_optimizar:
                mejor_ruta, mejor_costo = optimizador.hill_climbing_multi_inicio(
                    rutas_para_optimizar,
                    zonas_rojas=zonas,
                    iteraciones_por_ruta=15  # Reducido para velocidad
                )
                
                if mejor_ruta and "coordinates" in mejor_ruta:
                    logger.info("✅ Optimización Hill Climbing completada")
        except Exception as e:
            logger.warning(f"⚠️ Hill Climbing falló: {e}. Usando método tradicional.")
    
    # Seleccionar mejor ruta
    analisis_ruta = seleccionar_mejor_ruta(rutas)
    seleccionada = rutas[analisis_ruta["route_index"]]
    puntos_ruta = [
        (punto["lat"], punto["lng"])
        for punto in analisis_ruta["coordinates"]
    ]

    # Encontrar peajes
    peajes, fuente_peajes = encontrar_peajes(seleccionada, clave_api, tiempo_espera)
    zonas_intersectadas = zonas_intersectan_ruta(puntos_ruta, zonas)

    # Cálculos finales
    distancia_km = float(seleccionada.get("distance_km") or analisis_ruta["distance_km"])
    litros = distancia_km / rendimiento_km_l
    costo_combustible = litros * precio_gasolina_mxn
    costo_peajes = float(seleccionada.get("toll_cost", 0) or 0)

    return {
        "origin": {
            "query": origen,
            "address": lugar_origen["address"],
            "city": lugar_origen["city"],
            "state": lugar_origen["state"],
            "lat": lugar_origen["lat"],
            "lng": lugar_origen["lng"],
        },
        "destination": {
            "query": destino,
            "address": lugar_destino["address"],
            "city": lugar_destino["city"],
            "state": lugar_destino["state"],
            "lat": lugar_destino["lat"],
            "lng": lugar_destino["lng"],
        },
        "polyline": seleccionada["polyline"],
        "coordinates": analisis_ruta["coordinates"],
        "distance_km": round(distancia_km, 2),
        "google_distance_km": seleccionada["distance_km"],
        "manhattan_distance_km": analisis_ruta["distance_km"],
        "duration_min": seleccionada["duration_min"],
        "algorithm": analisis_ruta["algorithm"],
        "route_nodes": analisis_ruta["node_count"],
        "selected_google_route": analisis_ruta["route_index"],
        "alternatives_count": len(rutas),
        "vehicle_type": seleccionada["vehicle_type"],
        "emission_type": seleccionada["emission_type"],
        "efficiency_km_l": round(rendimiento_km_l, 2),
        "gas_price_mxn": round(precio_gasolina_mxn, 2),
        "estimated_liters": round(litros, 2),
        "fuel_cost_mxn": round(costo_combustible, 2),
        "has_tolls": seleccionada["has_tolls"],
        "toll_price_available": seleccionada["toll_price_available"],
        "toll_cost": round(costo_peajes, 2),
        "toll_currency": seleccionada["toll_currency"],
        "tolls": peajes,
        "toll_count": len(peajes) if seleccionada["has_tolls"] else 0,
        "toll_source": fuente_peajes,
        "toll_warnings": seleccionada["toll_warnings"],
        "total_cost_mxn": round(costo_combustible + costo_peajes, 2),
        "has_red_zones": bool(zonas_intersectadas),
        "red_zones": zonas_intersectadas,
        "optimized": usar_optimizacion,
        "api_source": seleccionada.get("source", "Routes API"),
    }