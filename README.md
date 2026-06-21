# GPS — Rutas seguras

Aplicación web desarrollada con Flask, JavaScript y servicios de mapas para calcular recorridos, estimar combustible y peajes, mostrar únicamente las casetas asociadas al trayecto seleccionado y administrar zonas rojas.

Esta edición no contiene WhatsApp, Baileys, ESP32, módulo GPS físico, tanque, sensor ultrasónico ni alertas de combustible.

## Funciones del proyecto

- Mapa interactivo.
- Autocompletado de origen y destino.
- Selección de puntos haciendo clic sobre el mapa.
- Cálculo de una o varias alternativas de ruta.
- Selección de ruta mediante distancia Manhattan y Dijkstra.
- Distancia y duración aproximadas.
- Detección de recorridos con peaje.
- Costo estimado de peajes cuando el servicio lo proporciona.
- Filtrado estricto de casetas para no mostrar plazas de cobro cercanas que pertenecen a otra carretera.
- Estimación de litros y costo de gasolina.
- Cálculo del costo total del viaje.
- Visualización, creación, edición y eliminación de zonas rojas.
- Detección de zonas rojas intersectadas por el trayecto.
- Persistencia de zonas en un archivo JSON.
- Pruebas automáticas del backend, endpoints, algoritmos, zonas y filtrado de casetas.

## Estructura

```text
gps/
├── app.py
├── configuracion.py
├── requirements.txt
├── pytest.ini
├── README.md
├── .gitignore
│
├── routes/
│   ├── __init__.py
│   ├── paginas.py
│   └── api.py
│
├── services/
│   ├── __init__.py
│   ├── mapas.py
│   ├── casetas.py
│   ├── motor_rutas.py
│   └── zonas.py
│
├── data/
│   └── zonas_rojas.json
│
├── templates/
│   └── index.html
│
├── static/
│   ├── css/
│   │   └── estilos.css
│   └── js/
│       ├── aplicacion.js
│       ├── mapa.js
│       └── zonas.js
│
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── prueba_api.py
    └── prueba_servicios.py
```

Las carpetas se mantienen en inglés. Los archivos, funciones y variables propias del proyecto están en español, excepto `app.py`, solicitado con ese nombre, y nombres obligatorios de librerías o APIs.

## Función de los archivos

### `app.py`

Punto de entrada del proyecto.

- Crea la aplicación Flask.
- Carga `Configuracion`.
- Registra las rutas.
- Inicia el servidor.

### `configuracion.py`

Concentra las variables modificables:

- Clave de la API.
- Precio de gasolina.
- Rendimiento predeterminado.
- Tipo de vehículo.
- Archivo de zonas.
- Tiempo de espera.
- Puerto y modo de depuración.

La clave se escribe directamente aquí:

```python
CLAVE_API_GOOGLE = "AIzaSyBI7-JK1Ll0OQGwG7n0tTdkQAYRDN4f094"
```

### `routes/paginas.py`

Renderiza `templates/index.html` y envía a la plantilla la clave y el rendimiento predeterminado.

### `routes/api.py`

Contiene los endpoints del backend:

- Cálculo de ruta.
- Estado del servidor.
- Consulta de zonas.
- Creación de zonas.
- Actualización de zonas.
- Eliminación de zonas.

### `services/mapas.py`

Coordina el cálculo del viaje:

1. Convierte origen y destino en coordenadas.
2. Solicita las alternativas de ruta.
3. Selecciona una alternativa mediante el motor matemático.
4. Solicita las casetas de la alternativa elegida.
5. Detecta las zonas rojas intersectadas.
6. Calcula litros, gasolina, peajes y total.

También procesa la información general de distancia, duración y costo de peajes.

### `services/casetas.py`

Contiene el filtrado de casetas. Se separó de `mapas.py` para evitar un archivo excesivamente grande.

El proceso es el siguiente:

1. Solo se buscan casetas después de seleccionar la ruta definitiva.
2. La búsqueda se realiza sobre la polilínea completa mediante `searchAlongRouteParameters`.
3. Se calcula la distancia real entre cada caseta y cada segmento de la ruta.
4. Se descartan lugares ubicados a más de 60 metros de la polilínea.
5. Para cada candidato restante se consulta un tramo corto de la ruta y se confirma que dicho tramo reporte peaje.
6. Si esa segunda validación no está disponible, únicamente se acepta el lugar si está a 25 metros o menos de la ruta.
7. Se eliminan casetas duplicadas.
8. Los resultados se ordenan según su posición en el recorrido.

Esto evita el problema de mostrar casetas cercanas, de salidas, distribuidores o carreteras paralelas por las que el trayecto no pasa.

Si no se logra obtener el nombre de una caseta, el respaldo utiliza los pasos del recorrido con peaje y coloca puntos estimados directamente sobre la ruta. No utiliza una búsqueda amplia alrededor del mapa.

### `services/motor_rutas.py`

Incluye los algoritmos de rutas:

- Decodificación de polilíneas.
- Distancia Manhattan.
- Construcción de un grafo.
- Dijkstra.
- Evaluación y selección de alternativas.

### `services/zonas.py`

Administra las zonas rojas:

- Lectura y escritura segura del JSON.
- Validación de datos.
- CRUD de zonas.
- Fórmula de Haversine.
- Distancia de un punto a un segmento.
- Detección de intersección entre ruta y zona.

### `templates/index.html`

Contiene solamente la estructura visual:

- Formulario de origen y destino.
- Vehículo y rendimiento.
- Panel de resultados.
- Lista de casetas.
- Herramientas de zonas rojas.
- Diálogo para crear o editar zonas.

Los mensajes visibles ya no indican que otro servicio “hace los cálculos”. La interfaz únicamente muestra el estado de la operación y sus resultados.

### `static/js/aplicacion.js`

- Envía la solicitud de ruta.
- Valida el formulario.
- Muestra distancia, duración y costos.
- Muestra casetas y zonas detectadas.
- Controla los botones generales.

### `static/js/mapa.js`

- Inicializa el mapa.
- Configura el autocompletado.
- Permite seleccionar puntos.
- Dibuja la polilínea.
- Dibuja marcadores de origen, destino y casetas.

### `static/js/zonas.js`

- Consulta las zonas.
- Dibuja sus círculos.
- Abre el formulario.
- Crea, edita y elimina zonas.

### `data/zonas_rojas.json`

Almacena las zonas rojas. No se necesita una base de datos para ejecutar esta versión.

## Requisitos

- Windows, Linux o macOS.
- Python 3.10 o posterior.
- Acceso a Internet durante el uso del mapa.
- Una API key con los servicios necesarios habilitados.

Dependencias de Python:

```text
Flask
requests
pytest
```

Están declaradas en `requirements.txt`.

## Servicios que debes habilitar

En el mismo proyecto de Google Cloud habilita:

1. Maps JavaScript API.
2. Places API (New).
3. Geocoding API.
4. Routes API.
5. Facturación del proyecto.

Si Places API (New) no está habilitada, el sistema puede detectar el costo del peaje, pero utilizará puntos estimados de los pasos del recorrido en lugar de nombres de casetas.

## Instalación en Windows PowerShell

Entra a la carpeta del proyecto:

```powershell
cd C:\ruta\donde\descomprimiste\gps
```

Comprueba Python:

```powershell
python --version
```

Crea el entorno virtual:

```powershell
python -m venv .venv
```

Actívalo:

```powershell
.\.venv\Scripts\Activate.ps1
```

Si PowerShell bloquea la activación:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Instala las dependencias:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Coloca tu clave en `configuracion.py`:

```python
CLAVE_API_GOOGLE = "AIzaSyBI7-JK1Ll0OQGwG7n0tTdkQAYRDN4f094"
```

Ejecuta:

```powershell
python app.py
```

Abre:

```text
http://localhost:5000
```

No abras `templates/index.html` con doble clic. Debe ser procesado por Flask.

## Instalación en Linux

```bash
cd /ruta/al/proyecto/gps
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

Luego visita:

```text
http://localhost:5000
```

## Uso

1. Escribe el origen.
2. Selecciona una sugerencia.
3. Escribe el destino.
4. Selecciona una sugerencia.
5. Elige automóvil o camión.
6. Indica el rendimiento en kilómetros por litro.
7. Presiona **Calcular ruta**.
8. Revisa distancia, duración, combustible, peajes y total.
9. Las casetas mostradas corresponden a la polilínea seleccionada o a puntos de peaje estimados sobre ella.

También puedes elegir el origen y el destino haciendo clic en el mapa.

## Endpoints

| Método | Endpoint | Función |
|---|---|---|
| GET | `/` | Mostrar la aplicación |
| GET | `/api/health` | Comprobar el servidor |
| POST | `/api/route` | Calcular una ruta |
| GET | `/api/zones` | Consultar zonas |
| POST | `/api/zones` | Crear una zona |
| PUT | `/api/zones/<id>` | Editar una zona |
| DELETE | `/api/zones/<id>` | Eliminar una zona |

Ejemplo de solicitud:

```json
{
  "origin": "Jilotepec, Estado de México",
  "destination": "Querétaro, Querétaro",
  "vehicle_type": "GASOLINE",
  "efficiency_km_l": 14
}
```

## Fórmulas y algoritmos

### Combustible

```text
litros = distancia_km / rendimiento_km_l
```

### Costo de combustible

```text
costo_combustible = litros * precio_por_litro
```

### Costo total

```text
costo_total = costo_combustible + costo_peajes
```

### Distancia Manhattan

```text
d = |x2 - x1| + |y2 - y1|
```

### Dijkstra

Se utiliza para recorrer el grafo construido con los puntos de una alternativa y obtener su costo acumulado.

### Haversine y punto a segmento

Se utilizan para medir distancias geográficas y determinar si una zona o una caseta se encuentra realmente sobre el trayecto.

## Pruebas

Ejecuta:

```powershell
pytest
```

También puedes usar:

```powershell
python -m pytest
```

Las pruebas incluidas verifican:

- Carga de `index.html`.
- Estado del servidor.
- CRUD de zonas.
- Validación de formularios.
- Decodificación de polilíneas.
- Dijkstra.
- Distancia Manhattan.
- Intersección de zonas.
- Flujo completo del endpoint de rutas con servicios simulados.
- Descarte de una caseta alejada de la polilínea.
- Descarte de una caseta de una carretera paralela.
- Margen máximo de 25 metros cuando la validación adicional no está disponible.

Las pruebas automáticas no consumen cuota porque simulan las respuestas externas.

Para comprobar la API real debes colocar tu clave, tener Internet y calcular una ruta desde el navegador. El resultado externo depende de la información disponible para esa carretera y de las restricciones configuradas en la clave.

## Comprobaciones de sintaxis

Python:

```powershell
python -m compileall .
```

JavaScript, teniendo Node.js instalado:

```powershell
node --check static/js/aplicacion.js
node --check static/js/mapa.js
node --check static/js/zonas.js
```

## Solución de problemas

### `py` no se reconoce

Usa:

```powershell
python -m venv .venv
```

### `python` no se reconoce

Instala Python y marca **Add python.exe to PATH**. Después reinicia PowerShell.

### El mapa no carga

- Revisa `CLAVE_API_GOOGLE` en `configuracion.py`.
- Habilita Maps JavaScript API.
- Revisa las restricciones por dominio.
- Comprueba que la facturación esté activa.

### El mapa carga, pero no calcula

- Habilita Geocoding API y Routes API.
- Revisa las restricciones por IP para solicitudes del backend.
- Observa la terminal donde se ejecuta Flask.

### Hay costo de peaje, pero no aparecen nombres

- Habilita Places API (New).
- Revisa que la misma clave pueda utilizar ese servicio.
- El proyecto mostrará puntos estimados sobre la ruta cuando no existan nombres verificables.

### Una caseta cercana no aparece

Esto puede ser correcto. El filtro descarta deliberadamente lugares que no están sobre la polilínea o que pertenecen a una vía paralela. El objetivo es evitar falsos positivos.

## Seguridad

La clave está directamente en `configuracion.py` porque así fue solicitado. Antes de publicar el proyecto:

1. Borra la clave real.
2. Restringe la clave por API.
3. Configura restricciones de dominio para la parte web.
4. Configura restricciones adecuadas para las solicitudes del servidor.
5. No subas una clave sin restricciones a un repositorio público.
