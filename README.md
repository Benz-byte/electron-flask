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

## How the Solver Works

The solver (`python/solver/cpsat_solver.py`) uses two techniques together:

### Constraint Programming (CP-SAT)

Constraint programming means you describe the *rules* the schedule must follow, and the solver finds a valid answer on its own.

**Step 1 — Create the model (line 395)**

The model is the "rule book" everything gets added to.

```python
model = cp_model.CpModel()
```

**Step 2 — Create variables for each instructor-subject pair (lines 407–414)**

For every pair, the solver must choose a room and a time block. These are the decisions it needs to make.

```python
room_choice[pair_index]  = model.new_int_var(0, len(room_ids) - 1, f"room_{pair_index}")
block_choice[pair_index] = model.new_int_var(0, len(blocks) - 1,   f"block_{pair_index}")
```

**Step 3 — Track which room and timeslot each pair occupies (lines 416–441)**

Intermediate variables are created so the solver can check for conflicts — it needs to know exactly which room and which timeslot each class uses.

```python
uses_room[(pair_index, room_id)]           = room_var
uses_slot[(pair_index, ts_id)]             = slot_var
uses_room_slot[(pair_index, room_id, ts_id)] = room_slot_var
```

**Step 4 — Rule: no instructor can be in two places at once (lines 476–481)**

```python
for group in instructor_slot_groups.values():
    if len(group) > 1:
        model.add_at_most_one(group)
```

For every instructor and every timeslot, at most one class can be active. If this rule is broken, the schedule is rejected.

**Step 5 — Rule: no room can hold two classes at once (lines 483–489)**

```python
for group in room_slot_groups.values():
    if len(group) > 1:
        model.add_at_most_one(group)
```

Same idea as above but for rooms instead of instructors.

**Step 6 — Run the solver (lines 505–522)**

The solver searches for any assignment that satisfies all the rules above. If it finds one, it moves on to optimization. If not, it runs diagnostics and returns an error.

```python
stage1_status = solver.solve(model)
```

Room-type matching and capacity checks happen earlier at lines 349–358, before the model is even built — pairs that have no valid room are rejected immediately with a clear error message.

---

### Lexicographic Multi-Criteria Sorting

Once a valid schedule is found, the solver tries to improve it. It optimizes across multiple goals but in a strict priority order — a higher-ranked goal is never sacrificed to gain on a lower-ranked one.

| Rank | Goal | Description |
|------|------|-------------|
| 1 | **Feasibility** | Find any schedule that satisfies all hard constraints. This must be achieved before anything else. |
| 2 | **Instructor availability** | Maximize how well class times fit each instructor's available windows. One point of availability is worth more than any improvement in rank 3. |
| 3 | **Preferred start time** | Minimize how far each class is from the instructor's preferred start time, without undoing any gains from rank 2. |

**Rank 1 — Feasibility (line 505)**

Just find *any* valid schedule. No optimization yet, only rule-following.

```python
stage1_status = solver.solve(model)
```

**Rank 2 — Instructor availability (lines 528–533)**

Re-run the solver but now tell it to maximize how well class times fit each instructor's preferred availability windows.

```python
model.maximize(availability_expr)
stage2_status = solver.solve(model)
```

**Rank 3 — Preferred start time (lines 535–545)**

Re-run again to minimize how far each class is from the instructor's preferred start time. The multiplier `(max_deviation_total + 1)` is what locks in Rank 2 — it makes one point of availability mathematically worth more than any possible improvement in preferred time, so the solver will never trade one away for the other.

```python
model.minimize((max_deviation_total + 1) * -availability_expr + deviation_expr)
stage3_status = solver.solve(model)
```

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
