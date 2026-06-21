import requests
from flask import Blueprint, current_app, jsonify, request

from services.mapas import ErrorGoogleMaps, calcular_viaje
from services.zonas import (
    ErrorZonaNoEncontrada,
    ErrorValidacionZona,
    crear_zona,
    eliminar_zona,
    listar_zonas,
    actualizar_zona,
)


plano_api = Blueprint("api", __name__, url_prefix="/api")


def respuesta_error(mensaje, estado_http=400):
    return jsonify({"ok": False, "error": mensaje}), estado_http


@plano_api.get("/health")
def estado_servidor():
    return jsonify({"ok": True, "service": "gps"})


@plano_api.post("/route")
def calcular_ruta_api():
    datos = request.get_json(silent=True) or {}
    origen = str(datos.get("origin", "")).strip()
    destino = str(datos.get("destination", "")).strip()
    tipo_vehiculo = str(
        datos.get("vehicle_type", current_app.config["TIPO_VEHICULO_PREDETERMINADO"])
    ).strip().upper()

    try:
        rendimiento = float(
            datos.get(
                "efficiency_km_l",
                current_app.config["RENDIMIENTO_PREDETERMINADO_KM_L"],
            )
        )
    except (TypeError, ValueError):
        return respuesta_error("El rendimiento debe ser un número válido.")

    if not origen or not destino:
        return respuesta_error("Debes indicar un origen y un destino.")
    if tipo_vehiculo not in {"GASOLINE", "TRUCK"}:
        return respuesta_error("El tipo de vehículo debe ser GASOLINE o TRUCK.")
    if rendimiento <= 0 or rendimiento > 100:
        return respuesta_error("El rendimiento debe estar entre 0 y 100 km/l.")

    try:
        resultado = calcular_viaje(
            origen=origen,
            destino=destino,
            tipo_vehiculo=tipo_vehiculo,
            rendimiento_km_l=rendimiento,
            precio_gasolina_mxn=current_app.config["PRECIO_GASOLINA_MXN"],
            clave_api=current_app.config["CLAVE_API_GOOGLE"],
            tiempo_espera=current_app.config["TIEMPO_ESPERA_GOOGLE_SEGUNDOS"],
            zonas=listar_zonas(current_app.config["ARCHIVO_ZONAS"]),
        )
        return jsonify({"ok": True, "data": resultado})
    except ErrorGoogleMaps as error:
        return respuesta_error(str(error), 400)
    except requests.RequestException:
        current_app.logger.exception("No fue posible contactar Google Maps")
        return respuesta_error("No fue posible conectar con Google Maps.", 502)
    except Exception:
        current_app.logger.exception("Error inesperado calculando la ruta")
        return respuesta_error("Ocurrió un error inesperado al calcular la ruta.", 500)


@plano_api.get("/zones")
def consultar_zonas():
    return jsonify({
        "ok": True,
        "data": listar_zonas(current_app.config["ARCHIVO_ZONAS"]),
    })


@plano_api.post("/zones")
def crear_zona_api():
    try:
        zona = crear_zona(
            current_app.config["ARCHIVO_ZONAS"],
            request.get_json(silent=True) or {},
        )
        return jsonify({"ok": True, "data": zona}), 201
    except ErrorValidacionZona as error:
        return respuesta_error(str(error), 400)


@plano_api.put("/zones/<id_zona>")
def actualizar_zona_api(id_zona):
    try:
        zona = actualizar_zona(
            current_app.config["ARCHIVO_ZONAS"],
            id_zona,
            request.get_json(silent=True) or {},
        )
        return jsonify({"ok": True, "data": zona})
    except ErrorValidacionZona as error:
        return respuesta_error(str(error), 400)
    except ErrorZonaNoEncontrada as error:
        return respuesta_error(str(error), 404)


@plano_api.delete("/zones/<id_zona>")
def eliminar_zona_api(id_zona):
    try:
        eliminar_zona(current_app.config["ARCHIVO_ZONAS"], id_zona)
        return jsonify({"ok": True, "message": "Zona eliminada correctamente."})
    except ErrorZonaNoEncontrada as error:
        return respuesta_error(str(error), 404)
