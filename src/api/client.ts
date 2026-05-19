import type {
  Subject, Room, Instructor,
  ScheduleEntry, SolverResult,
} from './types'

// URL injected by the Electron preload; fall back for plain browser dev
const BASE = window.electron?.flaskUrl ?? 'http://localhost:5000'

async function req<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }))
    throw new Error((err as { error?: string }).error ?? res.statusText)
  }
  return res.json() as Promise<T>
}

export const api = {
  health: () =>
    req<{ status: string; message: string }>('GET', '/api/health'),

  subjects: {
    list:   ()                          => req<Subject[]>('GET',    '/api/subjects/'),
    create: (data: Omit<Subject, 'id'>) => req<Subject>  ('POST',   '/api/subjects/', data),
    remove: (id: number)                => req<void>      ('DELETE', `/api/subjects/${id}`),
  },

  rooms: {
    list:   ()                        => req<Room[]>('GET',    '/api/rooms/'),
    create: (data: Omit<Room, 'id'>) => req<Room>  ('POST',   '/api/rooms/', data),
    remove: (id: number)              => req<void>  ('DELETE', `/api/rooms/${id}`),
  },

  instructors: {
    list:          ()                              => req<Instructor[]>('GET',    '/api/instructors/'),
    create:        (data: Omit<Instructor, 'id'>) => req<Instructor>  ('POST',   '/api/instructors/', data),
    remove:        (id: number)                    => req<void>         ('DELETE', `/api/instructors/${id}`),
    listSubjects:  (id: number)                    => req<Subject[]>   ('GET',    `/api/instructors/${id}/subjects`),
    assignSubject: (id: number, subjectId: number, preferredTime?: string) =>
      req<void>('POST', `/api/instructors/${id}/subjects`, { subject_id: subjectId, preferred_time: preferredTime || null }),
    removeSubject: (id: number, subjectId: number) => req<void>         ('DELETE', `/api/instructors/${id}/subjects/${subjectId}`),
  },

  timeslots: {
    list: () => req<{ start_time: string; end_time: string }[]>('GET', '/api/timeslots/'),
  },

  schedules: {
    list:  () => req<ScheduleEntry[]>('GET',    '/api/schedules/'),
    clear: () => req<void>            ('DELETE', '/api/schedules/'),
  },

  solver: {
    run:    () => req<SolverResult>                       ('POST', '/api/solver/run'),
    status: () => req<{ status: string; message: string }>('GET',  '/api/solver/status'),
  },
}
