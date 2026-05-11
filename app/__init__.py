from flask import Flask, jsonify
from flasgger import Swagger
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os
from werkzeug.exceptions import HTTPException

db = SQLAlchemy()

def create_app():
    """
    Fábrica de aplicaciones Flask. Configura y devuelve la instancia de la aplicación.
    """
    app = Flask(__name__)
    
    # Cargar variables de entorno desde el archivo .env
    load_dotenv()

    # Configuración de Base de Datos (PostgreSQL)
    # Normalización para compatibilidad con SQLAlchemy 1.4+ y diversos hostings
    db_url = os.getenv("DATABASE_URL", "postgresql://user:password@host/db")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Configuración para mejorar la apariencia de Swagger (UI versión 3)
    app.config['SWAGGER'] = {
        'title': 'Mi API Dinámica',
        'uiversion': 3,
        'tryItOutEnabled': True,
        'displayRequestDuration': True
    }

    db.init_app(app)

    # Inicializar Swagger con metadatos personalizados
    Swagger(app, template={
        "info": {
            "title": "Documentación de API",
            "description": """
Documentación interactiva generada automáticamente.

### 🔍 Guía de Filtros
Puedes filtrar los recursos usando parámetros en la URL con sufijos especiales:
- **Exacto:** `?campo=valor`
- **Búsqueda:** `?campo__ilike=texto` (insensible a mayúsculas)
- **Rango:** `?precio__gt=10` (mayor), `__lt` (menor), `__gte`, `__lte`.
            """,
            "version": "1.0.0"
        },
        "tags": [
            {
                "name": "1. Gestión de Recursos",
                "description": "Operaciones para listar, renombrar y eliminar colecciones completas (ej. 'productos', 'usuarios')."
            },
            {
                "name": "2. Gestión de Items (CRUD)",
                "description": "Operaciones para los items individuales dentro de una colección. Incluye filtros y paginación."
            },
            {
                "name": "3. Simulación y Pruebas",
                "description": "Endpoints para probar el comportamiento de la API bajo condiciones de error simuladas."
            }
        ]
    })

    from .routes import api
    app.register_blueprint(api)

    @app.errorhandler(HTTPException)
    def handle_exception(e):
        """Asegura que todos los errores HTTP devuelvan JSON en lugar de HTML."""
        response = e.get_response()
        response.data = jsonify({
            "code": e.code,
            "name": e.name,
            "description": e.description,
        }).data
        response.content_type = "application/json"
        return response

    with app.app_context():
        db.create_all()

    return app
