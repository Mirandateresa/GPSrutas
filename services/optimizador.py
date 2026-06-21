"""
Módulo de optimización de rutas usando algoritmos heurísticos.
Hill Climbing y otros algoritmos de búsqueda local.
"""

import random
import math
from typing import List, Dict, Any, Tuple, Optional

from services.zonas import zonas_intersectan_ruta, distancia_a_ruta_m
from services.motor_rutas import decodificar_polilinea


class OptimizadorRutas:
    """Clase para optimizar rutas usando Hill Climbing y otros algoritmos."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Inicializa el optimizador con parámetros de configuración.
        
        Args:
            config: Diccionario con parámetros como:
                - max_iteraciones: int (default: 100)
                - paso_lat_lng: float (default: 0.001) ~111 metros
                - penalizacion_zona_roja: float (default: 50.0)
                - peso_distancia: float (default: 1.0)
                - peso_peaje: float (default: 0.5)
                - peso_tiempo: float (default: 0.1)
        """
        self.config = config or {}
        self.max_iteraciones = self.config.get("max_iteraciones", 100)
        self.paso = self.config.get("paso_lat_lng", 0.001)
        self.penalizacion_zona = self.config.get("penalizacion_zona_roja", 50.0)
        self.peso_distancia = self.config.get("peso_distancia", 1.0)
        self.peso_peaje = self.config.get("peso_peaje", 0.5)
        self.peso_tiempo = self.config.get("peso_tiempo", 0.1)
        self.peso_casetas = self.config.get("peso_casetas", 0.3)
        
    def evaluar_ruta(
        self, 
        ruta: Dict[str, Any], 
        zonas_rojas: List[Dict[str, Any]] = None,
        peajes: List[Dict[str, Any]] = None
    ) -> float:
        """
        Evalúa una ruta calculando un costo total.
        Menor costo = mejor ruta.
        
        Args:
            ruta: Diccionario con datos de la ruta (coordenadas, distancia, etc.)
            zonas_rojas: Lista de zonas rojas para penalizar
            peajes: Lista de peajes para considerar
            
        Returns:
            float: Costo total de la ruta (menor es mejor)
        """
        costo = 0.0
        
        # Factor 1: Distancia total (menos es mejor)
        distancia = ruta.get("distance_km", 0)
        costo += distancia * self.peso_distancia
        
        # Factor 2: Tiempo de viaje
        duracion = ruta.get("duration_min", 0)
        costo += duracion * self.peso_tiempo
        
        # Factor 3: Peajes (menos es mejor)
        costo_peaje = ruta.get("toll_cost", 0)
        costo += costo_peaje * self.peso_peaje
        
        # Factor 4: Número de casetas
        if peajes:
            costo += len(peajes) * self.peso_casetas
        
        # Factor 5: Zonas rojas (penalización fuerte)
        if zonas_rojas and "coordinates" in ruta:
            coordenadas = ruta["coordinates"]
            if coordenadas:
                # Convertir a tuplas para la función de intersección
                puntos_ruta = [(p["lat"], p["lng"]) for p in coordenadas]
                intersectadas = zonas_intersectan_ruta(puntos_ruta, zonas_rojas)
                costo += len(intersectadas) * self.penalizacion_zona
        
        return costo
    
    def generar_vecino(self, ruta: Dict[str, Any]) -> Dict[str, Any]:
        """
        Genera una ruta vecina modificando ligeramente los puntos intermedios.
        
        Args:
            ruta: Ruta actual
            
        Returns:
            Dict: Ruta vecina modificada
        """
        vecino = ruta.copy()
        
        if "coordinates" not in vecino or len(vecino["coordinates"]) < 3:
            return vecino
        
        # Crear copia de coordenadas
        puntos = [p.copy() for p in vecino["coordinates"]]
        
        # Seleccionar un punto aleatorio (excepto origen y destino)
        idx = random.randint(1, len(puntos) - 2)
        
        # Modificar ligeramente la latitud y longitud
        direcciones = [
            (self.paso, 0),
            (-self.paso, 0),
            (0, self.paso),
            (0, -self.paso),
            (self.paso, self.paso),
            (-self.paso, -self.paso),
            (self.paso, -self.paso),
            (-self.paso, self.paso)
        ]
        
        dx, dy = random.choice(direcciones)
        puntos[idx]["lat"] += dx * random.uniform(0.5, 1.5)
        puntos[idx]["lng"] += dy * random.uniform(0.5, 1.5)
        
        # Mantener dentro de límites geográficos
        puntos[idx]["lat"] = max(-90, min(90, puntos[idx]["lat"]))
        puntos[idx]["lng"] = max(-180, min(180, puntos[idx]["lng"]))
        
        vecino["coordinates"] = puntos
        
        # Recalcular la distancia si es posible (aproximada)
        if len(puntos) > 1:
            distancia_total = 0
            for i in range(len(puntos) - 1):
                p1 = puntos[i]
                p2 = puntos[i + 1]
                # Distancia Manhattan aproximada
                lat_media = math.radians((p1["lat"] + p2["lat"]) / 2)
                lat_km = abs(p2["lat"] - p1["lat"]) * 111.32
                lng_km = abs(p2["lng"] - p1["lng"]) * 111.32 * math.cos(lat_media)
                distancia_total += lat_km + lng_km
            vecino["distance_km"] = round(distancia_total, 2)
            vecino["distance_m"] = round(distancia_total * 1000, 2)
        
        return vecino
    
    def hill_climbing(
        self, 
        ruta_inicial: Dict[str, Any],
        zonas_rojas: List[Dict[str, Any]] = None,
        peajes: List[Dict[str, Any]] = None,
        max_iteraciones: int = None
    ) -> Tuple[Dict[str, Any], float, int]:
        """
        Aplica el algoritmo Hill Climbing para mejorar la ruta.
        
        Args:
            ruta_inicial: Ruta inicial (de Google Maps)
            zonas_rojas: Lista de zonas rojas
            peajes: Lista de peajes
            max_iteraciones: Número máximo de iteraciones
            
        Returns:
            Tuple: (mejor_ruta, mejor_costo, iteraciones_usadas)
        """
        if max_iteraciones is None:
            max_iteraciones = self.max_iteraciones
        
        # Ruta actual y mejor ruta
        ruta_actual = ruta_inicial.copy()
        mejor_ruta = ruta_inicial.copy()
        
        # Evaluar costo inicial
        costo_actual = self.evaluar_ruta(ruta_actual, zonas_rojas, peajes)
        mejor_costo = costo_actual
        
        iteraciones = 0
        sin_mejora = 0
        max_sin_mejora = max_iteraciones // 4  # Parar si no mejora después de 25% de iteraciones
        
        for i in range(max_iteraciones):
            iteraciones += 1
            
            # Generar vecino
            vecino = self.generar_vecino(ruta_actual)
            costo_vecino = self.evaluar_ruta(vecino, zonas_rojas, peajes)
            
            # Si el vecino es mejor, mover a él
            if costo_vecino < costo_actual:
                ruta_actual = vecino
                costo_actual = costo_vecino
                sin_mejora = 0
                
                # Actualizar mejor solución global
                if costo_actual < mejor_costo:
                    mejor_ruta = ruta_actual.copy()
                    mejor_costo = costo_actual
            else:
                sin_mejora += 1
            
            # Criterio de parada temprana
            if sin_mejora >= max_sin_mejora:
                break
        
        return mejor_ruta, mejor_costo, iteraciones
    
    def hill_climbing_multi_inicio(
        self,
        rutas_iniciales: List[Dict[str, Any]],
        zonas_rojas: List[Dict[str, Any]] = None,
        peajes: List[Dict[str, Any]] = None,
        iteraciones_por_ruta: int = 50
    ) -> Tuple[Dict[str, Any], float]:
        """
        Aplica Hill Climbing desde múltiples puntos de inicio.
        Ayuda a evitar mínimos locales.
        
        Args:
            rutas_iniciales: Lista de rutas iniciales (alternativas de Google)
            zonas_rojas: Lista de zonas rojas
            peajes: Lista de peajes
            iteraciones_por_ruta: Iteraciones para cada punto de inicio
            
        Returns:
            Tuple: (mejor_ruta, mejor_costo)
        """
        mejor_ruta_global = None
        mejor_costo_global = float("inf")
        
        for idx, ruta_inicial in enumerate(rutas_iniciales):
            ruta_mejorada, costo, iteraciones = self.hill_climbing(
                ruta_inicial,
                zonas_rojas,
                peajes,
                iteraciones_por_ruta
            )
            
            if costo < mejor_costo_global:
                mejor_costo_global = costo
                mejor_ruta_global = ruta_mejorada
        
        return mejor_ruta_global, mejor_costo_global


class OptimizadorZonas:
    """Optimiza la posición y radio de zonas rojas usando Hill Climbing."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.paso = self.config.get("paso_lat_lng", 0.0005)  # ~55 metros
        self.paso_radio = self.config.get("paso_radio", 50)  # 50 metros
        
    def calcular_cobertura(
        self,
        puntos_riesgo: List[Tuple[float, float]],
        centro: Tuple[float, float],
        radio: float
    ) -> float:
        """
        Calcula cuántos puntos de riesgo están dentro de la zona.
        
        Returns:
            float: Número de puntos cubiertos (mayor es mejor)
        """
        cobertura = 0
        for lat, lng in puntos_riesgo:
            distancia = math.sqrt(
                (lat - centro[0]) ** 2 + (lng - centro[1]) ** 2
            )
            # Convertir a metros (aproximado)
            distancia_m = distancia * 111320
            if distancia_m <= radio:
                cobertura += 1
        return cobertura
    
    def optimizar_zona(
        self,
        puntos_riesgo: List[Tuple[float, float]],
        centro_inicial: Tuple[float, float],
        radio_inicial: float,
        max_iteraciones: int = 100
    ) -> Tuple[Tuple[float, float], float, float]:
        """
        Optimiza el centro y radio de una zona roja.
        
        Returns:
            Tuple: (mejor_centro, mejor_radio, mejor_cobertura)
        """
        mejor_centro = centro_inicial
        mejor_radio = radio_inicial
        mejor_cobertura = self.calcular_cobertura(
            puntos_riesgo, mejor_centro, mejor_radio
        )
        
        direcciones = [
            (self.paso, 0),
            (-self.paso, 0),
            (0, self.paso),
            (0, -self.paso)
        ]
        
        for _ in range(max_iteraciones):
            mejora = False
            
            # Intentar mover el centro en las 4 direcciones
            for dx, dy in direcciones:
                nuevo_centro = (mejor_centro[0] + dx, mejor_centro[1] + dy)
                cobertura = self.calcular_cobertura(
                    puntos_riesgo, nuevo_centro, mejor_radio
                )
                
                if cobertura > mejor_cobertura:
                    mejor_centro = nuevo_centro
                    mejor_cobertura = cobertura
                    mejora = True
                    break
            
            # Si no hubo mejora moviendo el centro, ajustar el radio
            if not mejora:
                # Probar a aumentar el radio
                nuevo_radio = mejor_radio + self.paso_radio
                cobertura = self.calcular_cobertura(
                    puntos_riesgo, mejor_centro, nuevo_radio
                )
                if cobertura > mejor_cobertura:
                    mejor_radio = nuevo_radio
                    mejor_cobertura = cobertura
                    continue
                
                # Probar a disminuir el radio (más específico)
                nuevo_radio = max(50, mejor_radio - self.paso_radio)
                cobertura = self.calcular_cobertura(
                    puntos_riesgo, mejor_centro, nuevo_radio
                )
                # Solo aceptar si no perdemos cobertura
                if cobertura >= mejor_cobertura and nuevo_radio < mejor_radio:
                    mejor_radio = nuevo_radio
                    mejor_cobertura = cobertura
                    continue
                
                # Si no hay mejora, reducir el paso para refinar
                self.paso *= 0.9
                if self.paso < 0.00001:  # ~1 metro
                    break
        
        return mejor_centro, mejor_radio, mejor_cobertura