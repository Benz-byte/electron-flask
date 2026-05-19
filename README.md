# Auto Scheduler

A desktop scheduling application built with Electron + React (frontend) and Flask + CP-SAT (backend). It automatically generates conflict-free class schedules for instructors, subjects, and rooms using constraint programming.

---

## Prerequisites

Make sure you have all of these installed before proceeding:

| Tool | Version | Download |
|---|---|---|
| Node.js | 18 or higher | https://nodejs.org |
| Python | 3.10 or higher | https://python.org |
| pip | comes with Python | — |

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/Benz-byte/electron-flask.git
cd electron-flask
```

### 2. Install JavaScript dependencies

```bash
npm install
```

### 3. Install Python dependencies

```bash
pip install -r python/requirements.txt
```

The Python backend requires:
- `flask` — web server
- `flask-cors` — allows the Electron frontend to talk to Flask
- `ortools` — Google OR-Tools, which provides the CP-SAT solver

---

## Running the App

```bash
npm run dev
```

This single command starts three processes in parallel:
- **Vite** — builds and serves the React frontend
- **Electron** — opens the desktop window
- **Flask** — starts the Python API on `http://localhost:5000`

The database (`python/scheduler.db`) is created and seeded automatically on first run.

---

## How to Use

1. **Subjects tab** — add subjects with a code, name, hours per week, and room type (lecture or lab).
2. **Rooms tab** — add rooms with a name, capacity, and type (lecture or lab).
3. **Instructors tab** — add instructors, then use the Assign section to link each instructor to the subjects they teach. Optionally set a preferred start time per assignment.
4. **Schedule tab** — click **Run Solver (CP-SAT)** to generate the schedule. The solver finds a conflict-free timetable and displays it as a room-by-day grid.

---

## Project Structure

```
├── src/
│   ├── electron/        # Electron main process (TypeScript)
│   ├── ui/              # React frontend (TypeScript + CSS)
│   └── api/             # HTTP client and TypeScript types
│
└── python/
    ├── app.py           # Flask entry point
    ├── database.py      # All database logic (schema, CRUD, migrations)
    ├── requirements.txt
    ├── routes/          # HTTP route handlers (subjects, rooms, instructors, schedules, solver)
    └── solver/
        └── cpsat_solver.py  # CP-SAT scheduling logic
```

---

## Building a Distributable

```bash
# Windows
npm run dist:win

# macOS
npm run dist:mac

# Linux
npm run dist:linux
```
