from flask import Blueprint, request, jsonify
import time

api = Blueprint('api', __name__)

# Base de datos en memoria
database = {}
id_counter = 1

# Función para simular errores
def simulate_error():
    error = request.args.get('error')
    if error:
        if error == '400': return jsonify({'error':'400 Bad Request'}),400
        if error == '401': return jsonify({'error':'401 Unauthorized'}),401
        if error == '403': return jsonify({'error':'403 Forbidden'}),403
        if error == '404': return jsonify({'error':'404 Not Found'}),404
        if error == '422': return jsonify({'error':'422 Unprocessable Entity'}),422
        if error == '500': return jsonify({'error':'500 Internal Server Error'}),500
        if error == '502': return jsonify({'error':'502 Bad Gateway'}),502
        if error == '503': return jsonify({'error':'503 Service Unavailable'}),503
        if error == '504': return jsonify({'error':'504 Gateway Timeout'}),504
        if error == 'timeout': 
            time.sleep(20)
            return jsonify({'error':'Timeout: Request took too long'}),504
    return None

# ================= CRUD =================

@api.route('/items', methods=['POST'])
def create_item():
    global id_counter
    err = simulate_error()
    if err: return err
    data = request.json
    database[id_counter] = data
    response = {'id': id_counter, 'data': data}
    id_counter += 1
    return jsonify(response), 201

@api.route('/items', methods=['GET'])
def get_items():
    err = simulate_error()
    if err: return err
    return jsonify(database)

@api.route('/items/<int:item_id>', methods=['GET'])
def get_item(item_id):
    err = simulate_error()
    if err: return err
    if item_id in database:
        return jsonify({'id': item_id, 'data': database[item_id]})
    return jsonify({'error':'Item not found'}),404

@api.route('/items/<int:item_id>', methods=['PUT'])
def update_item(item_id):
    err = simulate_error()
    if err: return err
    if item_id in database:
        database[item_id] = request.json
        return jsonify({'id': item_id, 'data': database[item_id]})
    return jsonify({'error':'Item not found'}),404

@api.route('/items/<int:item_id>', methods=['DELETE'])
def delete_item(item_id):
    err = simulate_error()
    if err: return err
    if item_id in database:
        del database[item_id]
        return jsonify({'message':'Item deleted','id':item_id})
    return jsonify({'error':'Item not found'}),404
