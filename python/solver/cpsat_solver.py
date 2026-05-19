"""
CP-SAT solver for the scheduler.

The model keeps one scheduling unit per (instructor, subject) pair.  Each unit
chooses a matching room and one valid timeslot block; overlap constraints are
then enforced from those choices instead of pre-expanding room x block x pattern
assignment variables.
"""

from ortools.sat.python import cp_model
from typing import Any, Optional

WINDOW_START_MINUTES = 7 * 60
WINDOW_END_MINUTES = 21 * 60
DEFAULT_PREFERRED_START_MINUTES = 9 * 60
ALIGNMENT_MINUTES = 30


def _time_to_minutes(time_str: str) -> int:
    hours, minutes = map(int, time_str.split(":"))
    return hours * 60 + minutes


def _is_aligned(minutes: int) -> bool:
    return (minutes - WINDOW_START_MINUTES) % ALIGNMENT_MINUTES == 0


def _slot_duration(timeslots: list[dict]) -> int:
    durations = {int(t["duration"]) for t in timeslots}
    return min(durations) if durations else ALIGNMENT_MINUTES


def _allowed_timeslots(timeslots: list[dict], slot_duration_minutes: int) -> list[dict]:
    allowed = []
    for slot in timeslots:
        start = _time_to_minutes(slot["start_time"])
        end = _time_to_minutes(slot["end_time"])
        if (
            int(slot["duration"]) == slot_duration_minutes
            and start >= WINDOW_START_MINUTES
            and end <= WINDOW_END_MINUTES
            and end - start == slot_duration_minutes
            and _is_aligned(start)
            and _is_aligned(end)
        ):
            allowed.append(slot)
    return allowed


def _get_session_patterns(hours_per_week: int, slot_duration_minutes: int) -> list[tuple[int, ...]]:
    total_slots = int(hours_per_week * (60 / slot_duration_minutes))
    if total_slots <= 0 or total_slots != hours_per_week * (60 / slot_duration_minutes):
        return []
    if total_slots == 6:
        return [(6,), (3, 3)]
    if total_slots == 10:
        return [(10,), (4, 6), (5, 5)]
    return [(total_slots,)]


def _find_consecutive_blocks(timeslots: list[dict], slots_needed: int) -> list[list[int]]:
    by_day: dict[str, list[dict]] = {}
    for slot in timeslots:
        by_day.setdefault(slot["day"], []).append(slot)

    blocks = []
    for day_slots in by_day.values():
        sorted_slots = sorted(day_slots, key=lambda s: _time_to_minutes(s["start_time"]))
        for start_index in range(len(sorted_slots) - slots_needed + 1):
            block = sorted_slots[start_index : start_index + slots_needed]
            if all(
                _time_to_minutes(block[i]["start_time"]) == _time_to_minutes(block[i - 1]["end_time"])
                for i in range(1, len(block))
            ):
                blocks.append([slot["id"] for slot in block])
    return blocks


def _candidate_blocks(
    timeslots: list[dict],
    patterns: list[tuple[int, ...]],
    permitted_timeslot_ids: Optional[set[int]] = None,
) -> list[list[int]]:
    by_size: dict[int, list[list[int]]] = {}
    for pattern in patterns:
        for size in pattern:
            if size not in by_size:
                blocks = _find_consecutive_blocks(timeslots, size)
                if permitted_timeslot_ids is not None:
                    blocks = [block for block in blocks if all(ts_id in permitted_timeslot_ids for ts_id in block)]
                by_size[size] = blocks

    candidates: list[list[int]] = []
    seen: set[tuple[int, ...]] = set()
    timeslot_map = {slot["id"]: slot for slot in timeslots}

    for pattern in patterns:
        if len(pattern) == 1:
            for block in by_size.get(pattern[0], []):
                key = tuple(block)
                if key not in seen:
                    seen.add(key)
                    candidates.append(block)
            continue

        first_size, second_size = pattern
        first_blocks = by_size.get(first_size, [])
        second_blocks = by_size.get(second_size, [])
        symmetric = first_size == second_size
        use_aligned_split_starts = len(first_blocks) * len(second_blocks) > 1000
        for first in first_blocks:
            for second in second_blocks:
                if timeslot_map[first[0]]["day"] == timeslot_map[second[0]]["day"]:
                    continue
                if symmetric and first[0] >= second[0]:
                    continue
                if use_aligned_split_starts and (
                    timeslot_map[first[0]]["start_time"] != timeslot_map[second[0]]["start_time"]
                ):
                    continue
                block = first + second
                key = tuple(block)
                if key not in seen:
                    seen.add(key)
                    candidates.append(block)
    return candidates


def _parse_instructor_availability(
    instructor_availability: list[dict],
    timeslot_map: dict[int, dict],
    allowed_timeslot_ids: set[int],
) -> tuple[dict[int, list[tuple]], dict[int, set[int]]]:
    windows: dict[int, list[tuple]] = {}
    for row in instructor_availability:
        windows.setdefault(row["instructor_id"], []).append(
            (
                row["day"],
                _time_to_minutes(row["start_time"]),
                _time_to_minutes(row["end_time"]),
            )
        )

    allowed_by_instructor: dict[int, set[int]] = {}
    for instructor_id, instructor_windows in windows.items():
        allowed: set[int] = set()
        for ts_id in allowed_timeslot_ids:
            slot = timeslot_map[ts_id]
            start = _time_to_minutes(slot["start_time"])
            end = _time_to_minutes(slot["end_time"])
            if any(
                slot["day"] == day and start >= win_start and end <= win_end
                for day, win_start, win_end in instructor_windows
            ):
                allowed.add(ts_id)
        allowed_by_instructor[instructor_id] = allowed
    return windows, allowed_by_instructor


def _availability_satisfaction_score(
    block: list[int],
    instructor_id: int,
    timeslot_map: dict[int, dict],
    availability_windows: dict[int, list[tuple]],
) -> int:
    windows = availability_windows.get(instructor_id)
    if not windows:
        return 0

    score = 0
    for ts_id in block:
        slot = timeslot_map[ts_id]
        start = _time_to_minutes(slot["start_time"])
        end = _time_to_minutes(slot["end_time"])
        for day, win_start, win_end in windows:
            if slot["day"] == day and start >= win_start and end <= win_end:
                score += win_end - end
                break
    return score


def _preferred_time_deviation(
    block: list[int],
    instructor_id: int,
    subject_id: int,
    timeslot_map: dict[int, dict],
    preferred_start_map: dict[tuple[int, int], int],
) -> int:
    preferred_start = preferred_start_map.get((instructor_id, subject_id))
    if preferred_start is None:
        return 0
    first_by_day: dict[str, int] = {}
    for ts_id in block:
        slot = timeslot_map[ts_id]
        start = _time_to_minutes(slot["start_time"])
        day = slot["day"]
        first_by_day[day] = min(first_by_day.get(day, start), start)
    return sum(0 if start == preferred_start else 8 for start in first_by_day.values())


def _status_name(solver: cp_model.CpSolver, status: int) -> str:
    return solver.status_name(status)


def _diagnostics(
    pairs: list[dict],
    pair_data: dict[int, dict],
    subject_map: dict[int, dict],
    instructor_map: dict[int, dict],
    rooms: list[dict],
    allowed_timeslot_ids: set[int],
    allowed_timeslots_per_instructor: dict[int, set[int]],
) -> str:
    problems: list[str] = []

    rooms_by_type: dict[str, list[dict]] = {}
    for room in rooms:
        rooms_by_type.setdefault(room["type"], []).append(room)

    for index, row in enumerate(pairs):
        instructor = instructor_map.get(row["instructor_id"], {"name": f"Instructor {row['instructor_id']}"})
        subject = subject_map.get(row["subject_id"], {"code": f"Subject {row['subject_id']}", "type": "unknown"})
        data = pair_data.get(index)
        if not rooms_by_type.get(subject["type"]):
            problems.append(f"Missing rooms: {subject['code']} needs a {subject['type']} room.")
        if data is not None and not data["blocks"]:
            problems.append(
                f"Missing valid blocks: {instructor['name']} / {subject['code']} has no block inside 07:00-21:00"
                " that also satisfies availability."
            )

    required_by_instructor: dict[int, int] = {}
    for data in pair_data.values():
        required_by_instructor[data["instructor_id"]] = (
            required_by_instructor.get(data["instructor_id"], 0) + data["required_slots"]
        )
    for instructor_id, required in required_by_instructor.items():
        available = len(allowed_timeslots_per_instructor.get(instructor_id, allowed_timeslot_ids))
        if required > available:
            name = instructor_map.get(instructor_id, {}).get("name", f"Instructor {instructor_id}")
            problems.append(
                f"Instructor conflicts: {name} needs {required} slots but only {available} allowed slots exist."
            )

    required_by_type: dict[str, int] = {}
    for data in pair_data.values():
        required_by_type[data["room_type"]] = required_by_type.get(data["room_type"], 0) + data["required_slots"]
    for room_type, required in required_by_type.items():
        capacity = len(rooms_by_type.get(room_type, [])) * len(allowed_timeslot_ids)
        if required > capacity:
            problems.append(
                f"Missing rooms: {room_type} subjects need {required} room-slots but only {capacity} are available."
            )

    if not problems:
        problems.append(
            "Instructor conflicts: the remaining constraints leave no non-overlapping combination. "
            "Check shared rooms, tight availability windows, and long subject blocks."
        )
    return "\n- " + "\n- ".join(dict.fromkeys(problems))


def run_cpsat_solver(
    subjects: list[dict],
    rooms: list[dict],
    instructors: list[dict],
    instructor_subjects: list[dict],
    timeslots: list[dict],
    instructor_availability: Optional[list[dict]] = None,
    preferred_time_slots: Optional[list[dict]] = None,
) -> dict[str, Any]:
    if not instructor_subjects:
        return {
            "status": "error",
            "solution_status": "NO_INPUT",
            "message": (
                "No subjects are assigned to any instructor. Go to the Instructors tab, select an instructor "
                "and a subject, then click Assign."
            ),
            "assignments": [],
        }
    if not rooms:
        return {
            "status": "error",
            "solution_status": "NO_ROOMS",
            "message": "No rooms found. Add at least one room before running the solver.",
            "assignments": [],
        }
    if not timeslots:
        return {
            "status": "error",
            "solution_status": "NO_TIMESLOTS",
            "message": "No timeslots found in the database. Restart the server so the database can seed them.",
            "assignments": [],
        }

    slot_duration_minutes = _slot_duration(timeslots)
    allowed_timeslots = _allowed_timeslots(timeslots, slot_duration_minutes)
    allowed_timeslot_ids = {slot["id"] for slot in allowed_timeslots}
    if not allowed_timeslots:
        return {
            "status": "error",
            "solution_status": "NO_ALLOWED_TIMESLOTS",
            "message": "No valid 30-minute aligned timeslots exist inside the strict 07:00-21:00 window.",
            "assignments": [],
        }

    timeslot_map = {slot["id"]: slot for slot in timeslots}
    instructor_map = {instructor["id"]: instructor for instructor in instructors}
    subject_map = {subject["id"]: subject for subject in subjects}

    availability_windows: dict[int, list[tuple]] = {}
    allowed_timeslots_per_instructor: dict[int, set[int]] = {}
    if instructor_availability:
        availability_windows, allowed_timeslots_per_instructor = _parse_instructor_availability(
            instructor_availability,
            timeslot_map,
            allowed_timeslot_ids,
        )

    preferred_start_map: dict[tuple[int, int], int] = {}
    if preferred_time_slots:
        for row in preferred_time_slots:
            preferred_start_map[(row["instructor_id"], row["subject_id"])] = _time_to_minutes(
                row["preferred_start_time"]
            )

    rooms_by_type: dict[str, list[dict]] = {}
    for room in rooms:
        rooms_by_type.setdefault(room["type"], []).append(room)

    problems: list[str] = []
    pairs: list[dict] = []
    pair_data: dict[int, dict] = {}

    for row in instructor_subjects:
        instructor_id = row["instructor_id"]
        subject_id = row["subject_id"]
        subject = subject_map.get(subject_id)
        instructor = instructor_map.get(instructor_id)

        if not instructor:
            problems.append(f"Instructor id={instructor_id} no longer exists; remove and re-add the assignment.")
            continue
        if not subject:
            problems.append(f"Subject id={subject_id} no longer exists; remove and re-add the assignment.")
            continue

        matching_rooms = rooms_by_type.get(subject["type"], [])
        if not matching_rooms:
            problems.append(f"Missing rooms: {subject['code']} needs a {subject['type']} room.")
            continue

        patterns = _get_session_patterns(int(subject["hours_per_week"]), slot_duration_minutes)
        if not patterns:
            problems.append(
                f"Missing valid blocks: {subject['code']} has hours_per_week that does not align with "
                f"{slot_duration_minutes}-minute slots."
            )
            continue

        instructor_allowed = allowed_timeslots_per_instructor.get(instructor_id)
        blocks = _candidate_blocks(allowed_timeslots, patterns, instructor_allowed)

        pair_index = len(pairs)
        pairs.append(row)
        pair_data[pair_index] = {
            "instructor_id": instructor_id,
            "subject_id": subject_id,
            "room_type": subject["type"],
            "room_ids": [room["id"] for room in matching_rooms],
            "blocks": blocks,
            "required_slots": sum(patterns[0]),
        }
        if not blocks:
            problems.append(
                f"Missing valid blocks: {instructor['name']} / {subject['code']} has no block inside 07:00-21:00"
                " that also satisfies availability."
            )

    if problems:
        return {
            "status": "infeasible",
            "solution_status": "INVALID_INPUT",
            "message": "Cannot build a feasible schedule:\n- " + "\n- ".join(dict.fromkeys(problems)),
            "assignments": [],
        }

    model = cp_model.CpModel()

    assigned: dict[int, cp_model.IntVar] = {}
    room_choice: dict[int, cp_model.IntVar] = {}
    block_choice: dict[int, cp_model.IntVar] = {}
    uses_slot: dict[tuple[int, int], cp_model.IntVar] = {}
    uses_room: dict[tuple[int, int], cp_model.IntVar] = {}
    uses_room_slot: dict[tuple[int, int, int], cp_model.IntVar] = {}
    availability_terms = []
    deviation_terms = []
    max_deviation_total = 0

    for pair_index, data in pair_data.items():
        assigned[pair_index] = model.new_bool_var(f"assign_{pair_index}")
        model.add(assigned[pair_index] == 1)

        room_ids = data["room_ids"]
        blocks = data["blocks"]
        room_choice[pair_index] = model.new_int_var(0, len(room_ids) - 1, f"room_{pair_index}")
        block_choice[pair_index] = model.new_int_var(0, len(blocks) - 1, f"block_{pair_index}")

        for room_idx, room_id in enumerate(room_ids):
            room_var = model.new_bool_var(f"pair_{pair_index}_room_{room_id}")
            model.add(room_choice[pair_index] == room_idx).only_enforce_if(room_var)
            model.add(room_choice[pair_index] != room_idx).only_enforce_if(room_var.Not())
            uses_room[(pair_index, room_id)] = room_var

        relevant_slots = sorted({ts_id for block in blocks for ts_id in block})
        for ts_id in relevant_slots:
            containing_blocks = [block_idx for block_idx, block in enumerate(blocks) if ts_id in block]
            slot_var = model.new_bool_var(f"pair_{pair_index}_slot_{ts_id}")
            model.add_allowed_assignments(
                [block_choice[pair_index], slot_var],
                [(block_idx, 1 if block_idx in containing_blocks else 0) for block_idx in range(len(blocks))],
            )
            uses_slot[(pair_index, ts_id)] = slot_var

        for room_id in room_ids:
            for ts_id in relevant_slots:
                room_slot_var = model.new_bool_var(f"pair_{pair_index}_room_{room_id}_slot_{ts_id}")
                model.add_bool_and([uses_room[(pair_index, room_id)], uses_slot[(pair_index, ts_id)]]).only_enforce_if(
                    room_slot_var
                )
                model.add_bool_or(
                    [uses_room[(pair_index, room_id)].Not(), uses_slot[(pair_index, ts_id)].Not()]
                ).only_enforce_if(room_slot_var.Not())
                uses_room_slot[(pair_index, room_id, ts_id)] = room_slot_var

        if availability_windows:
            scores = [
                _availability_satisfaction_score(
                    block,
                    data["instructor_id"],
                    timeslot_map,
                    availability_windows,
                )
                for block in blocks
            ]
            max_score = max(scores) if scores else 0
            score_var = model.new_int_var(0, max_score, f"availability_score_{pair_index}")
            model.add_element(block_choice[pair_index], scores, score_var)
            availability_terms.append(score_var)

        if preferred_start_map:
            deviations = [
                _preferred_time_deviation(
                    block,
                    data["instructor_id"],
                    data["subject_id"],
                    timeslot_map,
                    preferred_start_map,
                )
                for block in blocks
            ]
            max_deviation = max(deviations) if deviations else 0
            max_deviation_total += max_deviation
            deviation_var = model.new_int_var(0, max_deviation, f"preferred_deviation_{pair_index}")
            model.add_element(block_choice[pair_index], deviations, deviation_var)
            deviation_terms.append(deviation_var)

    # No instructor overlap per timeslot.
    instructor_slot_groups: dict[tuple[int, int], list[cp_model.IntVar]] = {}
    for (pair_index, ts_id), slot_var in uses_slot.items():
        instructor_slot_groups.setdefault((pair_data[pair_index]["instructor_id"], ts_id), []).append(slot_var)
    for group in instructor_slot_groups.values():
        if len(group) > 1:
            model.add_at_most_one(group)

    # No room overlap per timeslot.
    room_slot_groups: dict[tuple[int, int], list[cp_model.IntVar]] = {}
    for (pair_index, room_id, ts_id), room_slot_var in uses_room_slot.items():
        room_slot_groups.setdefault((room_id, ts_id), []).append(room_slot_var)
    for group in room_slot_groups.values():
        if len(group) > 1:
            model.add_at_most_one(group)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30.0
    solver.parameters.num_search_workers = 8

    best_rooms: dict[int, int] = {}
    best_blocks: dict[int, int] = {}

    def remember_solution() -> None:
        best_rooms.clear()
        best_blocks.clear()
        for pair_index, data in pair_data.items():
            best_rooms[pair_index] = data["room_ids"][solver.value(room_choice[pair_index])]
            best_blocks[pair_index] = solver.value(block_choice[pair_index])

    stage1_status = solver.solve(model)
    final_status = stage1_status
    if stage1_status not in (cp_model.FEASIBLE, cp_model.OPTIMAL):
        detail = _diagnostics(
            pairs,
            pair_data,
            subject_map,
            instructor_map,
            rooms,
            allowed_timeslot_ids,
            allowed_timeslots_per_instructor,
        )
        return {
            "status": "infeasible",
            "solution_status": _status_name(solver, stage1_status),
            "message": f"No feasible schedule found. Diagnostics:{detail}",
            "assignments": [],
        }
    remember_solution()

    availability_expr = sum(availability_terms) if availability_terms else None
    deviation_expr = sum(deviation_terms) if deviation_terms else None

    if availability_expr is not None:
        model.maximize(availability_expr)
        stage2_status = solver.solve(model)
        if stage2_status in (cp_model.FEASIBLE, cp_model.OPTIMAL):
            final_status = stage2_status
            remember_solution()

    if deviation_expr is not None:
        if availability_expr is not None:
            # Keep Stage 2 lexicographic: one point of availability is worth more
            # than the full possible preferred-time deviation range.
            model.minimize((max_deviation_total + 1) * -availability_expr + deviation_expr)
        else:
            model.minimize(deviation_expr)
        stage3_status = solver.solve(model)
        if stage3_status in (cp_model.FEASIBLE, cp_model.OPTIMAL):
            final_status = stage3_status
            remember_solution()

    assignments = []
    for pair_index, data in pair_data.items():
        block = data["blocks"][best_blocks[pair_index]]
        for ts_id in block:
            assignments.append(
                {
                    "instructor_id": data["instructor_id"],
                    "subject_id": data["subject_id"],
                    "room_id": best_rooms[pair_index],
                    "timeslot_id": ts_id,
                }
            )

    return {
        "status": "success",
        "solution_status": _status_name(solver, final_status),
        "message": f"Schedule generated with {len(assignments)} session slots assigned.",
        "assignments": assignments,
    }
