import sys
import os
import json
from io import BytesIO

# Agregar el directorio raíz al path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

from app import crear_aplicacion

# Crear la aplicación
app = crear_aplicacion()

def handler(event, context):
    """Handler para Netlify Functions"""
    try:
        # Extraer información de la solicitud
        path = event.get('path', '/')
        method = event.get('httpMethod', 'GET')
        headers = event.get('headers', {})
        body = event.get('body', '')
        
        # Construir el entorno WSGI
        environ = {
            'REQUEST_METHOD': method,
            'PATH_INFO': path,
            'QUERY_STRING': '',
            'CONTENT_TYPE': headers.get('content-type', ''),
            'CONTENT_LENGTH': str(len(body)) if body else '0',
            'wsgi.input': BytesIO(body.encode('utf-8')) if body else BytesIO(),
            'wsgi.errors': sys.stderr,
            'wsgi.version': (1, 0),
            'wsgi.multithread': False,
            'wsgi.multiprocess': True,
            'wsgi.run_once': True,
            'SERVER_NAME': 'netlify',
            'SERVER_PORT': '443',
            'SERVER_PROTOCOL': 'HTTP/1.1',
            'wsgi.url_scheme': 'https',
        }
        
        # Agregar headers
        for key, value in headers.items():
            key = key.upper().replace('-', '_')
            if key not in ['CONTENT_TYPE', 'CONTENT_LENGTH']:
                environ[f'HTTP_{key}'] = value
        
        # Agregar variable de Netlify
        environ['NETLIFY'] = 'true'
        
        # Ejecutar Flask
        response = app.wsgi_app(environ, lambda *args, **kwargs: None)
        
        # Procesar respuesta
        if isinstance(response, tuple):
            status_code = int(response[0].split()[0])
            headers_dict = dict(response[1])
            body_content = b''.join(response[2]) if hasattr(response[2], '__iter__') else b''
        else:
            status_code = 200
            headers_dict = {}
            body_content = b''
        
        # Si el body está vacío, devolver un mensaje de error amigable
        if not body_content:
            body_content = b'<h1>GPS - Rutas Seguras</h1><p>La aplicacion esta cargando...</p><a href="/mapa">Ir al mapa</a>'
        
        return {
            'statusCode': status_code,
            'headers': {
                'Content-Type': 'text/html; charset=utf-8',
            },
            'body': body_content.decode('utf-8') if isinstance(body_content, bytes) else str(body_content),
        }
        
    except Exception as e:
        error_msg = f"Error en el handler: {str(e)}"
        print(error_msg)
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'ok': False, 'error': str(e)})
        }