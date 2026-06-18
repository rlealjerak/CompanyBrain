import { useEffect, useState, ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { api, PersonalTask, TaskSummary } from '../api/client'
import { IconCheckSquare, IconSparkles, IconArrowRight, IconRefresh, IconDoc, IconDatabase, IconClock, IconTrendUp } from './Icons'

export default function RightPanel() {
  const { token } = useAuth()
  const navigate = useNavigate()
  const [tasks, setTasks] = useState<PersonalTask[]>([])
  const [summary, setSummary] = useState<TaskSummary | null>(null)
  const [_docCount, setDocCount] = useState<number>(0)

  useEffect(() => {
    if (!token) return
    api.listTasks(token, 'open').then(d => setTasks(d.tasks.slice(0, 4))).catch(() => {})
    api.getTaskSummary(token).then(setSummary).catch(() => {})
    api.listJobs(token, 100).then(d => setDocCount(d.jobs.length)).catch(() => {})
  }, [token])

  const urgencyColor = (band: string | null) => {
    if (band === 'high') return { color: 'var(--high)', bg: 'var(--high-bg)' }
    if (band === 'medium') return { color: 'var(--mid)', bg: 'var(--mid-bg)' }
    return { color: 'var(--low)', bg: 'var(--low-bg)' }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* My Tasks section */}
      <div style={{ padding: '16px 14px 0', borderBottom: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{
              width: 30, height: 30, borderRadius: 8,
              background: 'var(--purple-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <IconCheckSquare size={15} color="var(--purple)" />
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: '0.88rem', color: 'var(--text-1)' }}>My Tasks</div>
              <div style={{ fontSize: '0.69rem', color: 'var(--text-2)' }}>Personal Intelligence</div>
            </div>
          </div>
          <IconSparkles size={16} color="var(--accent)" />
        </div>

        {/* Task list */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 1, marginBottom: 10 }}>
          {tasks.length === 0 ? (
            <p style={{ fontSize: '0.78rem', color: 'var(--text-2)', textAlign: 'center', padding: '12px 0' }}>
              No open tasks. Click Extract Tasks on the dashboard.
            </p>
          ) : tasks.map(task => {
            const uc = urgencyColor(task.urgency_band)
            return (
              <div key={task.id} className="card-hover" style={{
                display: 'flex', gap: 8, padding: '9px 4px', borderRadius: 8,
                cursor: 'pointer',
              }} onClick={() => navigate('/tasks')}>
                <div style={{
                  width: 16, height: 16, borderRadius: 4, border: '1.5px solid var(--border-s)',
                  flexShrink: 0, marginTop: 1,
                }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-1)', lineHeight: 1.3, marginBottom: 2 }}>
                    {task.description.length > 55 ? task.description.slice(0, 55) + '…' : task.description}
                  </div>
                  <div style={{ fontSize: '0.69rem', color: 'var(--text-2)' }}>
                    {task.source_label ?? task.source_reference}
                  </div>
                </div>
                {task.urgency_band && (
                  <span style={{
                    flexShrink: 0, fontSize: '0.65rem', fontWeight: 700,
                    padding: '2px 7px', borderRadius: 5,
                    color: uc.color, background: uc.bg,
                    alignSelf: 'flex-start', textTransform: 'capitalize',
                  }}>
                    {task.urgency_band.charAt(0).toUpperCase() + task.urgency_band.slice(1)}
                  </span>
                )}
              </div>
            )
          })}
        </div>

        <button
          onClick={() => navigate('/tasks')}
          style={{
            display: 'flex', alignItems: 'center', gap: 4,
            background: 'none', border: 'none', cursor: 'pointer',
            color: 'var(--purple)', fontSize: '0.78rem', fontWeight: 600,
            padding: '0 4px 14px', marginLeft: 'auto',
          }}
        >
          View all tasks <IconArrowRight size={13} />
        </button>
      </div>

      {/* Knowledge at a glance */}
      <div style={{ padding: '14px 14px 0' }}>
        <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-2)', marginBottom: 10 }}>
          Knowledge at a glance
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 12 }}>
          <StatCard icon={<IconDoc size={16} color="var(--accent)" />} value="50+" label="Documents Indexed" />
          <StatCard icon={<IconDatabase size={16} color="var(--purple)" />} value="2" label="Sources Connected" />
          <StatCard icon={<IconClock size={16} color="var(--mid)" />} value="Auto" label="Last Sync Time" />
          <StatCard icon={<IconTrendUp size={16} color="var(--green)" />}
            value={summary ? summary.total.toString() : '—'} label="Tasks Today" />
        </div>

        {summary && (
          <div style={{
            padding: '8px 10px', borderRadius: 8,
            background: 'var(--bg-card)', border: '1px solid var(--border)',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12,
          }}>
            <div style={{ display: 'flex', gap: 12 }}>
              <Pill label="High" count={summary.high} color="var(--high)" />
              <Pill label="Med" count={summary.medium} color="var(--mid)" />
              <Pill label="Low" count={summary.low} color="var(--low)" />
            </div>
            <span style={{ fontSize: '0.68rem', color: 'var(--text-2)' }}>{summary.total} open</span>
          </div>
        )}

        <div style={{ display: 'flex', alignItems: 'center', gap: 5, color: 'var(--text-3)', fontSize: '0.7rem', paddingBottom: 14 }}>
          <IconRefresh size={12} />
          Data synced automatically
        </div>
      </div>
    </div>
  )
}

function StatCard({ icon, value, label }: { icon: ReactNode; value: string; label: string }) {
  return (
    <div style={{
      background: 'var(--bg-card)', border: '1px solid var(--border)',
      borderRadius: 8, padding: '10px 10px',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>{icon}</div>
      <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-1)', lineHeight: 1 }}>{value}</div>
      <div style={{ fontSize: '0.67rem', color: 'var(--text-2)', marginTop: 2 }}>{label}</div>
    </div>
  )
}

function Pill({ label, count, color }: { label: string; count: number; color: string }) {
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{ fontSize: '0.85rem', fontWeight: 700, color }}>{count}</div>
      <div style={{ fontSize: '0.63rem', color: 'var(--text-3)' }}>{label}</div>
    </div>
  )
}

