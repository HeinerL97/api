from flask import Blueprint, request, jsonify, abort, g
from app import db
import time
import logging
import os

api = Blueprint('api', __name__)
logger = logging.getLogger(__name__)

# Constantes para la simulación de latencia global (se pueden configurar vía .env)
DEFAULT_GLOBAL_DELAY_SECONDS = float(os.getenv("DEFAULT_GLOBAL_DELAY", 0.5))
MAX_GLOBAL_DELAY_SECONDS = float(os.getenv("MAX_GLOBAL_DELAY", 120))

# Modelo de base de datos para items dinámicos
class Item(db.Model):
    __tablename__ = 'items'
    id = db.Column(db.Integer, primary_key=True)
    resource_name = db.Column(db.String(64), index=True, nullable=False)
    data = db.Column(db.JSON, nullable=False)

    def to_dict(self):
        item = self.data.copy()
        item['_id'] = self.id
        return item

@api.before_request
def handle_global_delay_and_json_body():
    """
    Maneja la latencia simulada global (parámetro __delay) y pre-procesa el cuerpo JSON.
    """
    # 1. Manejo de Latencia
    requested_delay = request.args.get('__delay', type=float)
    
    if requested_delay is not None:
        # Prioridad: Parámetro __delay explícito (permite 0 para desactivar)
        actual_delay = max(0.0, min(requested_delay, MAX_GLOBAL_DELAY_SECONDS))
        if actual_delay > 0:
            time.sleep(actual_delay)
    elif not request.path.startswith('/simulate/'):
        # Latencia base por defecto solo para rutas normales (no simulación)
        if DEFAULT_GLOBAL_DELAY_SECONDS > 0:
            time.sleep(DEFAULT_GLOBAL_DELAY_SECONDS)

    # 2. Procesamiento de JSON
    g.json_data = None
    if request.is_json:
        g.json_data = request.get_json(silent=True)

@api.route('/', methods=['GET'])
def list_resources():
    """
    Devuelve una lista de todos los recursos (colecciones) creados.

    ---
    tags:
        - 1. Gestión de Recursos
    responses:
        200:
            description: Lista de nombres de recursos
            schema:
                type: array
                items:
                    type: string
    """
    # Obtener nombres de recursos únicos desde la base de datos
    resource_names = [r[0] for r in db.session.query(Item.resource_name).distinct().all()]
    return jsonify(resource_names)

@api.route('/<resource_name>', methods=['PUT'])
def rename_resource(resource_name):
    """
    Renombra una colección completa de recursos.
    Actualiza el identificador del recurso para todos los items asociados.
    ---
    tags:
        - 1. Gestión de Recursos
    parameters:
        - in: path
          name: resource_name
          required: true
          type: string
          description: Nombre actual del recurso.
        - in: body
          name: body
          required: true
          schema:
            type: object
            properties:
                new_name:
                    type: string
                    example: "nuevos_productos"
    responses:
        200:
            description: Recurso renombrado exitosamente.
        400:
            description: Falta el nuevo nombre en el cuerpo.
        404:
            description: Recurso no encontrado.
    """
    if not g.json_data or 'new_name' not in g.json_data:
        abort(400, description="Se requiere un JSON con el campo 'new_name'.")
    
    new_name = g.json_data['new_name']
    
    updated_count = Item.query.filter_by(resource_name=resource_name).update({Item.resource_name: new_name})
    db.session.commit()
    
    if updated_count == 0:
        abort(404, description=f"Resource '{resource_name}' not found")
        
    return jsonify({"message": f"Resource renamed from '{resource_name}' to '{new_name}'", "count": updated_count})

@api.route('/<resource_name>', methods=['DELETE'])
def delete_resource(resource_name):
    """
    Elimina una colección completa y todos sus items.
    ¡Esta acción es irreversible!
    ---
    tags:
        - 1. Gestión de Recursos
    parameters:
        - in: path
          name: resource_name
          required: true
          type: string
          description: Nombre del recurso (colección) a eliminar.
    responses:
        204:
            description: Recurso y todos sus items eliminados exitosamente.
    """
    # The delete() method performs a bulk delete without loading objects into memory.
    Item.query.filter_by(resource_name=resource_name).delete()
    db.session.commit()
    # A 204 No Content response is appropriate for a successful DELETE.
    return jsonify({}), 204

# ================= CRUD Dinámico =================

@api.route('/<resource_name>', methods=['POST'])
def create_item(resource_name):
    """
    Crea un nuevo item en la colección indicada.

    ---
    tags:
        - 2. Gestión de Items (CRUD)
    parameters:
        - in: path
          name: resource_name
          required: true
          type: string
          description: Nombre del recurso (colección)
        - in: body
          name: body
          required: true
          schema:
            type: object
          example:
            name: "Producto de ejemplo"
            price: 19.99
            stock: 100
    responses:
        201:
            description: Item creado con su ID
            schema:
                type: object
            examples:
              application/json:
                _id: 1
                name: "Producto de ejemplo"
                price: 19.99
                stock: 100
        400:
            description: Bad Request. El cuerpo de la petición no es un JSON válido o está vacío.
            schema:
                type: object
                properties:
                    error:
                        type: string
                        example: "Se esperaba un cuerpo JSON."
    """
    if not g.json_data:
        abort(400, description="Se esperaba un cuerpo JSON.")
    
    new_item = Item(resource_name=resource_name, data=g.json_data)
    db.session.add(new_item)
    db.session.commit()
    
    return jsonify(new_item.to_dict()), 201

@api.route('/<resource_name>', methods=['GET'])
def get_items(resource_name):
    """
    Obtiene items de una colección con paginación y filtros avanzados.

    ---
    tags:
        - 2. Gestión de Items (CRUD)
    parameters:
        - in: path
          name: resource_name
          required: true
          type: string
        - in: query
          name: page
          type: integer
          required: false
          description: Número de página (default 1)
        - in: query
          name: limit
          type: integer
          required: false
          description: Items por página (default 20)
        - in: query
          name: (filtro_dinamico)
          type: string
          required: false
          description: >
            Filtra por campos en el JSON. Usa sufijos para comparaciones avanzadas:
            - `?campo=valor` (coincidencia exacta)
            - `?campo__ilike=valor` (contiene el texto, sin distinción de mayúsculas/minúsculas)
            - `?campo__gt=10` (mayor que)
            - `?campo__gte=10` (mayor o igual que)
            - `?campo__lt=10` (menor que)
            - `?campo__lte=10` (menor o igual que)
    responses:
        200:
            description: Lista paginada de items
            schema:
                type: object
            examples:
              application/json:
                data:
                  - _id: 1
                    name: "Producto 1"
                    price: 25.50
                  - _id: 2
                    name: "Producto 2"
                    price: 30.00
                meta:
                  total_items: 2
                  per_page: 20
                  current_page: 1
                  total_pages: 1
        400:
            description: Bad Request. Los parámetros 'page' o 'limit' no son números enteros válidos.
            schema:
                type: object
                properties:
                    error:
                        type: string
                        example: "Los parámetros 'page' y 'limit' deben ser números enteros."
    """
    # Leer parámetros de paginación de la URL
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        if page < 1 or limit < 1:
            raise ValueError()
    except (ValueError, TypeError):
        abort(400, description="Los parámetros 'page' y 'limit' deben ser números enteros positivos.")

    # Construir la consulta base
    query = Item.query.filter_by(resource_name=resource_name)

    # Aplicar filtros dinámicos basados en los parámetros de la URL
    reserved_params = ['page', 'limit']
    for key, value in request.args.items():
        if key in reserved_params:
            continue

        # Separar el nombre del campo y el operador (ej. 'precio__gt')
        parts = key.split('__')
        field_name = parts[0]
        op = parts[1] if len(parts) > 1 else 'eq'

        # Obtener el campo JSON como texto para poder operar sobre él
        json_field_as_text = Item.data.op('->>')(field_name)

        if op == 'eq':
            query = query.filter(json_field_as_text == value)
        elif op == 'ilike':
            # Búsqueda de texto parcial, insensible a mayúsculas/minúsculas
            query = query.filter(json_field_as_text.ilike(f'%{value}%'))
        elif op in ['gt', 'gte', 'lt', 'lte']:
            try:
                # Para comparaciones numéricas, debemos convertir el campo y el valor
                numeric_value = float(value)
                json_field_as_numeric = db.cast(json_field_as_text, db.Float)

                if op == 'gt':
                    query = query.filter(json_field_as_numeric > numeric_value)
                elif op == 'gte':
                    query = query.filter(json_field_as_numeric >= numeric_value)
                elif op == 'lt':
                    query = query.filter(json_field_as_numeric < numeric_value)
                elif op == 'lte':
                    query = query.filter(json_field_as_numeric <= numeric_value)
            except (ValueError, TypeError):
                # Si el valor no es un número, ignoramos este filtro para evitar un error.
                pass

    pagination = query.paginate(
        page=page, per_page=limit, error_out=False
    )
    
    paginated_items = [item.to_dict() for item in pagination.items]

    response = {
        "data": paginated_items,
        "meta": {
            "total_items": pagination.total,
            "per_page": pagination.per_page,
            "current_page": pagination.page,
            "total_pages": pagination.pages
        }
    }
    
    return jsonify(response)

@api.route('/<resource_name>/<int:item_id>', methods=['GET'])
def get_item(resource_name, item_id):
    """
    Obtiene un item por su ID.

    ---
    tags:
        - 2. Gestión de Items (CRUD)
    parameters:
        - in: path
          name: resource_name
          required: true
          type: string
        - in: path
          name: item_id
          required: true
          type: integer
    responses:
        200:
            description: Item encontrado
            schema:
                type: object
            examples:
              application/json:
                _id: 1
                name: "Producto de ejemplo"
                price: 19.99
                stock: 100
        404:
            description: Item no encontrado
    """
    item = Item.query.filter_by(resource_name=resource_name, id=item_id).first()
    if item:
        return jsonify(item.to_dict())
    abort(404, description=f"Item with id {item_id} not found in resource '{resource_name}'")

@api.route('/<resource_name>/<int:item_id>', methods=['PUT'])
def update_item(resource_name, item_id):
    """
    Reemplaza un item existente (PUT).

    ---
    tags:
        - 2. Gestión de Items (CRUD)
    parameters:
        - in: path
          name: resource_name
          required: true
          type: string
        - in: path
          name: item_id
          required: true
          type: integer
        - in: body
          name: body
          required: true
          schema:
            type: object
          example:
            name: "Producto actualizado"
            price: 25.99
            stock: 50
    responses:
        200:
            description: Item actualizado exitosamente. Devuelve el objeto completo.
            schema:
                type: object
            examples:
              application/json:
                _id: 1
                name: "Producto actualizado"
                price: 25.99
                stock: 50
        404:
            description: Item no encontrado
        400:
            description: Bad Request. El cuerpo de la petición no es un JSON válido o está vacío.
            schema:
                type: object
                properties:
                    error:
                        type: string
                        example: "Se esperaba un cuerpo JSON."
    """
    if not g.json_data:
        abort(400, description="Se esperaba un cuerpo JSON.")
    
    item = Item.query.filter_by(resource_name=resource_name, id=item_id).first()
    if item:
        item.data = g.json_data
        db.session.commit()
        return jsonify(item.to_dict())
    abort(404, description=f"Item with id {item_id} not found in resource '{resource_name}'")

@api.route('/<resource_name>/<int:item_id>', methods=['PATCH'])
def patch_item(resource_name, item_id):
    """
    Actualiza parcialmente un item (PATCH).

    ---
    tags:
        - 2. Gestión de Items (CRUD)
    parameters:
        - in: path
          name: resource_name
          required: true
          type: string
        - in: path
          name: item_id
          required: true
          type: integer
        - in: body
          name: body
          required: true
          schema:
            type: object
          example:
            price: 22.50
    responses:
        200:
            description: Item actualizado parcialmente. Devuelve el objeto completo.
            schema:
                type: object
            examples:
              application/json:
                _id: 1
                name: "Producto de ejemplo"
                price: 22.50
                stock: 100
        404:
            description: Item no encontrado
        400:
            description: Bad Request. El cuerpo de la petición no es un JSON válido o está vacío.
            schema:
                type: object
                properties:
                    error:
                        type: string
                        example: "Se esperaba un cuerpo JSON."
    """
    if not g.json_data:
        abort(400, description="Se esperaba un cuerpo JSON.")
    
    item = Item.query.filter_by(resource_name=resource_name, id=item_id).first()
    if item:
        new_data = item.data.copy()
        new_data.update(g.json_data)
        # Forzamos a SQLAlchemy a detectar el cambio en el campo JSON
        from sqlalchemy.orm.attributes import flag_modified
        item.data = new_data
        flag_modified(item, "data")
        db.session.commit()
        return jsonify(item.to_dict())
    abort(404, description=f"Item with id {item_id} not found in resource '{resource_name}'")

@api.route('/<resource_name>/<int:item_id>', methods=['DELETE'])
def delete_item(resource_name, item_id):
    """
    Elimina un item por su ID.

    ---
    tags:
        - 2. Gestión de Items (CRUD)
    parameters:
        - in: path
          name: resource_name
          required: true
          type: string
        - in: path
          name: item_id
          required: true
          type: integer
    responses:
        204:
            description: Item eliminado (No Content)
        404:
            description: Item no encontrado
    """
    item = Item.query.filter_by(resource_name=resource_name, id=item_id).first()
    if item:
        db.session.delete(item)
        db.session.commit()
        return jsonify({}), 204
    abort(404, description=f"Item with id {item_id} not found in resource '{resource_name}'")

# ================= Testing & Simulation =================

@api.route('/simulate/error/<int:status_code>', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
def simulate_error(status_code):
    """
    Simula una respuesta de error HTTP.
    Este endpoint permite probar cómo una aplicación cliente reacciona a diferentes códigos de error HTTP.
    ---
    tags:
        - 3. Simulación y Pruebas
    parameters:
        - in: path
          name: status_code
          required: true
          type: integer
          description: El código de estado HTTP a simular (ej. 404, 500, 401).
    responses:
        '4xx':
            description: Respuesta de error del cliente simulada.
        '5xx':
            description: Respuesta de error del servidor simulada.
    """
    error_messages = {
        400: "Bad Request", 401: "Unauthorized", 403: "Forbidden", 404: "Not Found",
        410: "Gone", 415: "Unsupported Media Type", 422: "Unprocessable Entity", 500: "Internal Server Error",
        502: "Bad Gateway", 503: "Service Unavailable", 504: "Gateway Timeout"
    }
    description = error_messages.get(status_code, f"Simulated Error {status_code}")
    abort(status_code, description=description)

@api.route('/simulate/timeout/<float:duration>', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
def simulate_timeout(duration):
    """
    Simula un timeout en la respuesta del servidor.
    Este endpoint bloquea la ejecución durante un número de segundos y luego devuelve un error 504 Gateway Timeout.
    ---
    tags:
        - 3. Simulación y Pruebas
    parameters:
        - in: path
          name: duration
          required: true
          type: number
          description: El número de segundos que la petición debe esperar antes de fallar.
    responses:
        504:
            description: Gateway Timeout. La petición esperó el tiempo especificado.
            schema:
                type: object
                properties:
                    error:
                        type: string
                        example: "Gateway Timeout: La petición tardó 5 segundos."
    """
    if duration < 0:
        abort(400, description="La duración del timeout debe ser un número no negativo.")
    
    actual_duration = min(duration, MAX_GLOBAL_DELAY_SECONDS)
    time.sleep(actual_duration)
    
    return jsonify({"error": f"Gateway Timeout: La petición tardó {actual_duration:.2f} segundos."}), 504

@api.route('/simulate/delay/<float:duration>', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
def simulate_delay(duration):
    """
    Simula un retraso exitoso (latencia) en la respuesta.
    ---
    tags:
        - 3. Simulación y Pruebas
    parameters:
        - in: path
          name: duration
          required: true
          type: number
          description: Segundos de retraso.
    responses:
        200:
            description: Respuesta exitosa tras el retraso.
            schema:
                type: object
                properties:
                    message:
                        type: string
                        example: "Respuesta completada tras 3.00 segundos."
    """
    if duration < 0:
        abort(400, description="La duración debe ser un número no negativo.")
    
    actual_duration = min(duration, MAX_GLOBAL_DELAY_SECONDS)
    time.sleep(actual_duration)
    return jsonify({
        "message": f"Respuesta completada tras {actual_duration:.2f} segundos.",
        "status": "success"
    })
