from flask import Blueprint, jsonify, request
import database as db

subjects_bp = Blueprint('subjects', __name__)


@subjects_bp.route('/', methods=['GET'])
def get_subjects():
    return jsonify(db.get_all_subjects())


@subjects_bp.route('/', methods=['POST'])
def create_subject():
    data = request.get_json()
    row = db.create_subject(
        data['code'],
        data['name'],
        data['hours_per_week'],
        data.get('type', 'lecture'),
        data.get('preferred_time') or None,
        data.get('students', 30),
    )
    return jsonify(row), 201


@subjects_bp.route('/<int:subject_id>', methods=['DELETE'])
def delete_subject(subject_id):
    db.delete_subject(subject_id)
    return jsonify({'message': 'Subject deleted'}), 200
