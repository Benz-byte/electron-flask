from flask import Blueprint, jsonify
import database as db
from solver.cpsat_solver import run_cpsat_solver

solver_bp = Blueprint('solver', __name__)

_solver_state = {'state': 'idle', 'message': 'Solver is ready'}


@solver_bp.route('/run', methods=['POST'])
def run_solver():
    global _solver_state
    _solver_state = {'state': 'running', 'message': 'Solver is running...'}
    try:
        result = run_cpsat_solver(
            db.get_all_subjects(),
            db.get_all_rooms(),
            db.get_all_instructors(),
            db.get_all_instructor_subjects(),
            db.get_all_timeslots(),
            db.get_instructor_availability(),
            db.get_preferred_time_slots(),
        )

        if result['status'] == 'success':
            db.save_schedule(result['assignments'])

        _solver_state = {'state': 'done', 'message': result.get('message', 'Done')}
        return jsonify(result)

    except Exception as error:
        _solver_state = {'state': 'idle', 'message': 'Solver encountered an error'}
        return jsonify({'status': 'error', 'message': str(error), 'assignments': []})


@solver_bp.route('/status', methods=['GET'])
def solver_status():
    return jsonify(_solver_state)
