from flask import Blueprint, request, jsonify, abort, g
import time
import math

api = Blueprint('api', __name__)

# Base de datos en memoria para múltiples recursos.
# La estructura será: {'nombre_recurso': {'items': {1: data}, 'next_id': 2}}
database = {}

@api.before_request
def preprocess_json_body():
    """
    Se ejecuta antes de cada petición para pre-procesar el cuerpo JSON si existe.
    """
    g.json_data = None
    if request.is_json:
        g.json_data = request.get_json()

@api.route('/', methods=['GET'])
def list_resources():
    """
    Devuelve una lista de todos los recursos (colecciones) creados.

    ---
    tags:
        - resources
    responses:
        200:
            description: Lista de nombres de recursos
            schema:
                type: array
                items:
                    type: string
    """
    resource_names = list(database.keys())
    return jsonify(resource_names)

# ================= CRUD Dinámico =================

def get_resource(resource_name):
    """Función auxiliar para obtener o inicializar una colección de recursos."""
    if resource_name not in database:
        database[resource_name] = {'items': {}, 'next_id': 1}
    return database[resource_name]

@api.route('/<resource_name>', methods=['POST'])
def create_item(resource_name):
    """
    Crea un nuevo item en la colección indicada.

    ---
    tags:
        - items
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
    resource = get_resource(resource_name)
    if not g.json_data:
        abort(400, description="Se esperaba un cuerpo JSON.")
    
    item_id = resource['next_id']
    data = g.json_data
    resource['items'][item_id] = data
    resource['next_id'] += 1
    
    # En lugar de 'data', el estándar RESTful devuelve el objeto creado con su ID.
    response = data.copy()
    response['_id'] = item_id
    
    return jsonify(response), 201

@api.route('/<resource_name>', methods=['GET'])
def get_items(resource_name):
    """
    Obtiene items de una colección con paginación.

    ---
    tags:
        - items
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
    resource = get_resource(resource_name)

    # Leer parámetros de paginación de la URL
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
    except (ValueError, TypeError):
        abort(400, description="Los parámetros 'page' y 'limit' deben ser números enteros.")

    all_items = []
    for item_id, data in resource['items'].items():
        item = data.copy()
        item['_id'] = item_id
        all_items.append(item)
    
    total_items = len(all_items)
    total_pages = math.ceil(total_items / limit)
    
    # Calcular los índices para la página actual
    start_index = (page - 1) * limit
    end_index = start_index + limit
    
    paginated_items = all_items[start_index:end_index]
    
    response = {
        "data": paginated_items,
        "meta": {
            "total_items": total_items,
            "per_page": limit,
            "current_page": page,
            "total_pages": total_pages
        }
    }
    
    return jsonify(response)

@api.route('/<resource_name>/<int:item_id>', methods=['GET'])
def get_item(resource_name, item_id):
    """
    Obtiene un item por su ID.

    ---
    tags:
        - items
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
    resource = get_resource(resource_name)
    if item_id in resource['items']:
        item = resource['items'][item_id].copy()
        item['_id'] = item_id
        return jsonify(item)
    abort(404, description=f"Item with id {item_id} not found in resource '{resource_name}'")

@api.route('/<resource_name>/<int:item_id>', methods=['PUT'])
def update_item(resource_name, item_id):
    """
    Reemplaza un item existente (PUT).

    ---
    tags:
        - items
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
    resource = get_resource(resource_name)
    if not g.json_data:
        abort(400, description="Se esperaba un cuerpo JSON.")
    if item_id in resource['items']:
        # PUT reemplaza el objeto completo
        resource['items'][item_id] = g.json_data
        # Devolver el recurso actualizado
        response = resource['items'][item_id].copy()
        response['_id'] = item_id
        return jsonify(response)
    abort(404, description=f"Item with id {item_id} not found in resource '{resource_name}'")

@api.route('/<resource_name>/<int:item_id>', methods=['PATCH'])
def patch_item(resource_name, item_id):
    """
    Actualiza parcialmente un item (PATCH).

    ---
    tags:
        - items
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
    resource = get_resource(resource_name)
    if not g.json_data:
        abort(400, description="Se esperaba un cuerpo JSON.")
    if item_id in resource['items']:
        resource['items'][item_id].update(g.json_data)
        # Devolver el recurso actualizado
        response = resource['items'][item_id].copy()
        response['_id'] = item_id
        return jsonify(response)
    abort(404, description=f"Item with id {item_id} not found in resource '{resource_name}'")

@api.route('/<resource_name>/<int:item_id>', methods=['DELETE'])
def delete_item(resource_name, item_id):
    """
    Elimina un item por su ID.

    ---
    tags:
        - items
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
    resource = get_resource(resource_name)
    if item_id in resource['items']:
        del resource['items'][item_id]
        return jsonify({}), 204 # 204 No Content es común para DELETE
    abort(404, description=f"Item with id {item_id} not found in resource '{resource_name}'")

# ================= Testing & Simulation =================

@api.route('/simulate/error/<int:status_code>', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
def simulate_error(status_code):
    """
    Simula una respuesta de error HTTP.
    Este endpoint permite probar cómo una aplicación cliente reacciona a diferentes códigos de error HTTP.
    ---
    tags:
        - Testing & Simulation
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

@api.route('/simulate/timeout/<int:duration>', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
def simulate_timeout(duration):
    """
    Simula un timeout en la respuesta del servidor.
    Este endpoint bloquea la ejecución durante un número de segundos y luego devuelve un error 504 Gateway Timeout.
    ---
    tags:
        - Testing & Simulation
    parameters:
        - in: path
          name: duration
          required: true
          type: integer
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
    time.sleep(duration)
    abort(504, description=f"Gateway Timeout: La petición tardó {duration} segundos.")
