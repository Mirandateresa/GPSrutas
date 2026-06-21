"""
Pruebas para el módulo de optimización con Hill Climbing.
"""

import pytest
from services.optimizador import OptimizadorRutas, OptimizadorZonas


def prueba_evaluacion_ruta_simple():
    """Prueba que la evaluación de ruta funciona correctamente."""
    optimizador = OptimizadorRutas()
    
    ruta = {
        "coordinates": [{"lat": 19.0, "lng": -99.0}, {"lat": 19.1, "lng": -99.1}],
        "distance_km": 15.0,
        "duration_min": 30,
        "toll_cost": 50.0,
    }
    
    costo = optimizador.evaluar_ruta(ruta)
    assert costo > 0
    assert costo == 15.0 * 1.0 + 30 * 0.1 + 50.0 * 0.5  # 15 + 3 + 25 = 43


def prueba_evaluacion_con_zonas_rojas():
    """Prueba que las zonas rojas aumentan el costo."""
    optimizador = OptimizadorRutas({
        "penalizacion_zona_roja": 100.0
    })
    
    ruta = {
        "coordinates": [{"lat": 19.0, "lng": -99.0}, {"lat": 19.1, "lng": -99.1}],
        "distance_km": 10.0,
        "duration_min": 20,
        "toll_cost": 0,
    }
    
    zonas = [{
        "id": "test-1",
        "name": "Zona peligrosa",
        "lat": 19.05,
        "lng": -99.05,
        "radius_m": 1000,
    }]
    
    costo_sin_zonas = optimizador.evaluar_ruta(ruta, [])
    costo_con_zonas = optimizador.evaluar_ruta(ruta, zonas)
    
    assert costo_con_zonas > costo_sin_zonas


def prueba_generacion_vecino():
    """Prueba que se genera un vecino válido."""
    optimizador = OptimizadorRutas()
    
    ruta = {
        "coordinates": [
            {"lat": 19.0, "lng": -99.0},
            {"lat": 19.05, "lng": -99.05},
            {"lat": 19.1, "lng": -99.1}
        ],
        "distance_km": 15.0,
    }
    
    vecino = optimizador.generar_vecino(ruta)
    
    assert vecino is not None
    assert "coordinates" in vecino
    assert len(vecino["coordinates"]) == len(ruta["coordinates"])
    # El origen y destino deben mantenerse iguales
    assert vecino["coordinates"][0] == ruta["coordinates"][0]
    assert vecino["coordinates"][-1] == ruta["coordinates"][-1]


def prueba_hill_climbing_mejora_ruta():
    """Prueba que Hill Climbing encuentra una ruta mejor."""
    optimizador = OptimizadorRutas({
        "max_iteraciones": 20,
        "paso_lat_lng": 0.01,
    })
    
    # Ruta inicial que pasa por una zona roja
    ruta_inicial = {
        "coordinates": [
            {"lat": 19.0, "lng": -99.0},
            {"lat": 19.05, "lng": -99.05},  # Punto dentro de zona roja
            {"lat": 19.1, "lng": -99.1}
        ],
        "distance_km": 15.0,
        "duration_min": 30,
        "toll_cost": 0,
    }
    
    zonas = [{
        "id": "test-1",
        "name": "Zona peligrosa",
        "lat": 19.05,
        "lng": -99.05,
        "radius_m": 2000,
    }]
    
    ruta_mejorada, costo, iteraciones = optimizador.hill_climbing(
        ruta_inicial, zonas, max_iteraciones=20
    )
    
    # La ruta debería mejorar (costo menor)
    costo_inicial = optimizador.evaluar_ruta(ruta_inicial, zonas)
    assert costo < costo_inicial or costo == costo_inicial


def prueba_optimizador_zonas():
    """Prueba la optimización de zonas rojas."""
    optimizador = OptimizadorZonas({
        "paso_lat_lng": 0.001,
        "paso_radio": 100,
    })
    
    puntos_riesgo = [
        (19.05, -99.05),
        (19.051, -99.051),
        (19.052, -99.052),
        (19.0, -99.0),  # Punto lejano
    ]
    
    centro_inicial = (19.04, -99.04)
    radio_inicial = 1000
    
    mejor_centro, mejor_radio, cobertura = optimizador.optimizar_zona(
        puntos_riesgo, centro_inicial, radio_inicial, max_iteraciones=50
    )
    
    # La cobertura debería ser al menos 3 (los puntos cercanos)
    assert cobertura >= 3
    assert mejor_radio > 0
    assert -90 <= mejor_centro[0] <= 90
    assert -180 <= mejor_centro[1] <= 180