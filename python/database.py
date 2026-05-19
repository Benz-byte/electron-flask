import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'scheduler.db')


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def init_db() -> None:
    conn = get_db()
    cursor = conn.cursor()

    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS subjects (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            code            TEXT    NOT NULL UNIQUE,
            name            TEXT    NOT NULL,
            hours_per_week  INTEGER NOT NULL DEFAULT 3,
            type            TEXT    NOT NULL DEFAULT 'lecture',
            preferred_time  TEXT
        );

        CREATE TABLE IF NOT EXISTS rooms (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT    NOT NULL UNIQUE,
            capacity INTEGER NOT NULL DEFAULT 40,
            type     TEXT    NOT NULL DEFAULT 'lecture'
        );

        CREATE TABLE IF NOT EXISTS instructors (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            name           TEXT NOT NULL,
            email          TEXT UNIQUE,
            department     TEXT,
            preferred_time TEXT
        );

        CREATE TABLE IF NOT EXISTS timeslots (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            day        TEXT    NOT NULL,
            start_time TEXT    NOT NULL,
            end_time   TEXT    NOT NULL,
            duration   INTEGER NOT NULL DEFAULT 30
        );

        CREATE TABLE IF NOT EXISTS instructor_subjects (
            instructor_id  INTEGER NOT NULL,
            subject_id     INTEGER NOT NULL,
            preferred_time TEXT,
            PRIMARY KEY (instructor_id, subject_id),
            FOREIGN KEY (instructor_id) REFERENCES instructors(id) ON DELETE CASCADE,
            FOREIGN KEY (subject_id)    REFERENCES subjects(id)    ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS schedules (
            id            INTEGER   PRIMARY KEY AUTOINCREMENT,
            subject_id    INTEGER   NOT NULL,
            room_id       INTEGER   NOT NULL,
            instructor_id INTEGER   NOT NULL,
            timeslot_id   INTEGER   NOT NULL,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (subject_id)    REFERENCES subjects(id),
            FOREIGN KEY (room_id)       REFERENCES rooms(id),
            FOREIGN KEY (instructor_id) REFERENCES instructors(id),
            FOREIGN KEY (timeslot_id)   REFERENCES timeslots(id)
        );
    ''')

    # One-time migration: remove units column from subjects if present.
    subj_cols = [row[1] for row in cursor.execute('PRAGMA table_info(subjects)').fetchall()]
    if 'units' in subj_cols:
        cursor.executescript('''
            PRAGMA foreign_keys = OFF;
            DROP TABLE IF EXISTS subjects_new;
            CREATE TABLE subjects_new (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                code            TEXT    NOT NULL UNIQUE,
                name            TEXT    NOT NULL,
                hours_per_week  INTEGER NOT NULL DEFAULT 3,
                type            TEXT    NOT NULL DEFAULT 'lecture',
                preferred_time  TEXT
            );
            INSERT INTO subjects_new (id, code, name, hours_per_week, type)
                SELECT id, code, name, hours_per_week, type FROM subjects;
            DROP TABLE subjects;
            ALTER TABLE subjects_new RENAME TO subjects;
            PRAGMA foreign_keys = ON;
        ''')

    # One-time migration: remove section_id from schedules if present.
    sched_cols = [row[1] for row in cursor.execute('PRAGMA table_info(schedules)').fetchall()]
    if 'section_id' in sched_cols:
        cursor.executescript('''
            DROP TABLE IF EXISTS schedules;
            CREATE TABLE schedules (
                id            INTEGER   PRIMARY KEY AUTOINCREMENT,
                subject_id    INTEGER   NOT NULL,
                room_id       INTEGER   NOT NULL,
                instructor_id INTEGER   NOT NULL,
                timeslot_id   INTEGER   NOT NULL,
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (subject_id)    REFERENCES subjects(id),
                FOREIGN KEY (room_id)       REFERENCES rooms(id),
                FOREIGN KEY (instructor_id) REFERENCES instructors(id),
                FOREIGN KEY (timeslot_id)   REFERENCES timeslots(id)
            );
        ''')

    # Migration: add preferred_time to existing tables if the column is missing.
    instr_cols = [row[1] for row in cursor.execute('PRAGMA table_info(instructors)').fetchall()]
    if 'preferred_time' not in instr_cols:
        cursor.execute('ALTER TABLE instructors ADD COLUMN preferred_time TEXT')

    subj_cols = [row[1] for row in cursor.execute('PRAGMA table_info(subjects)').fetchall()]
    if 'preferred_time' not in subj_cols:
        cursor.execute('ALTER TABLE subjects ADD COLUMN preferred_time TEXT')

    is_cols = [row[1] for row in cursor.execute('PRAGMA table_info(instructor_subjects)').fetchall()]
    if 'preferred_time' not in is_cols:
        cursor.execute('ALTER TABLE instructor_subjects ADD COLUMN preferred_time TEXT')

    # Seed 30-minute timeslots (07:00–21:00, including lunch, no gaps).
    # Migrate automatically if old 60-minute slots are detected.
    def seed_30min_timeslots():
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        for day in days:
            for start_min in range(7 * 60, 21 * 60, 30):
                h1, m1 = start_min // 60, start_min % 60
                h2, m2 = (start_min + 30) // 60, (start_min + 30) % 60
                cursor.execute(
                    'INSERT INTO timeslots (day, start_time, end_time, duration) VALUES (?, ?, ?, ?)',
                    (day, f'{h1:02d}:{m1:02d}', f'{h2:02d}:{m2:02d}', 30),
                )

    cursor.execute('SELECT COUNT(*) FROM timeslots')
    timeslot_count = cursor.fetchone()[0]

    if timeslot_count == 0:
        seed_30min_timeslots()
    else:
        first_duration = cursor.execute('SELECT duration FROM timeslots LIMIT 1').fetchone()[0]
        if first_duration != 30:
            cursor.execute('DELETE FROM schedules')
            cursor.execute('DELETE FROM timeslots')
            seed_30min_timeslots()

    conn.commit()
    conn.close()


# ── Subjects ──────────────────────────────────────────────────────────────────

def get_all_subjects():
    conn = get_db()
    rows = conn.execute('SELECT * FROM subjects ORDER BY code').fetchall()
    conn.close()
    return [dict(row) for row in rows]


def create_subject(code, name, hours_per_week, type, preferred_time=None):
    conn = get_db()
    cursor = conn.execute(
        'INSERT INTO subjects (code, name, hours_per_week, type, preferred_time) VALUES (?, ?, ?, ?, ?)',
        (code, name, hours_per_week, type, preferred_time or None),
    )
    conn.commit()
    row = conn.execute('SELECT * FROM subjects WHERE id = ?', (cursor.lastrowid,)).fetchone()
    conn.close()
    return dict(row)


def delete_subject(subject_id):
    conn = get_db()
    conn.execute('DELETE FROM schedules WHERE subject_id = ?', (subject_id,))
    conn.execute('DELETE FROM subjects WHERE id = ?', (subject_id,))
    conn.commit()
    conn.close()


# ── Rooms ─────────────────────────────────────────────────────────────────────

def get_all_rooms():
    conn = get_db()
    rows = conn.execute('SELECT * FROM rooms ORDER BY name').fetchall()
    conn.close()
    return [dict(row) for row in rows]


def create_room(name, capacity, type):
    conn = get_db()
    cursor = conn.execute(
        'INSERT INTO rooms (name, capacity, type) VALUES (?, ?, ?)',
        (name, capacity, type),
    )
    conn.commit()
    row = conn.execute('SELECT * FROM rooms WHERE id = ?', (cursor.lastrowid,)).fetchone()
    conn.close()
    return dict(row)


def delete_room(room_id):
    conn = get_db()
    conn.execute('DELETE FROM schedules WHERE room_id = ?', (room_id,))
    conn.execute('DELETE FROM rooms WHERE id = ?', (room_id,))
    conn.commit()
    conn.close()


# ── Instructors ───────────────────────────────────────────────────────────────

def get_all_instructors():
    conn = get_db()
    rows = conn.execute('SELECT * FROM instructors ORDER BY name').fetchall()
    conn.close()
    return [dict(row) for row in rows]


def create_instructor(name, email, department, preferred_time=None):
    conn = get_db()
    cursor = conn.execute(
        'INSERT INTO instructors (name, email, department, preferred_time) VALUES (?, ?, ?, ?)',
        (name, email, department, preferred_time or None),
    )
    conn.commit()
    row = conn.execute('SELECT * FROM instructors WHERE id = ?', (cursor.lastrowid,)).fetchone()
    conn.close()
    return dict(row)


def delete_instructor(instructor_id):
    conn = get_db()
    conn.execute('DELETE FROM schedules WHERE instructor_id = ?', (instructor_id,))
    conn.execute('DELETE FROM instructors WHERE id = ?', (instructor_id,))
    conn.commit()
    conn.close()


def get_instructor_subjects(instructor_id):
    conn = get_db()
    rows = conn.execute(
        '''SELECT sub.*
           FROM subjects sub
           JOIN instructor_subjects ins ON ins.subject_id = sub.id
           WHERE ins.instructor_id = ?
           ORDER BY sub.code''',
        (instructor_id,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def assign_subject(instructor_id, subject_id, preferred_time=None):
    conn = get_db()
    try:
        conn.execute(
            'INSERT INTO instructor_subjects (instructor_id, subject_id, preferred_time) VALUES (?, ?, ?)',
            (instructor_id, subject_id, preferred_time or None),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        conn.close()
        raise
    conn.close()


def remove_instructor_subject(instructor_id, subject_id):
    conn = get_db()
    conn.execute(
        'DELETE FROM instructor_subjects WHERE instructor_id = ? AND subject_id = ?',
        (instructor_id, subject_id),
    )
    conn.commit()
    conn.close()


# ── Schedules ─────────────────────────────────────────────────────────────────

def get_all_schedules():
    conn = get_db()
    rows = conn.execute('''
        SELECT
            s.id,
            sub.code     AS subject_code,
            sub.name     AS subject_name,
            r.name       AS room_name,
            i.name       AS instructor_name,
            t.day,
            t.start_time,
            t.end_time
        FROM schedules s
        JOIN subjects    sub ON sub.id = s.subject_id
        JOIN rooms       r   ON r.id   = s.room_id
        JOIN instructors i   ON i.id   = s.instructor_id
        JOIN timeslots   t   ON t.id   = s.timeslot_id
        ORDER BY r.name, t.day, t.start_time
    ''').fetchall()
    conn.close()
    return [dict(row) for row in rows]


def clear_schedules():
    conn = get_db()
    conn.execute('DELETE FROM schedules')
    conn.commit()
    conn.close()


def save_schedule(assignments):
    conn = get_db()
    conn.execute('DELETE FROM schedules')
    for a in assignments:
        conn.execute(
            'INSERT INTO schedules (subject_id, room_id, instructor_id, timeslot_id) VALUES (?, ?, ?, ?)',
            (a['subject_id'], a['room_id'], a['instructor_id'], a['timeslot_id']),
        )
    conn.commit()
    conn.close()


# ── Timeslots ─────────────────────────────────────────────────────────────────

def get_all_timeslots():
    conn = get_db()
    rows = conn.execute('SELECT * FROM timeslots').fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_distinct_timeslots():
    conn = get_db()
    rows = conn.execute(
        'SELECT DISTINCT start_time, end_time, duration FROM timeslots ORDER BY start_time'
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ── Solver helpers ────────────────────────────────────────────────────────────

def get_all_instructor_subjects():
    conn = get_db()
    rows = conn.execute('SELECT * FROM instructor_subjects').fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_instructor_availability():
    conn = get_db()
    try:
        rows = conn.execute('SELECT * FROM instructor_availability').fetchall()
        return [dict(row) for row in rows] or None
    except Exception:
        return None
    finally:
        conn.close()


def get_preferred_time_slots():
    conn = get_db()
    rows = conn.execute(
        '''SELECT instructor_id, subject_id, preferred_time AS preferred_start_time
           FROM instructor_subjects
           WHERE preferred_time IS NOT NULL AND preferred_time != ""'''
    ).fetchall()
    conn.close()
    result = [dict(row) for row in rows]
    return result if result else None
