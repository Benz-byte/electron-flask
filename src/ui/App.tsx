import { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'
import type { Subject, Room, Instructor, ScheduleEntry } from '../api/types'
import './App.css'

type Tab = 'subjects' | 'rooms' | 'instructors' | 'schedule'
type ApiStatus = 'connecting' | 'online' | 'offline'

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']

const PREFERRED_TIMES = [
  { label: 'Any time', value: '' },
  ...Array.from({ length: 14 }, (_, i) => {
    const h = String(7 + i).padStart(2, '0')
    return { label: `Start at ${h}:00`, value: `${h}:00` }
  }),
]

// ── Subjects ────────────────────────────────────────────────────────────────

function SubjectsTab() {
  const [items, setItems] = useState<Subject[]>([])
  const [form, setForm] = useState({ code: '', name: '', hours_per_week: 3, type: 'lecture' as 'lecture' | 'lab' | 'cisco' | 'drawing', students: 30 })
  const [err, setErr] = useState('')

  const load = useCallback(async () => {
    try { setItems(await api.subjects.list()) } catch (e) { setErr(String(e)) }
  }, [])

  useEffect(() => { load() }, [load])

  const handleAdd = async (e: React.SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault(); setErr('')
    try { await api.subjects.create(form); setForm({ code: '', name: '', hours_per_week: 3, type: 'lecture' as 'lecture' | 'lab' | 'cisco' | 'drawing', students: 30 }); load() }
    catch (e) { setErr(String(e)) }
  }

  return (
    <div className="tab-pane">
      <h2>Subjects</h2>
      {err && <p className="msg-error">{err}</p>}
      <form className="add-form" onSubmit={handleAdd}>
        <input placeholder="Code (e.g. CS101)" value={form.code} onChange={e => setForm(f => ({ ...f, code: e.target.value }))} required />
        <input placeholder="Name" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} required />
        <input type="number" placeholder="Hrs/wk" value={form.hours_per_week} min={1} max={14} onChange={e => setForm(f => ({ ...f, hours_per_week: +e.target.value }))} required />
        <input type="number" placeholder="Students" value={form.students} min={1} onChange={e => setForm(f => ({ ...f, students: +e.target.value }))} required />
        <select value={form.type} onChange={e => setForm(f => ({ ...f, type: e.target.value as 'lecture' | 'lab' | 'cisco' | 'drawing' }))}>
          <option value="lecture">Lecture</option>
          <option value="lab">Lab</option>
          <option value="cisco">Cisco</option>
          <option value="drawing">Drawing</option>
        </select>
        <button type="submit" className="btn-add">+ Add</button>
      </form>
      <table>
        <thead><tr><th>Code</th><th>Name</th><th>Hrs/Wk</th><th>Students</th><th>Type</th><th /></tr></thead>
        <tbody>
          {items.map(s => (
            <tr key={s.id}>
              <td>{s.code}</td><td>{s.name}</td><td>{s.hours_per_week}</td>
              <td>{s.students}</td>
              <td><span className={`badge badge-${s.type}`}>{s.type}</span></td>
              <td><button className="btn-del" onClick={() => api.subjects.remove(s.id).then(load).catch(e => setErr(String(e)))}>×</button></td>
            </tr>
          ))}
          {items.length === 0 && <tr><td colSpan={6} className="empty-row">No subjects yet</td></tr>}
        </tbody>
      </table>
    </div>
  )
}

// ── Rooms ───────────────────────────────────────────────────────────────────

function RoomsTab() {
  const [items, setItems] = useState<Room[]>([])
  const [form, setForm] = useState({ name: '', capacity: 40, type: 'lecture' as 'lecture' | 'lab' | 'cisco' | 'drawing' })
  const [err, setErr] = useState('')

  const load = useCallback(async () => {
    try { setItems(await api.rooms.list()) } catch (e) { setErr(String(e)) }
  }, [])

  useEffect(() => { load() }, [load])

  const handleAdd = async (e: React.SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault(); setErr('')
    try { await api.rooms.create(form); setForm({ name: '', capacity: 40, type: 'lecture' as 'lecture' | 'lab' | 'cisco' | 'drawing' }); load() }
    catch (e) { setErr(String(e)) }
  }

  return (
    <div className="tab-pane">
      <h2>Rooms</h2>
      {err && <p className="msg-error">{err}</p>}
      <form className="add-form" onSubmit={handleAdd}>
        <input placeholder="Room name (e.g. R101)" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} required />
        <input type="number" placeholder="Capacity" value={form.capacity} min={1} onChange={e => setForm(f => ({ ...f, capacity: +e.target.value }))} required />
        <select value={form.type} onChange={e => setForm(f => ({ ...f, type: e.target.value as 'lecture' | 'lab' | 'cisco' | 'drawing' }))}>
          <option value="lecture">Lecture</option>
          <option value="lab">Lab</option>
          <option value="cisco">Cisco</option>
          <option value="drawing">Drawing</option>
          <option value = 'other'>Fuck you ben</option>
        </select>
        <button type="submit" className="btn-add">+ Add</button>
      </form>
      <table>
        <thead><tr><th>Name</th><th>Capacity</th><th>Type</th><th /></tr></thead>
        <tbody>
          {items.map(r => (
            <tr key={r.id}>
              <td>{r.name}</td><td>{r.capacity}</td>
              <td><span className={`badge badge-${r.type}`}>{r.type}</span></td>
              <td><button className="btn-del" onClick={() => api.rooms.remove(r.id).then(load)}>×</button></td>
            </tr>
          ))}
          {items.length === 0 && <tr><td colSpan={4} className="empty-row">No rooms yet</td></tr>}
        </tbody>
      </table>
    </div>
  )
}

// ── Instructors ──────────────────────────────────────────────────────────────

function InstructorsTab() {
  const [items, setItems]                       = useState<Instructor[]>([])
  const [form, setForm]                         = useState({ name: '', email: '', department: '' })
  const [err, setErr]                           = useState('')
  const [subjects, setSubjects]                 = useState<Subject[]>([])
  const [assignedSubjects, setAssignedSubjects] = useState<Record<number, Subject[]>>({})
  const [assignForm, setAssignForm]             = useState({ instructor_id: 0, subject_id: 0, preferred_time: '' })

  const load = useCallback(async () => {
    try {
      const instructors = await api.instructors.list()
      setItems(instructors)
      // Load each instructor's assigned subjects in parallel.
      const pairs = await Promise.all(
        instructors.map(async (i) => {
          try { return [i.id, await api.instructors.listSubjects(i.id)] as [number, Subject[]] }
          catch  { return [i.id, []] as [number, Subject[]] }
        })
      )
      setAssignedSubjects(Object.fromEntries(pairs))
    } catch (e) { setErr(String(e)) }
  }, [])

  useEffect(() => { load() }, [load])
  useEffect(() => { api.subjects.list().then(setSubjects).catch(() => {}) }, [])

  const handleAdd = async (e: React.SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault(); setErr('')
    try { await api.instructors.create(form); setForm({ name: '', email: '', department: '' }); load() }
    catch (e) { setErr(String(e)) }
  }

  const handleAssign = async (e: React.SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault(); setErr('')
    const { instructor_id, subject_id } = assignForm
    if (!instructor_id || !subject_id) return
    try {
      await api.instructors.assignSubject(instructor_id, subject_id, assignForm.preferred_time || undefined)
      const updated = await api.instructors.listSubjects(instructor_id)
      setAssignedSubjects(prev => ({ ...prev, [instructor_id]: updated }))
    } catch (e) { setErr(String(e)) }
  }

  const handleRemoveSubject = async (instructorId: number, subjectId: number) => {
    try {
      await api.instructors.removeSubject(instructorId, subjectId)
      setAssignedSubjects(prev => ({
        ...prev,
        [instructorId]: (prev[instructorId] ?? []).filter(s => s.id !== subjectId),
      }))
    } catch (e) { setErr(String(e)) }
  }

  return (
    <div className="tab-pane">
      <h2>Instructors</h2>
      {err && <p className="msg-error">{err}</p>}
      <form className="add-form" onSubmit={handleAdd}>
        <input placeholder="Full name" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} required />
        <input placeholder="Email" type="email" value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} />
        <input placeholder="Department" value={form.department} onChange={e => setForm(f => ({ ...f, department: e.target.value }))} />
        <button type="submit" className="btn-add">+ Add</button>
      </form>
      <table>
        <thead><tr><th>Name</th><th>Email</th><th>Department</th><th>Assigned Subjects</th><th /></tr></thead>
        <tbody>
          {items.map(i => (
            <tr key={i.id}>
              <td>{i.name}</td><td>{i.email}</td><td>{i.department}</td>
              <td>
                {(assignedSubjects[i.id] ?? []).map(s => (
                  <span
                    key={s.id}
                    className={`badge badge-${s.type}`}
                    style={{ marginRight: 4, cursor: 'pointer' }}
                    title={`${s.name} — click to remove`}
                    onClick={() => handleRemoveSubject(i.id, s.id)}
                  >
                    {s.code} ×
                  </span>
                ))}
                {(assignedSubjects[i.id] ?? []).length === 0 && <span style={{ color: 'var(--text-muted, #888)', fontSize: '0.85em' }}>none</span>}
              </td>
              <td><button className="btn-del" onClick={() => api.instructors.remove(i.id).then(load)}>×</button></td>
            </tr>
          ))}
          {items.length === 0 && <tr><td colSpan={5} className="empty-row">No instructors yet</td></tr>}
        </tbody>
      </table>

      <h3 style={{ marginTop: '1.5rem', marginBottom: '0.5rem' }}>Assign Subject to Instructor</h3>
      <form className="add-form" onSubmit={handleAssign}>
        <select
          value={assignForm.instructor_id}
          onChange={e => setAssignForm(f => ({ ...f, instructor_id: +e.target.value }))}
          required
        >
          <option value={0}>Select instructor…</option>
          {items.map(i => <option key={i.id} value={i.id}>{i.name}</option>)}
        </select>
        <select
          value={assignForm.subject_id}
          onChange={e => setAssignForm(f => ({ ...f, subject_id: +e.target.value }))}
          required
        >
          <option value={0}>Select subject…</option>
          {subjects.map(s => <option key={s.id} value={s.id}>{s.code} — {s.name}</option>)}
        </select>
        <select value={assignForm.preferred_time} onChange={e => setAssignForm(f => ({ ...f, preferred_time: e.target.value }))}>
          {PREFERRED_TIMES.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <button type="submit" className="btn-add">Assign</button>
      </form>
    </div>
  )
}

// ── Sections ─────────────────────────────────────────────────────────────────

// ── Schedule ─────────────────────────────────────────────────────────────────

function ScheduleTab() {
  const [entries,   setEntries]   = useState<ScheduleEntry[]>([])
  const [rooms,     setRooms]     = useState<Room[]>([])
  const [timeSlots, setTimeSlots] = useState<{ start_time: string; end_time: string }[]>([])
  const [running,   setRunning]   = useState(false)
  const [msg,       setMsg]       = useState('')
  const [err,       setErr]       = useState('')

  const load = useCallback(async () => {
    try {
      const [sched, roomList, slots] = await Promise.all([
        api.schedules.list(),
        api.rooms.list(),
        api.timeslots.list(),
      ])
      setEntries(sched)
      setRooms(roomList)
      setTimeSlots(slots)
    } catch (e) { setErr(String(e)) }
  }, [])

  useEffect(() => { load() }, [load])

  const runSolver = async () => {
    setRunning(true); setMsg(''); setErr('')
    try {
      const result = await api.solver.run()
      if (result.status === 'success') {
        setMsg(`Schedule generated using ${result.solver ?? 'solver'} — ${result.assignments.length} slots assigned.`)
        load()
      } else {
        setErr(result.message ?? 'Solver returned no solution.')
      }
    } catch (e) { setErr(String(e)) }
    finally { setRunning(false) }
  }

  const clearAll = async () => {
    try { await api.schedules.clear(); setEntries([]); setMsg(''); setErr('') }
    catch (e) { setErr(String(e)) }
  }

  // Lookup: "room_name|day|start_time" → ScheduleEntry
  const scheduleMap: Record<string, ScheduleEntry> = {}
  for (const entry of entries) {
    scheduleMap[`${entry.room_name}|${entry.day}|${entry.start_time}`] = entry
  }

  return (
    <div className="tab-pane">
      <h2>Generated Schedule</h2>
      <div className="solver-bar">
        <button className="btn-primary" onClick={runSolver} disabled={running}>
          {running ? 'Running solver…' : 'Run Solver (CP-SAT)'}
        </button>
        <button className="btn-secondary" onClick={clearAll} disabled={running}>Clear</button>
      </div>
      {msg && <p className="msg-success">{msg}</p>}
      {err && <p className="msg-error">{err}</p>}

      {rooms.length === 0 ? (
        <p className="empty-row" style={{ marginTop: '2rem' }}>
          No rooms yet — add subjects, rooms, and instructors, assign subjects to instructors, then click Run Solver.
        </p>
      ) : (
        DAYS.map(day => (
          <div key={day} className="day-group">
            <h3 className="day-heading">{day}</h3>
            <table>
              <thead>
                <tr>
                  <th style={{ whiteSpace: 'nowrap' }}>Time</th>
                  {rooms.map(room => (
                    <th key={room.id}>
                      {room.name}
                      <br />
                      <span style={{ fontWeight: 'normal', fontSize: '0.78em' }}>({room.type})</span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {timeSlots.map(slot => (
                  <tr key={slot.start_time}>
                    <td className="time-cell" style={{ whiteSpace: 'nowrap' }}>
                      {slot.start_time} – {slot.end_time}
                    </td>
                    {rooms.map(room => {
                      const entry = scheduleMap[`${room.name}|${day}|${slot.start_time}`]
                      return (
                        <td key={room.id} style={entry ? { verticalAlign: 'top' } : { color: '#bbb', textAlign: 'center', fontSize: '0.8em' }}>
                          {entry ? (
                            <>
                              <strong>{entry.subject_code}</strong>
                              <br />
                              <small style={{ display: 'block' }}>{entry.subject_name}</small>
                              <small style={{ display: 'block', color: '#666' }}>{entry.instructor_name}</small>
                            </>
                          ) : 'Vacant'}
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))
      )}
    </div>
  )
}

// ── Root App ─────────────────────────────────────────────────────────────────

export default function App() {
  const [tab, setTab] = useState<Tab>('subjects')
  const [apiStatus, setApiStatus] = useState<ApiStatus>('connecting')

  useEffect(() => {
    const check = () =>
      api.health()
        .then(() => setApiStatus('online'))
        .catch(() => setApiStatus('offline'))

    check()
    const id = setInterval(check, 5000)
    return () => clearInterval(id)
  }, [])

  const tabs: { key: Tab; label: string }[] = [
    { key: 'subjects',    label: 'Subjects' },
    { key: 'rooms',       label: 'Rooms' },
    { key: 'instructors', label: 'Instructors' },
    { key: 'schedule',    label: 'Schedule' },
  ]

  return (
    <div className="app-shell">
      <header className="app-header">
        <span className="app-title">Auto Scheduler</span>
        <span className={`api-badge api-${apiStatus}`}>
          {apiStatus === 'connecting' ? 'Connecting…' : apiStatus === 'online' ? 'API Online' : 'API Offline'}
        </span>
      </header>

      <nav className="tab-nav">
        {tabs.map(t => (
          <button
            key={t.key}
            className={`tab-btn${tab === t.key ? ' active' : ''}`}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <main className="app-main">
        {tab === 'subjects'    && <SubjectsTab />}
        {tab === 'rooms'       && <RoomsTab />}
        {tab === 'instructors' && <InstructorsTab />}
        {tab === 'schedule'    && <ScheduleTab />}
      </main>
    </div>
  )
}
