from flask import Blueprint, jsonify, request
import database as db

instructors_bp = Blueprint('instructors', __name__)


@instructors_bp.route('/', methods=['GET'])
def get_instructors():
    return jsonify(db.get_all_instructors())


@instructors_bp.route('/', methods=['POST'])
def create_instructor():
    data = request.get_json()
    row = db.create_instructor(
        data['name'],
        data.get('email', ''),
        data.get('department', ''),
        data.get('preferred_time') or None,
    )
    return jsonify(row), 201


@instructors_bp.route('/<int:instructor_id>', methods=['DELETE'])
def delete_instructor(instructor_id):
    db.delete_instructor(instructor_id)
    return jsonify({'message': 'Instructor deleted'}), 200


# ── Subject assignment routes ─────────────────────────────────────────────────

@instructors_bp.route('/<int:instructor_id>/subjects', methods=['GET'])
def get_instructor_subjects(instructor_id):
    return jsonify(db.get_instructor_subjects(instructor_id))


@instructors_bp.route('/<int:instructor_id>/subjects', methods=['POST'])
def assign_subject_to_instructor(instructor_id):
    data = request.get_json()
    subject_id = data.get('subject_id')
    if not subject_id:
        return jsonify({'error': 'subject_id is required'}), 400
    try:
        db.assign_subject(instructor_id, subject_id, data.get('preferred_time') or None)
    except Exception:
        return jsonify({'error': 'Subject is already assigned to this instructor'}), 409
    return jsonify({'message': 'Subject assigned'}), 201


@instructors_bp.route('/<int:instructor_id>/subjects/<int:subject_id>', methods=['DELETE'])
def remove_subject_from_instructor(instructor_id, subject_id):
    db.remove_instructor_subject(instructor_id, subject_id)
    return jsonify({'message': 'Assignment removed'}), 200
