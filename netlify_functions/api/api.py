import sys
import os
import json

# Agregar el directorio raíz al path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

from app import app

def handler(event, context):
    """Handler para Netlify Functions"""
    try:
        from werkzeug.wrappers import Request, Response
        
        # Obtener la ruta
        path = event.get('path', '/')
        
        # Crear request
        request = Request({
            'REQUEST_METHOD': event.get('httpMethod', 'GET'),
            'PATH_INFO': path,
            'QUERY_STRING': event.get('queryStringParameters', ''),
            'SERVER_NAME': 'netlify',
            'SERVER_PORT': '443',
            'wsgi.url_scheme': 'https',
        })
        
        # Headers
        for key, value in event.get('headers', {}).items():
            request.headers[key] = value
        
        # Body
        if event.get('body'):
            request._cached_data = event['body'].encode('utf-8')
        
        # Ejecutar Flask
        response = Response.from_app(app, request.environ)
        
        return {
            'statusCode': response.status_code,
            'headers': dict(response.headers),
            'body': response.get_data(as_text=True),
        }
        
    except Exception as e:
        # Si hay error, devolver una página HTML simple
        error_html = f"""
        <!DOCTYPE html>
        <html>
        <head><title>GPS - Error</title></head>
        <body>
            <h1>📍 GPS - Rutas Seguras</h1>
            <p>Error al cargar la aplicación: {str(e)}</p>
            <a href="/">Volver al inicio</a>
        </body>
        </html>
        """
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'text/html; charset=utf-8'},
            'body': error_html
        }