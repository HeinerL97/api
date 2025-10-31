from flask import Flask
from .routes import api

def create_app():
    """
    Fábrica de aplicaciones Flask. Configura y devuelve la instancia de la aplicación.
    """
    app = Flask(__name__)

    app.register_blueprint(api)

    return app
