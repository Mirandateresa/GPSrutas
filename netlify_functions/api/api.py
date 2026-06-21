import sys
import os
import json

# Agregar el directorio raíz al path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

from app import crear_aplicacion

app = crear_aplicacion()

def handler(event, context):
    """Handler para Netlify Functions"""
    try:
        from werkzeug.wrappers import Request, Response
        
        request = Request({
            'REQUEST_METHOD': event.get('httpMethod', 'GET'),
            'PATH_INFO': event.get('path', '/'),
            'QUERY_STRING': event.get('queryStringParameters', ''),
            'SERVER_NAME': 'netlify',
            'SERVER_PORT': '443',
            'wsgi.url_scheme': 'https',
        })
        
        for key, value in event.get('headers', {}).items():
            request.headers[key] = value
        
        if event.get('body'):
            request._cached_data = event['body'].encode('utf-8')
        
        response = Response.from_app(app, request.environ)
        
        return {
            'statusCode': response.status_code,
            'headers': dict(response.headers),
            'body': response.get_data(as_text=True),
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }