import requests
import logging
import math

from services.motor_rutas import seleccionar_mejor_ruta_osm, decodificar_polilinea
from services.zonas import zonas_intersectan_ruta

logger = logging.getLogger(__name__)

# URLs
URL_NOMINATIM_SEARCH = "https://nominatim.openstreetmap.org/search"
URL_NOMINATIM_REVERSE = "https://nominatim.openstreetmap.org/reverse"
URL_OSRM_ROUTE = "https://router.project-osrm.org/route/v1/driving"


class ErrorGeocodificacion(RuntimeError):
    pass


class ErrorRuta(RuntimeError):
    pass


def _obtener_headers():
    """Headers para Nominatim"""
    return {
        "User-Agent": "GPS-RutasSeguras/1.0",
        "Accept": "application/json",
    }


def geocodificar(direccion, tiempo_espera=20):
    """Geocodifica una dirección usando Nominatim."""
    if not direccion or not direccion.strip():
        raise ErrorGeocodificacion("La dirección está vacía.")

    try:
        respuesta = requests.get(
            URL_NOMINATIM_SEARCH,
            params={
                "q": direccion,
                "format": "json",
                "limit": 1,
                "addressdetails": 1,
                "countrycodes": "mx",
                "accept-language": "es",
            },
            headers=_obtener_headers(),
            timeout=tiempo_espera,
        )
        respuesta.raise_for_status()
        datos = respuesta.json()

        if not datos:
            raise ErrorGeocodificacion(f"No se encontró la dirección: {direccion}")

        resultado = datos[0]
        lat = float(resultado["lat"])
        lng = float(resultado["lon"])
        direccion_formateada = resultado.get("display_name", direccion)

        direccion_detalles = resultado.get("address", {})
        ciudad = (
            direccion_detalles.get("city") or
            direccion_detalles.get("town") or
            direccion_detalles.get("village") or
            direccion_detalles.get("municipality") or
            ""
        )
        estado = (
            direccion_detalles.get("state") or
            direccion_detalles.get("region") or
            ""
        )
        pais = direccion_detalles.get("country", "México")

        return {
            "lat": lat,
            "lng": lng,
            "address": direccion_formateada,
            "city": ciudad,
            "state": estado,
            "country": pais,
            "place_id": str(resultado.get("place_id", "")),
        }

    except requests.RequestException as e:
        raise ErrorGeocodificacion(f"Error de conexión: {str(e)}")
    except (KeyError, ValueError, IndexError) as e:
        raise ErrorGeocodificacion(f"Error al procesar la respuesta: {str(e)}")


def geocodificar_reversa(lat, lng, tiempo_espera=20):
    """Geocodificación inversa usando Nominatim."""
    try:
        respuesta = requests.get(
            URL_NOMINATIM_REVERSE,
            params={
                "lat": lat,
                "lon": lng,
                "format": "json",
                "addressdetails": 1,
                "accept-language": "es",
            },
            headers=_obtener_headers(),
            timeout=tiempo_espera,
        )
        respuesta.raise_for_status()
        datos = respuesta.json()

        if not datos:
            return f"{lat:.6f}, {lng:.6f}"

        return datos.get("display_name", f"{lat:.6f}, {lng:.6f}")

    except (requests.RequestException, ValueError):
        return f"{lat:.6f}, {lng:.6f}"


# ============================================================
# 1. DETECCIÓN MEJORADA DE PEAJES EN OSRM
# ============================================================

def _detectar_peajes_osrm_mejorado(ruta):
    """
    Detecta peajes con más detalle examinando las instrucciones paso a paso.
    """
    peajes = []
    has_tolls = False
    visto = set()
    
    if not isinstance(ruta, dict):
        return has_tolls, peajes
    
    legs = ruta.get("legs", [])
    if not legs or not isinstance(legs, list):
        return has_tolls, peajes
    
    for leg in legs:
        if not isinstance(leg, dict):
            continue
            
        steps = leg.get("steps", [])
        if not steps or not isinstance(steps, list):
            continue
            
        for step in steps:
            if not isinstance(step, dict):
                continue
                
            # Verificar el modo (toll = peaje)
            if step.get("mode") == "toll":
                has_tolls = True
                maniobra = step.get("maneuver", {})
                if isinstance(maniobra, dict):
                    location = maniobra.get("location", {})
                else:
                    location = {}
                
                nombre = step.get("name", "Peaje")
                if not nombre:
                    nombre = "Peaje"
                
                lat = location.get("lat", 0) if isinstance(location, dict) else 0
                lng = location.get("lon", 0) if isinstance(location, dict) else 0
                
                clave = f"{nombre}_{lat}_{lng}"
                if clave not in visto:
                    visto.add(clave)
                    peajes.append({
                        "name": nombre,
                        "address": step.get("name", "Autopista de cuota"),
                        "instruction": maniobra.get("instruction", "Tramo de peaje") if isinstance(maniobra, dict) else "Tramo de peaje",
                        "lat": lat,
                        "lng": lng,
                        "source": "OSRM",
                        "price": None,
                        "estimated_location": True if lat == 0 else False,
                    })
                continue
            
            # Verificar la instrucción del paso
            maniobra = step.get("maneuver", {})
            if isinstance(maniobra, dict):
                instruccion = maniobra.get("instruction", "")
            else:
                instruccion = ""
                
            if "toll" in instruccion.lower() or "peaje" in instruccion.lower() or "cuota" in instruccion.lower():
                has_tolls = True
                if isinstance(maniobra, dict):
                    location = maniobra.get("location", {})
                else:
                    location = {}
                
                nombre = step.get("name", "Peaje")
                if not nombre:
                    nombre = "Peaje"
                
                lat = location.get("lat", 0) if isinstance(location, dict) else 0
                lng = location.get("lon", 0) if isinstance(location, dict) else 0
                
                clave = f"{nombre}_{lat}_{lng}"
                if clave not in visto:
                    visto.add(clave)
                    peajes.append({
                        "name": nombre,
                        "address": step.get("name", "Autopista de cuota"),
                        "instruction": instruccion,
                        "lat": lat,
                        "lng": lng,
                        "source": "OSRM",
                        "price": None,
                        "estimated_location": True if lat == 0 else False,
                    })
            
            # Verificar el nombre de la vía
            nombre_via = step.get("name", "")
            if nombre_via and ("toll" in nombre_via.lower() or "cuota" in nombre_via.lower() or "peaje" in nombre_via.lower()):
                has_tolls = True
                if isinstance(maniobra, dict):
                    location = maniobra.get("location", {})
                else:
                    location = {}
                
                lat = location.get("lat", 0) if isinstance(location, dict) else 0
                lng = location.get("lon", 0) if isinstance(location, dict) else 0
                
                clave = f"{nombre_via}_{lat}_{lng}"
                if clave not in visto:
                    visto.add(clave)
                    peajes.append({
                        "name": nombre_via,
                        "address": nombre_via,
                        "instruction": "Vía de cuota",
                        "lat": lat,
                        "lng": lng,
                        "source": "OSRM",
                        "price": None,
                        "estimated_location": True if lat == 0 else False,
                    })
    
    return has_tolls, peajes


def _estimar_coordenadas_peajes(peajes, coordenadas_ruta):
    """
    Estima coordenadas para peajes que no tienen ubicación.
    """
    if not peajes or not coordenadas_ruta or len(coordenadas_ruta) < 2:
        return peajes
    
    # Contar cuántos peajes tienen coordenadas válidas
    peajes_con_coords = [p for p in peajes if p.get("lat", 0) != 0 and p.get("lng", 0) != 0]
    peajes_sin_coords = [p for p in peajes if p.get("lat", 0) == 0 and p.get("lng", 0) == 0]
    
    if not peajes_sin_coords:
        return peajes
    
    logger.info(f"Estimando coordenadas para {len(peajes_sin_coords)} peajes")
    
    # Si hay algunos peajes con coordenadas, usarlos como referencia
    if peajes_con_coords:
        # Ordenar peajes por su posición estimada en la ruta
        for peaje in peajes_sin_coords:
            # Buscar el peaje más cercano con coordenadas
            mejor_dist = float('inf')
            mejor_coord = None
            for p in peajes_con_coords:
                for coord in coordenadas_ruta:
                    if isinstance(coord, dict) and "lat" in coord and "lng" in coord:
                        dist = math.sqrt(
                            (p["lat"] - coord["lat"])**2 + 
                            (p["lng"] - coord["lng"])**2
                        )
                        if dist < mejor_dist:
                            mejor_dist = dist
                            mejor_coord = coord
            
            if mejor_coord:
                peaje["lat"] = mejor_coord["lat"]
                peaje["lng"] = mejor_coord["lng"]
                peaje["estimated_location"] = True
    
    # Si ningún peaje tiene coordenadas, distribuirlos a lo largo de la ruta
    if not peajes_con_coords:
        step = len(coordenadas_ruta) // (len(peajes) + 1)
        for i, peaje in enumerate(peajes):
            idx = min((i + 1) * step, len(coordenadas_ruta) - 1)
            if idx < len(coordenadas_ruta):
                coord = coordenadas_ruta[idx]
                if isinstance(coord, dict) and "lat" in coord and "lng" in coord:
                    peaje["lat"] = coord["lat"]
                    peaje["lng"] = coord["lng"]
                    peaje["estimated_location"] = True
    
    return peajes


def _estimar_costo_peaje(distancia_m, has_tolls):
    """
    Estima el costo de peaje basado en distancia.
    """
    if not has_tolls:
        return 0.0
    
    distancia_km = distancia_m / 1000
    costo_base = distancia_km * 1.5
    
    return max(20.0, round(costo_base, 2))


# ============================================================
# 2. CALCULAR RUTA CON OSRM
# ============================================================

def calcular_ruta_osrm(origen, destino, tipo_vehiculo="GASOLINE", tiempo_espera=20):
    """
    Calcula una ruta usando OSRM con detección mejorada de peajes.
    """
    coords = f"{origen[1]},{origen[0]};{destino[1]},{destino[0]}"
    url = f"{URL_OSRM_ROUTE}/{coords}"

    params = {
        "overview": "full",
        "geometries": "polyline",
        "steps": "true",
        "annotations": "true",
        "alternatives": "true",
    }

    try:
        logger.info("🔄 Solicitando ruta a OSRM...")
        respuesta = requests.get(
            url,
            params=params,
            headers={"User-Agent": "GPS-RutasSeguras/1.0"},
            timeout=tiempo_espera,
        )
        respuesta.raise_for_status()
        datos = respuesta.json()

        if datos.get("code") != "Ok":
            raise ErrorRuta(f"OSRM error: {datos.get('code', 'Unknown error')}")

        rutas = []
        routes = datos.get("routes", [])
        
        if not routes or not isinstance(routes, list):
            raise ErrorRuta("No se encontraron rutas disponibles.")
        
        for idx, ruta in enumerate(routes):
            if not isinstance(ruta, dict):
                continue
                
            geometria = ruta.get("geometry", "")
            distancia_m = ruta.get("distance", 0)
            duracion_s = ruta.get("duration", 0)
            
            # Decodificar geometría primero para tener coordenadas de referencia
            puntos = decodificar_polilinea(geometria)
            coordenadas = []
            for p in puntos:
                if isinstance(p, tuple) and len(p) == 2:
                    coordenadas.append({"lat": p[0], "lng": p[1]})
            
            if not coordenadas:
                coordenadas = [
                    {"lat": origen[0], "lng": origen[1]},
                    {"lat": destino[0], "lng": destino[1]}
                ]
            
            # 🔍 DETECTAR PEAJES
            has_tolls, peajes = _detectar_peajes_osrm_mejorado(ruta)
            
            # 🔑 ESTIMAR COORDENADAS PARA PEAJES SIN UBICACIÓN
            if peajes:
                peajes = _estimar_coordenadas_peajes(peajes, coordenadas)
                logger.info(f"   Peajes detectados: {len(peajes)}")
                for p in peajes:
                    logger.info(f"      - {p['name']} ({p['lat']}, {p['lng']})")
            
            toll_cost = _estimar_costo_peaje(distancia_m, has_tolls)

            rutas.append({
                "index": idx,
                "polyline": geometria,
                "legs": ruta.get("legs", []),
                "distance_m": distancia_m,
                "distance_km": round(distancia_m / 1000, 2) if distancia_m > 0 else 0,
                "duration_s": round(duracion_s) if duracion_s > 0 else 0,
                "duration_min": round(duracion_s / 60) if duracion_s > 0 else 0,
                "toll_cost": toll_cost,
                "toll_currency": "MXN",
                "has_tolls": has_tolls,
                "toll_price_available": has_tolls,
                "vehicle_type": tipo_vehiculo,
                "emission_type": "GASOLINE" if tipo_vehiculo == "GASOLINE" else "DIESEL",
                "toll_warnings": ["Costo de peaje estimado (OSRM)"] if has_tolls else [],
                "source": "OSRM",
                "coordinates": coordenadas,
                "tolls": peajes,
            })

        if not rutas:
            raise ErrorRuta("No se encontraron rutas disponibles.")

        logger.info(f"✅ OSRM: {len(rutas)} rutas encontradas")
        return rutas

    except requests.RequestException as e:
        raise ErrorRuta(f"Error de conexión con OSRM: {str(e)}")
    except (KeyError, ValueError, IndexError) as e:
        raise ErrorRuta(f"Error al procesar la ruta: {str(e)}")


# ============================================================
# 3. CALCULAR VIAJE - PRINCIPAL
# ============================================================

def calcular_viaje(
    origen,
    destino,
    tipo_vehiculo,
    rendimiento_km_l,
    precio_gasolina_mxn,
    tiempo_espera,
    zonas,
    usar_optimizacion=False,
):
    """
    Calcula un viaje completo usando OSRM con detección mejorada de peajes.
    """
    logger.info(f"🔄 Geocodificando origen: {origen}")
    lugar_origen = geocodificar(origen, tiempo_espera)
    logger.info(f"✅ Origen: {lugar_origen['address']}")
    
    logger.info(f"🔄 Geocodificando destino: {destino}")
    lugar_destino = geocodificar(destino, tiempo_espera)
    logger.info(f"✅ Destino: {lugar_destino['address']}")

    punto_origen = (lugar_origen["lat"], lugar_origen["lng"])
    punto_destino = (lugar_destino["lat"], lugar_destino["lng"])

    # ====== CALCULAR RUTA CON OSRM ======
    try:
        rutas = calcular_ruta_osrm(
            punto_origen,
            punto_destino,
            tipo_vehiculo,
            tiempo_espera,
        )
    except ErrorRuta as e:
        raise ErrorRuta(f"No se pudo calcular la ruta: {str(e)}")

    # ====== SELECCIONAR MEJOR RUTA ======
    try:
        analisis_ruta = seleccionar_mejor_ruta_osm(rutas)
    except ValueError as e:
        raise ErrorRuta(f"Error al seleccionar la mejor ruta: {str(e)}")

    seleccionada = rutas[analisis_ruta["route_index"]]

    # Obtener puntos de la ruta
    puntos_ruta = []
    for coord in analisis_ruta.get("coordinates", []):
        if isinstance(coord, dict) and "lat" in coord and "lng" in coord:
            puntos_ruta.append((coord["lat"], coord["lng"]))

    if not puntos_ruta:
        for coord in seleccionada.get("coordinates", []):
            if isinstance(coord, dict) and "lat" in coord and "lng" in coord:
                puntos_ruta.append((coord["lat"], coord["lng"]))

    if not puntos_ruta:
        puntos_ruta = [punto_origen, punto_destino]

    # Obtener peajes de la ruta
    peajes = seleccionada.get("tolls", [])
    if not isinstance(peajes, list):
        peajes = []

    # Detectar zonas rojas
    zonas_intersectadas = zonas_intersectan_ruta(puntos_ruta, zonas)

    # Calcular costos
    distancia_km = float(analisis_ruta.get("distance_km", 0))
    if distancia_km == 0:
        distancia_km = float(seleccionada.get("distance_km", 0))
    
    litros = distancia_km / rendimiento_km_l if rendimiento_km_l > 0 else 0
    costo_combustible = litros * precio_gasolina_mxn
    costo_peajes = float(seleccionada.get("toll_cost", 0) or 0)

    resultado = {
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
        "polyline": seleccionada.get("polyline", ""),
        "coordinates": analisis_ruta.get("coordinates", []),
        "distance_km": round(distancia_km, 2),
        "google_distance_km": seleccionada.get("distance_km", 0),
        "manhattan_distance_km": analisis_ruta.get("distance_km", 0),
        "duration_min": seleccionada.get("duration_min", 0),
        "algorithm": analisis_ruta.get("algorithm", "OSRM"),
        "route_nodes": analisis_ruta.get("node_count", 0),
        "selected_google_route": analisis_ruta.get("route_index", 0),
        "alternatives_count": len(rutas),
        "vehicle_type": seleccionada.get("vehicle_type", tipo_vehiculo),
        "emission_type": seleccionada.get("emission_type", "GASOLINE"),
        "efficiency_km_l": round(rendimiento_km_l, 2),
        "gas_price_mxn": round(precio_gasolina_mxn, 2),
        "estimated_liters": round(litros, 2),
        "fuel_cost_mxn": round(costo_combustible, 2),
        "has_tolls": seleccionada.get("has_tolls", False),
        "toll_price_available": seleccionada.get("toll_price_available", False),
        "toll_cost": round(costo_peajes, 2),
        "toll_currency": seleccionada.get("toll_currency", "MXN"),
        "tolls": peajes,
        "toll_count": len(peajes) if seleccionada.get("has_tolls") else 0,
        "toll_source": "OSRM (mejorado)",
        "toll_warnings": seleccionada.get("toll_warnings", []),
        "total_cost_mxn": round(costo_combustible + costo_peajes, 2),
        "has_red_zones": bool(zonas_intersectadas),
        "red_zones": zonas_intersectadas,
        "optimized": usar_optimizacion,
        "api_source": "OSRM",
    }

    logger.info(f"✅ Ruta calculada: {distancia_km}km, {len(peajes)} peajes")
    return resultado