import requests
import logging
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

# Configurar logging
logger = logging.getLogger(__name__)

plano_api = Blueprint("api", __name__, url_prefix="/api")


def respuesta_error(mensaje, estado_http=400):
    return jsonify({"ok": False, "error": mensaje}), estado_http


@plano_api.get("/health")
def estado_servidor():
    return jsonify({"ok": True, "service": "gps"})


@plano_api.post("/route")
def calcular_ruta_api():
    try:
        # Obtener y registrar datos
        datos = request.get_json(silent=True) or {}
        logger.info(f"📥 Datos recibidos en /api/route: {datos}")
        
        origen = str(datos.get("origin", "")).strip()
        destino = str(datos.get("destination", "")).strip()
        tipo_vehiculo = str(
            datos.get("vehicle_type", current_app.config.get("TIPO_VEHICULO_PREDETERMINADO", "GASOLINE"))
        ).strip().upper()
        
        logger.info(f"📍 Origen: '{origen}', Destino: '{destino}'")
        logger.info(f"🚗 Tipo vehículo: '{tipo_vehiculo}'")

        # Validar rendimiento
        try:
            rendimiento = float(
                datos.get(
                    "efficiency_km_l",
                    current_app.config.get("RENDIMIENTO_PREDETERMINADO_KM_L", 14.0),
                )
            )
        except (TypeError, ValueError) as e:
            logger.error(f"❌ Error en rendimiento: {e}")
            return respuesta_error("El rendimiento debe ser un número válido.")

        # Validaciones
        if not origen or not destino:
            logger.error("❌ Origen o destino vacío")
            return respuesta_error("Debes indicar un origen y un destino.")
            
        if tipo_vehiculo not in {"GASOLINE", "TRUCK"}:
            logger.error(f"❌ Tipo de vehículo inválido: {tipo_vehiculo}")
            return respuesta_error("El tipo de vehículo debe ser GASOLINE o TRUCK.")
            
        if rendimiento <= 0 or rendimiento > 100:
            logger.error(f"❌ Rendimiento inválido: {rendimiento}")
            return respuesta_error("El rendimiento debe estar entre 0 y 100 km/l.")

        logger.info("✅ Datos validados correctamente")

        # Obtener zonas
        archivo_zonas = current_app.config.get("ARCHIVO_ZONAS")
        logger.info(f"📁 Archivo de zonas: {archivo_zonas}")
        
        zonas = listar_zonas(archivo_zonas)
        logger.info(f"📍 Zonas cargadas: {len(zonas)}")

        # Calcular ruta
        logger.info("🔄 Calculando ruta...")
        resultado = calcular_viaje(
            origen=origen,
            destino=destino,
            tipo_vehiculo=tipo_vehiculo,
            rendimiento_km_l=rendimiento,
            precio_gasolina_mxn=current_app.config.get("PRECIO_GASOLINA_MXN", 23.99),
            clave_api=current_app.config.get("CLAVE_API_GOOGLE"),
            tiempo_espera=current_app.config.get("TIEMPO_ESPERA_GOOGLE_SEGUNDOS", 35),
            zonas=zonas,
            usar_optimizacion=current_app.config.get("OPTIMIZACION_ACTIVADA", False),
        )
        
        logger.info("✅ Ruta calculada exitosamente")
        return jsonify({"ok": True, "data": resultado})
        
    except ErrorGoogleMaps as error:
        logger.error(f"❌ Error de Google Maps: {error}")
        return respuesta_error(str(error), 400)
        
    except requests.RequestException as error:
        logger.error(f"❌ Error de conexión: {error}")
        current_app.logger.exception("No fue posible contactar Google Maps")
        return respuesta_error("No fue posible conectar con Google Maps.", 502)
        
    except Exception as error:
        logger.error(f"❌ Error inesperado: {error}")
        current_app.logger.exception("Error inesperado calculando la ruta")
        return respuesta_error(f"Ocurrió un error inesperado: {str(error)}", 500)


@plano_api.get("/zones")
def consultar_zonas():
    try:
        zonas = listar_zonas(current_app.config["ARCHIVO_ZONAS"])
        return jsonify({
            "ok": True,
            "data": zonas,
        })
    except Exception as error:
        logger.error(f"❌ Error al listar zonas: {error}")
        return jsonify({"ok": False, "error": str(error)}), 500


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
    except Exception as error:
        logger.error(f"❌ Error al crear zona: {error}")
        return respuesta_error(f"Error al crear zona: {str(error)}", 500)


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
    except Exception as error:
        logger.error(f"❌ Error al actualizar zona: {error}")
        return respuesta_error(f"Error al actualizar zona: {str(error)}", 500)


@plano_api.delete("/zones/<id_zona>")
def eliminar_zona_api(id_zona):
    try:
        eliminar_zona(current_app.config["ARCHIVO_ZONAS"], id_zona)
        return jsonify({"ok": True, "message": "Zona eliminada correctamente."})
    except ErrorZonaNoEncontrada as error:
        return respuesta_error(str(error), 404)
    except Exception as error:
        logger.error(f"❌ Error al eliminar zona: {error}")
        return respuesta_error(f"Error al eliminar zona: {str(error)}", 500)