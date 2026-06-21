from routes import api as modulo_api


def prueba_carga_inicio(cliente):
    respuesta = cliente.get("/")
    assert respuesta.status_code == 200
    assert b"Rutas seguras" in respuesta.data
    assert b"test-key" in respuesta.data
    assert b"CONFIGURACION_APLICACION" not in respuesta.data
    assert b"{{" not in respuesta.data


def prueba_estado_servidor(cliente):
    respuesta = cliente.get("/api/health")
    assert respuesta.status_code == 200
    assert respuesta.get_json() == {"ok": True, "service": "gps"}


def prueba_listado_zonas(cliente):
    respuesta = cliente.get("/api/zones")
    contenido = respuesta.get_json()
    assert respuesta.status_code == 200
    assert contenido["ok"] is True
    assert contenido["data"][0]["name"] == "Zona de prueba"


def prueba_crud_zonas(cliente):
    zona_nueva = {
        "name": "Centro",
        "municipality": "Tula",
        "state": "Hidalgo",
        "risks": ["Asalto"],
        "description": "Zona creada desde la prueba.",
        "lat": 20.05,
        "lng": -99.34,
        "radius_m": 800,
    }
    respuesta_creacion = cliente.post("/api/zones", json=zona_nueva)
    assert respuesta_creacion.status_code == 201
    id_zona = respuesta_creacion.get_json()["data"]["id"]

    respuesta_actualizacion = cliente.put(
        f"/api/zones/{id_zona}",
        json={"name": "Centro actualizado", "radius_m": 900},
    )
    assert respuesta_actualizacion.status_code == 200
    assert respuesta_actualizacion.get_json()["data"]["name"] == "Centro actualizado"

    respuesta_eliminacion = cliente.delete(f"/api/zones/{id_zona}")
    assert respuesta_eliminacion.status_code == 200

    zonas_finales = cliente.get("/api/zones").get_json()["data"]
    assert all(zona["id"] != id_zona for zona in zonas_finales)


def prueba_validacion_zona(cliente):
    respuesta = cliente.post("/api/zones", json={"name": "Incompleta"})
    assert respuesta.status_code == 400
    assert respuesta.get_json()["ok"] is False


def prueba_validacion_ruta(cliente):
    respuesta = cliente.post("/api/route", json={"origin": "", "destination": "Toluca"})
    assert respuesta.status_code == 400


def prueba_endpoint_ruta_simulada(cliente, parche_mono):
    esperado = {
        "origin": {"address": "A", "lat": 19.9, "lng": -99.5},
        "destination": {"address": "B", "lat": 19.3, "lng": -99.1},
        "coordinates": [{"lat": 19.9, "lng": -99.5}, {"lat": 19.3, "lng": -99.1}],
        "distance_km": 100,
        "duration_min": 90,
        "estimated_liters": 7.14,
        "fuel_cost_mxn": 171.29,
        "toll_cost": 80,
        "toll_currency": "MXN",
        "total_cost_mxn": 251.29,
        "tolls": [],
        "red_zones": [],
    }

    parche_mono.setattr(modulo_api, "calcular_viaje", lambda **argumentos: esperado)
    respuesta = cliente.post("/api/route", json={
        "origin": "Jilotepec",
        "destination": "Toluca",
        "vehicle_type": "GASOLINE",
        "efficiency_km_l": 14,
    })
    assert respuesta.status_code == 200
    assert respuesta.get_json()["data"]["distance_km"] == 100


class _RespuestaExternaSimulada:
    def __init__(self, contenido, estado=200):
        self._contenido = contenido
        self.status_code = estado
        self.ok = 200 <= estado < 300
        self.text = ""

    def json(self):
        return self._contenido

    def raise_for_status(self):
        if not self.ok:
            raise RuntimeError(f"HTTP {self.status_code}")


def prueba_flujo_completo_filtra_caseta_fuera_de_ruta(cliente, parche_mono):
    from services import mapas as modulo_mapas

    geocodificaciones = iter([
        _RespuestaExternaSimulada({
            "status": "OK",
            "results": [{
                "formatted_address": "Origen de prueba",
                "place_id": "origen",
                "geometry": {"location": {"lat": 38.5, "lng": -120.2}},
                "address_components": [],
            }],
        }),
        _RespuestaExternaSimulada({
            "status": "OK",
            "results": [{
                "formatted_address": "Destino de prueba",
                "place_id": "destino",
                "geometry": {"location": {"lat": 43.252, "lng": -126.453}},
                "address_components": [],
            }],
        }),
    ])

    def obtener_simulado(*argumentos, **opciones):
        return next(geocodificaciones)

    def publicar_simulado(url, *argumentos, **opciones):
        cuerpo = opciones.get("json", {})
        if "places.googleapis.com" in url:
            return _RespuestaExternaSimulada({
                "places": [
                    {
                        "id": "caseta-ruta",
                        "displayName": {"text": "Caseta correcta"},
                        "formattedAddress": "Sobre la ruta",
                        "location": {"latitude": 38.5, "longitude": -120.2},
                        "primaryType": "toll_station",
                        "types": ["toll_station"],
                    },
                    {
                        "id": "caseta-lejana",
                        "displayName": {"text": "Caseta de otra carretera"},
                        "formattedAddress": "Fuera de la ruta",
                        "location": {"latitude": 38.5, "longitude": -120.25},
                        "primaryType": "toll_station",
                        "types": ["toll_station"],
                    },
                ]
            })
        if cuerpo.get("computeAlternativeRoutes") is True:
            return _RespuestaExternaSimulada({
                "routes": [{
                    "distanceMeters": 100000,
                    "duration": "5400s",
                    "polyline": {"encodedPolyline": "_p~iF~ps|U_ulLnnqC_mqNvxq`@"},
                    "travelAdvisory": {
                        "tollInfo": {
                            "estimatedPrice": [{
                                "currencyCode": "MXN",
                                "units": "80",
                                "nanos": 0,
                            }]
                        }
                    },
                    "legs": [{
                        "travelAdvisory": {"tollInfo": {}},
                        "steps": [{
                            "startLocation": {
                                "latLng": {"latitude": 38.5, "longitude": -120.2}
                            },
                            "navigationInstruction": {
                                "instructions": "Continúa por la carretera 57D"
                            },
                        }],
                    }],
                }]
            })
        if cuerpo.get("intermediates"):
            return _RespuestaExternaSimulada({
                "routes": [{"travelAdvisory": {"tollInfo": {}}}]
            })
        raise AssertionError(f"Solicitud no esperada: {url} {cuerpo}")

    parche_mono.setattr(modulo_mapas.requests, "get", obtener_simulado)
    parche_mono.setattr(modulo_mapas.requests, "post", publicar_simulado)

    respuesta = cliente.post("/api/route", json={
        "origin": "Origen",
        "destination": "Destino",
        "vehicle_type": "GASOLINE",
        "efficiency_km_l": 14,
    })
    contenido = respuesta.get_json()

    assert respuesta.status_code == 200
    assert contenido["ok"] is True
    assert contenido["data"]["toll_count"] == 1
    assert [caseta["name"] for caseta in contenido["data"]["tolls"]] == [
        "Caseta correcta"
    ]
    assert contenido["data"]["total_cost_mxn"] > contenido["data"]["fuel_cost_mxn"]
