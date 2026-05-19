import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, jsonify
from flask_cors import CORS
from database import init_db
import database as db
from routes.subjects import subjects_bp
from routes.rooms import rooms_bp
from routes.instructors import instructors_bp
from routes.schedules import schedules_bp
from routes.solver import solver_bp

app = Flask(__name__)
CORS(app)

app.register_blueprint(subjects_bp, url_prefix='/api/subjects')
app.register_blueprint(rooms_bp, url_prefix='/api/rooms')
app.register_blueprint(instructors_bp, url_prefix='/api/instructors')
app.register_blueprint(schedules_bp, url_prefix='/api/schedules')
app.register_blueprint(solver_bp, url_prefix='/api/solver')


@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'message': 'Auto Scheduler API is running'})


@app.route('/api/timeslots/')
def get_timeslots():
    return jsonify(db.get_distinct_timeslots())


if __name__ == '__main__':
    init_db()
    app.run(port=5000, debug=False, use_reloader=False)
