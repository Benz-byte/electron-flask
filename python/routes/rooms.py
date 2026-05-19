from flask import Blueprint, jsonify, request
import database as db

rooms_bp = Blueprint('rooms', __name__)


@rooms_bp.route('/', methods=['GET'])
def get_rooms():
    return jsonify(db.get_all_rooms())


@rooms_bp.route('/', methods=['POST'])
def create_room():
    data = request.get_json()
    row = db.create_room(data['name'], data['capacity'], data.get('type', 'lecture'))
    return jsonify(row), 201


@rooms_bp.route('/<int:room_id>', methods=['DELETE'])
def delete_room(room_id):
    db.delete_room(room_id)
    return jsonify({'message': 'Room deleted'}), 200
