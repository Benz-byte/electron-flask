export interface Subject {
  id: number
  code: string
  name: string
  hours_per_week: number
  type: 'lecture' | 'lab'
  preferred_time?: string
  students: number
}

export interface Room {
  id: number
  name: string
  capacity: number
  type: 'lecture' | 'lab'
}

export interface Instructor {
  id: number
  name: string
  email: string
  department: string
  preferred_time?: string
}


export interface Timeslot {
  id: number
  day: string
  start_time: string
  end_time: string
  duration: number
}

export interface ScheduleEntry {
  id: number
  subject_code: string
  subject_name: string
  room_name: string
  instructor_name: string
  day: string
  start_time: string
  end_time: string
}

export interface SolverResult {
  status: 'success' | 'infeasible' | 'error'
  solver?: string
  solution_status?: string
  message?: string
  assignments: Array<{
    subject_id: number
    room_id: number
    instructor_id: number
    timeslot_id: number
  }>
}
