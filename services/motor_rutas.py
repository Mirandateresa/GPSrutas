import heapq
import math
import polyline


RADIO_TIERRA_KM = 6371.0088


def decodificar_polilinea(codificada):
    """
    Decodifica una polyline en pares (latitud, longitud).
    """
    if not codificada:
        return []

    try:
        puntos = polyline.decode(codificada)
        return [(float(lat), float(lng)) for lat, lng in puntos]
    except Exception:
        return _decodificar_polilinea_manual(codificada)


def decodificar_polilinea_osrm(codificada):
    """Decodifica una polyline de OSRM."""
    return decodificar_polilinea(codificada)


def _decodificar_polilinea_manual(codificada):
    """Decodificación manual de polilínea."""
    if not codificada:
        return []

    coordenadas = []
    indice = latitud = longitud = 0
    longitud_codificada = len(codificada)

    while indice < longitud_codificada:
        for eje in ("lat", "lng"):
            desplazamiento = resultado = 0
            while True:
                if indice >= longitud_codificada:
                    return coordenadas
                valor = ord(codificada[indice]) - 63
                indice += 1
                resultado |= (valor & 0x1F) << desplazamiento
                desplazamiento += 5
                if valor < 0x20:
                    break
            diferencia = ~(resultado >> 1) if resultado & 1 else resultado >> 1
            if eje == "lat":
                latitud += diferencia
            else:
                longitud += diferencia
        coordenadas.append((latitud / 1e5, longitud / 1e5))

    return coordenadas


def distancia_manhattan_km(punto_a, punto_b):
    """Distancia Manhattan aproximada."""
    latitud1, longitud1 = punto_a
    latitud2, longitud2 = punto_b
    latitud_media = math.radians((latitud1 + latitud2) / 2)
    latitud_km = abs(latitud2 - latitud1) * 111.32
    longitud_km = abs(longitud2 - longitud1) * 111.32 * math.cos(latitud_media)
    return latitud_km + longitud_km


def _nodo(punto):
    return round(float(punto[0]), 6), round(float(punto[1]), 6)


def construir_grafo_cadena(puntos):
    grafo = {}
    normalizados = [_nodo(punto) for punto in puntos]
    for inicio, fin in zip(normalizados, normalizados[1:]):
        peso = distancia_manhattan_km(inicio, fin)
        grafo.setdefault(inicio, []).append((fin, peso))
        grafo.setdefault(fin, []).append((inicio, peso))
    if normalizados:
        grafo.setdefault(normalizados[0], [])
    return grafo, normalizados


def aplicar_dijkstra(grafo, origen, destino):
    distancias = {origen: 0.0}
    anteriores = {}
    cola = [(0.0, origen)]

    while cola:
        distancia_actual, actual = heapq.heappop(cola)
        if actual == destino:
            break
        if distancia_actual > distancias.get(actual, float("inf")):
            continue

        for vecino, peso in grafo.get(actual, []):
            candidato = distancia_actual + peso
            if candidato < distancias.get(vecino, float("inf")):
                distancias[vecino] = candidato
                anteriores[vecino] = actual
                heapq.heappush(cola, (candidato, vecino))

    if destino not in distancias:
        return [], float("inf")

    camino = [destino]
    while camino[-1] != origen:
        camino.append(anteriores[camino[-1]])
    camino.reverse()
    return camino, distancias[destino]


def analizar_ruta_osm(ruta):
    """Analiza una ruta de OSRM."""
    puntos = ruta.get("coordinates", [])
    
    if not puntos:
        polilinea = ruta.get("polyline", "")
        if polilinea:
            puntos_decodificados = decodificar_polilinea(polilinea)
            puntos = [{"lat": lat, "lng": lng} for lat, lng in puntos_decodificados]
    
    if not puntos and "distance_km" in ruta:
        return {
            "points": [],
            "manhattan_distance_km": ruta.get("distance_km", 0),
            "node_count": 0,
            "coordinates": [],
        }
    
    if len(puntos) < 2:
        return None

    puntos_tupla = [(p["lat"], p["lng"]) for p in puntos if isinstance(p, dict)]
    if len(puntos_tupla) < 2:
        return None
        
    grafo, nodos = construir_grafo_cadena(puntos_tupla)
    camino, distancia = aplicar_dijkstra(grafo, nodos[0], nodos[-1])
    
    return {
        "points": camino,
        "manhattan_distance_km": distancia,
        "node_count": len(camino),
        "coordinates": [{"lat": p[0], "lng": p[1]} for p in camino],
    }


def seleccionar_mejor_ruta_osm(rutas):
    """Evalúa rutas de OSRM y elige la de menor peso Manhattan."""
    candidatos = []
    for indice, ruta in enumerate(rutas):
        analisis = analizar_ruta_osm(ruta)
        if analisis and analisis["manhattan_distance_km"] > 0:
            candidatos.append((analisis["manhattan_distance_km"], indice, analisis))
        elif ruta.get("distance_km", 0) > 0:
            candidatos.append((ruta.get("distance_km", 999999), indice, {
                "coordinates": ruta.get("coordinates", []),
                "distance_km": ruta.get("distance_km", 0),
                "node_count": len(ruta.get("coordinates", [])),
                "manhattan_distance_km": ruta.get("distance_km", 0),
            }))

    if not candidatos:
        if rutas:
            return {
                "route_index": 0,
                "coordinates": rutas[0].get("coordinates", []),
                "distance_km": rutas[0].get("distance_km", 0),
                "distance_m": rutas[0].get("distance_m", 0),
                "node_count": len(rutas[0].get("coordinates", [])),
                "algorithm": "OSRM (fallback)",
            }
        raise ValueError("Ninguna ruta contiene coordenadas válidas.")

    _, indice, analisis = min(candidatos, key=lambda elemento: elemento[0])
    return {
        "route_index": indice,
        "coordinates": analisis.get("coordinates", []),
        "distance_km": round(analisis.get("manhattan_distance_km", 0), 2),
        "distance_m": round(analisis.get("manhattan_distance_km", 0) * 1000, 2),
        "node_count": analisis.get("node_count", 0),
        "algorithm": "OSRM + distancia Manhattan + Dijkstra",
    }


# Mantener compatibilidad
seleccionar_mejor_ruta = seleccionar_mejor_ruta_osm


def generar_polilinea_desde_coordenadas(coordenadas):
    """Genera una polilínea codificada."""
    if not coordenadas:
        return ""
    
    try:
        puntos = [(p["lat"], p["lng"]) for p in coordenadas if isinstance(p, dict)]
        return polyline.encode(puntos)
    except Exception:
        return ""


def calcular_distancia_aproximada(coordenadas):
    """Calcula la distancia aproximada de una ruta."""
    if len(coordenadas) < 2:
        return 0
    
    distancia_total = 0
    for i in range(len(coordenadas) - 1):
        p1 = coordenadas[i]
        p2 = coordenadas[i + 1]
        if not isinstance(p1, dict) or not isinstance(p2, dict):
            continue
        lat_media = math.radians((p1["lat"] + p2["lat"]) / 2)
        lat_km = abs(p2["lat"] - p1["lat"]) * 111.32
        lng_km = abs(p2["lng"] - p1["lng"]) * 111.32 * math.cos(lat_media)
        distancia_total += lat_km + lng_km
    
    return distancia_total


def crear_ruta_desde_coordenadas(coordenadas, ruta_original=None):
    """Crea una ruta desde coordenadas."""
    if ruta_original is None:
        ruta_original = {}
    
    distancia_km = calcular_distancia_aproximada(coordenadas)
    
    ruta = {
        "coordinates": coordenadas,
        "distance_km": round(distancia_km, 2),
        "distance_m": round(distancia_km * 1000, 2),
        "polyline": generar_polilinea_desde_coordenadas(coordenadas),
        "node_count": len(coordenadas),
        "algorithm": "Optimizado con Hill Climbing",
    }
    
    for key in ["duration_min", "toll_cost", "toll_currency", "has_tolls"]:
        if key in ruta_original:
            ruta[key] = ruta_original[key]
    
    return ruta