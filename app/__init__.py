from flask import Flask
from flasgger import Swagger
from .routes import api

def create_app():
    """
    Fábrica de aplicaciones Flask. Configura y devuelve la instancia de la aplicación.
    """
    app = Flask(__name__)

    # Configuración para mejorar la apariencia de Swagger (UI versión 3)
    app.config['SWAGGER'] = {
        'title': 'Mi API Dinámica',
        'uiversion': 3,
        'tryItOutEnabled': True,
        'displayRequestDuration': True
    }

    # Inicializar Swagger con metadatos personalizados
    Swagger(app, template={
        "info": {
            "title": "Documentación de API",
            "description": "Documentación interactiva generada automáticamente.",
            "version": "1.0.0"
        },
        "tags": [
            {
                "name": "resources",
                "description": "Operaciones para listar las colecciones de recursos disponibles."
            },
            {
                "name": "items",
                "description": "Operaciones CRUD estándar para los items dentro de una colección."
            },
            {
                "name": "Testing & Simulation",
                "description": "Endpoints para probar el comportamiento de la API bajo condiciones de error."
            }
        ]
    })

    app.register_blueprint(api)

    return app
