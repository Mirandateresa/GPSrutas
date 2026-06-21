from services.motor_rutas import (
    construir_grafo_cadena,
    decodificar_polilinea,
    aplicar_dijkstra,
    seleccionar_mejor_ruta,
)
from services.zonas import distancia_a_ruta_m, zonas_intersectan_ruta


def prueba_decodificacion_polilinea_google():
    puntos = decodificar_polilinea("_p~iF~ps|U_ulLnnqC_mqNvxq`@")
    assert puntos == [(38.5, -120.2), (40.7, -120.95), (43.252, -126.453)]


def prueba_dijkstra_en_cadena():
    grafo, nodos = construir_grafo_cadena([(19.0, -99.0), (19.1, -99.1), (19.2, -99.2)])
    camino, distancia = aplicar_dijkstra(grafo, nodos[0], nodos[-1])
    assert camino == nodos
    assert distancia > 0


def prueba_seleccion_mejor_ruta():
    corta = "_p~iF~ps|U_ulLnnqC"
    larga = "_p~iF~ps|U_ulLnnqC_mqNvxq`@"
    resultado = seleccionar_mejor_ruta([
        {"polyline": larga},
        {"polyline": corta},
    ])
    assert resultado["route_index"] == 1
    assert resultado["node_count"] == 2


def prueba_interseccion_zona():
    ruta = [(19.0, -99.0), (19.1, -99.1)]
    zonas = [{
        "id": "1",
        "name": "Cercana",
        "lat": 19.05,
        "lng": -99.05,
        "radius_m": 1000,
    }]
    coincidencias = zonas_intersectan_ruta(ruta, zonas)
    assert len(coincidencias) == 1
    assert coincidencias[0]["distance_to_route_m"] < 1000


def prueba_distancia_punto_lejano_ruta():
    distancia = distancia_a_ruta_m((20.0, -100.0), [(19.0, -99.0), (19.1, -99.1)])
    assert distancia > 100_000


class _RespuestaSimulada:
    def __init__(self, contenido, estado=200):
        self._contenido = contenido
        self.status_code = estado
        self.ok = 200 <= estado < 300
        self.text = ""

    def json(self):
        return self._contenido


def prueba_casetas_descarta_lugares_cercanos_y_vias_paralelas(parche_mono):
    from services import casetas as modulo_casetas

    puntos_ruta = [(19.0, -99.0), (19.1, -99.0)]
    respuestas = iter([
        _RespuestaSimulada({
            "places": [
                {
                    "id": "sobre-ruta",
                    "displayName": {"text": "Caseta sobre la ruta"},
                    "formattedAddress": "Autopista principal",
                    "location": {"latitude": 19.05, "longitude": -99.0},
                    "primaryType": "toll_station",
                    "types": ["toll_station"],
                },
                {
                    "id": "cercana",
                    "displayName": {"text": "Caseta cercana"},
                    "formattedAddress": "Otra carretera",
                    "location": {"latitude": 19.05, "longitude": -99.005},
                    "primaryType": "toll_station",
                    "types": ["toll_station"],
                },
                {
                    "id": "paralela",
                    "displayName": {"text": "Caseta de vía paralela"},
                    "formattedAddress": "Carretera paralela",
                    "location": {"latitude": 19.06, "longitude": -98.99962},
                    "primaryType": "toll_station",
                    "types": ["toll_station"],
                },
            ]
        }),
        _RespuestaSimulada({
            "routes": [{"travelAdvisory": {"tollInfo": {}}}]
        }),
        _RespuestaSimulada({"routes": [{}]}),
    ])
    cuerpos = []

    def publicar_simulado(*argumentos, **opciones):
        cuerpos.append(opciones.get("json", {}))
        return next(respuestas)

    parche_mono.setattr(modulo_casetas.requests, "post", publicar_simulado)
    lugares = modulo_casetas._buscar_lugares_peaje(
        puntos_ruta,
        "polilinea-codificada",
        "clave-prueba",
    )

    assert [lugar["id"] for lugar in lugares] == ["sobre-ruta"]
    assert lugares[0]["distance_to_route_m"] < 1
    assert cuerpos[0]["searchAlongRouteParameters"]["polyline"]["encodedPolyline"] == "polilinea-codificada"
    assert "intermediates" in cuerpos[1]


def prueba_caseta_sin_segunda_validacion_exige_maximo_25_metros(parche_mono):
    import requests
    from services import casetas as modulo_casetas

    puntos_ruta = [(19.0, -99.0), (19.1, -99.0)]
    respuesta_lugares = _RespuestaSimulada({
        "places": [
            {
                "id": "muy-cercana",
                "displayName": {"text": "Caseta muy cercana"},
                "formattedAddress": "Sobre el recorrido",
                "location": {"latitude": 19.04, "longitude": -98.99991},
                "primaryType": "toll_station",
                "types": ["toll_station"],
            },
            {
                "id": "a-cuarenta-metros",
                "displayName": {"text": "Caseta a cuarenta metros"},
                "formattedAddress": "Vía lateral",
                "location": {"latitude": 19.06, "longitude": -98.99962},
                "primaryType": "toll_station",
                "types": ["toll_station"],
            },
        ]
    })
    llamadas = 0

    def publicar_simulado(*argumentos, **opciones):
        nonlocal llamadas
        llamadas += 1
        if llamadas == 1:
            return respuesta_lugares
        raise requests.RequestException("validación no disponible")

    parche_mono.setattr(modulo_casetas.requests, "post", publicar_simulado)
    lugares = modulo_casetas._buscar_lugares_peaje(
        puntos_ruta,
        "polilinea-codificada",
        "clave-prueba",
    )

    assert [lugar["id"] for lugar in lugares] == ["muy-cercana"]
    assert lugares[0]["distance_to_route_m"] < 25
