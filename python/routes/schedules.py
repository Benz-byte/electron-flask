from flask import Blueprint, jsonify
import database as db

schedules_bp = Blueprint('schedules', __name__)


@schedules_bp.route('/', methods=['GET'])
def get_schedules():
    return jsonify(db.get_all_schedules())


@schedules_bp.route('/', methods=['DELETE'])
def clear_schedules():
    db.clear_schedules()
    return jsonify({'message': 'All schedules cleared'}), 200
