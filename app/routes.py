from flask import Blueprint, request, jsonify, abort, g
import time
import math

api = Blueprint('api', __name__)

# Base de datos en memoria para múltiples recursos.
# La estructura será: {'nombre_recurso': {'items': {1: data}, 'next_id': 2}}
database = {}

@api.errorhandler(ValueError)
def handle_value_error(e):
    """Captura errores de conversión de tipo, como int('texto')."""
    return jsonify(error="Parámetro 'error' inválido. Debe ser un número."), 400

@api.before_request
def process_request_hooks():
    """
    Se ejecuta antes de cada petición. Maneja la simulación de errores
    y pre-procesa el cuerpo JSON si existe.
    """
    # 1. Simular errores numéricos desde el parámetro URL
    error_code = request.args.get('error')
    if error_code:
        status_code = int(error_code) # Lanza ValueError si no es un número, capturado por el errorhandler
        error_messages = {
            400: "Bad Request", 401: "Unauthorized", 403: "Forbidden", 404: "Not Found", 
            410: "Gone", 415: "Unsupported Media Type", 422: "Unprocessable Entity", 500: "Internal Server Error",
            502: "Bad Gateway", 503: "Service Unavailable", 504: "Gateway Timeout"
        }
        description = error_messages.get(status_code, "Unknown Error")
        abort(status_code, description=description)

    # 2. Pre-procesar el cuerpo JSON y manejar el timeout activado por JSON
    g.json_data = None
    if request.is_json:
        g.json_data = request.get_json()

        # Para POST/PUT, si la descripción es "timeout", simularlo y quitar la clave de control
        if request.method in ['POST', 'PUT'] and g.json_data.get('description') == 'timeout':
            control_data = g.json_data.pop('control', None) # Extrae y elimina la clave 'control' del JSON

            if control_data and 'timeout' in control_data:
                try:
                    timeout_duration = int(control_data['timeout'])
                    time.sleep(timeout_duration)
                    abort(504, description=f"Gateway Timeout: La petición tardó {timeout_duration} segundos.")
                except (ValueError, TypeError):
                    abort(400, description="El valor de 'timeout' en la clave 'control' debe ser un número entero.")

@api.route('/', methods=['GET'])
def list_resources():
    """Devuelve una lista de todos los recursos (colecciones) creados."""
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
    resource = get_resource(resource_name)
    if item_id in resource['items']:
        item = resource['items'][item_id].copy()
        item['_id'] = item_id
        return jsonify(item)
    abort(404, description=f"Item with id {item_id} not found in resource '{resource_name}'")

@api.route('/<resource_name>/<int:item_id>', methods=['PUT'])
def update_item(resource_name, item_id):
    resource = get_resource(resource_name)
    if not g.json_data:
        abort(400, description="Se esperaba un cuerpo JSON.")
    if item_id in resource['items']:
        resource['items'][item_id] = g.json_data # PUT reemplaza el objeto completo
        return jsonify({'message': f"Item {item_id} updated successfully."})
    abort(404, description=f"Item with id {item_id} not found in resource '{resource_name}'")

@api.route('/<resource_name>/<int:item_id>', methods=['PATCH'])
def patch_item(resource_name, item_id):
    resource = get_resource(resource_name)
    if not g.json_data:
        abort(400, description="Se esperaba un cuerpo JSON.")
    if item_id in resource['items']:
        resource['items'][item_id].update(g.json_data)
        return jsonify({'message': f"Item {item_id} partially updated successfully."})
    abort(404, description=f"Item with id {item_id} not found in resource '{resource_name}'")

@api.route('/<resource_name>/<int:item_id>', methods=['DELETE'])
def delete_item(resource_name, item_id):
    resource = get_resource(resource_name)
    if item_id in resource['items']:
        del resource['items'][item_id]
        return jsonify({}), 204 # 204 No Content es común para DELETE
    abort(404, description=f"Item with id {item_id} not found in resource '{resource_name}'")
