import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { api, PersonalTask, SearchResult } from '../api/client'
import Layout from '../components/Layout'
import { IconCheckSquare, IconSparkles, IconSearch, IconChevronDown, SourceIcon, IconArrowRight } from '../components/Icons'

const BAND_COLOR: Record<string, string> = {
  high: 'var(--high)', medium: 'var(--mid)', low: 'var(--low)',
}
const BAND_BG: Record<string, string> = {
  high: 'var(--high-bg)', medium: 'var(--mid-bg)', low: 'var(--low-bg)',
}

export default function TasksPage() {
  const { token } = useAuth()
  const [tasks, setTasks] = useState<PersonalTask[]>([])
  const [selected, setSelected] = useState<PersonalTask | null>(null)
  const [loading, setLoading] = useState(true)
  const [urgencyFilter, setUrgencyFilter] = useState('All')
  const [search, setSearch] = useState('')
  const [triggering, setTriggering] = useState(false)
  const [notice, setNotice] = useState('')

  const fetchTasks = useCallback(async () => {
    if (!token) return
    try {
      const data = await api.listTasks(token)
      setTasks(data.tasks)
      if (selected) {
        const refreshed = data.tasks.find(t => t.id === selected.id)
        if (refreshed) setSelected(refreshed)
      }
    } catch { /* ignore */ }
    finally { setLoading(false) }
  }, [token, selected?.id]) // eslint-disable-line

  useEffect(() => {
    fetchTasks()
    const id = setInterval(fetchTasks, 60_000)
    return () => clearInterval(id)
  }, [fetchTasks])

  async function handleStatus(taskId: string, status: string) {
    if (!token) return
    try {
      const updated = await api.patchTask(token, taskId, status)
      setTasks(prev => prev.map(t => t.id === taskId ? updated : t))
      if (selected?.id === taskId) setSelected(updated)
    } catch { /* ignore */ }
  }

  async function triggerExtraction() {
    if (!token) return
    setTriggering(true)
    setNotice('')
    try {
      await api.triggerPersonalExtraction(token)
      setNotice('Extraction triggered — tasks will appear in a few seconds.')
      setTimeout(fetchTasks, 4000)
    } catch { setNotice('Trigger failed. Please try again.') }
    finally { setTriggering(false) }
  }

  const openTasks = tasks.filter(t => t.status === 'open')
  const filtered = openTasks.filter(t => {
    if (urgencyFilter !== 'All' && t.urgency_band !== urgencyFilter.toLowerCase()) return false
    if (search && !t.description.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  return (
    <Layout rightPanel={<TaskContextPanel task={selected} onStatusChange={handleStatus} />}>
      <div style={{ padding: '20px 24px', height: '100%', display: 'flex', flexDirection: 'column' }}>
        {/* Header */}
        <div style={{ marginBottom: 16, flexShrink: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 4 }}>
            <h1 style={{ margin: 0, fontSize: '1.6rem', fontWeight: 800, color: 'var(--purple)' }}>
              My Tasks
            </h1>
            <span style={{
              display: 'flex', alignItems: 'center', gap: 5,
              fontSize: '0.72rem', fontWeight: 700, padding: '4px 10px', borderRadius: 6,
              background: 'var(--purple-bg)', color: 'var(--purple)',
              border: '1px solid var(--purple-bg)',
            }}>
              <IconSparkles size={12} /> Personal Intelligence
            </span>
            <div style={{ marginLeft: 'auto' }}>
              <button onClick={triggerExtraction} disabled={triggering} style={{
                padding: '7px 14px', background: 'var(--accent-bg)',
                border: '1px solid var(--accent)', borderRadius: 8,
                color: 'var(--accent)', fontSize: '0.8rem', fontWeight: 600,
                cursor: triggering ? 'not-allowed' : 'pointer',
              }}>
                {triggering ? 'Running…' : 'Extract Tasks'}
              </button>
            </div>
          </div>
          <p style={{ margin: 0, color: 'var(--text-2)', fontSize: '0.85rem' }}>
            AI-extracted action items enriched with relevant company knowledge.
          </p>
          {notice && (
            <div style={{
              marginTop: 8, padding: '8px 12px', borderRadius: 8,
              background: 'var(--accent-bg)', border: '1px solid var(--accent)',
              color: 'var(--accent)', fontSize: '0.8rem',
            }}>
              {notice}
            </div>
          )}
        </div>

        {/* Filters */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14,
          flexShrink: 0, flexWrap: 'wrap',
        }}>
          <FilterDropdown label="Urgency" value={urgencyFilter}
            options={['All', 'High', 'Medium', 'Low']}
            onChange={setUrgencyFilter} />
          <FilterDropdown label="Source" value="All"
            options={['All', 'Slack', 'Email']} onChange={() => {}} />
          <FilterDropdown label="Date Range" value="All Time"
            options={['All Time', 'Today', 'This Week']} onChange={() => {}} />
          <div style={{
            flex: 1, minWidth: 200, display: 'flex', alignItems: 'center', gap: 7,
            background: 'var(--bg-input)', border: '1px solid var(--border)',
            borderRadius: 8, padding: '0 10px', height: 34,
          }}>
            <IconSearch size={14} color="var(--text-3)" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search tasks..."
              style={{ flex: 1, background: 'none', border: 'none', fontSize: '0.83rem', color: 'var(--text-1)' }}
            />
          </div>
        </div>

        {/* Table */}
        <div style={{ flex: 1, overflowY: 'auto', borderRadius: 10, border: '1px solid var(--border)', background: 'var(--bg-card)' }}>
          {loading ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-3)', fontSize: '0.88rem' }}>
              Loading tasks…
            </div>
          ) : filtered.length === 0 ? (
            <div style={{ padding: '3rem', textAlign: 'center' }}>
              <IconCheckSquare size={32} color="var(--text-3)" />
              <p style={{ color: 'var(--text-2)', marginTop: 12, fontSize: '0.88rem' }}>
                {openTasks.length === 0
                  ? 'No tasks yet. Click "Extract Tasks" to run the PIL pipeline.'
                  : 'No tasks match your filters.'}
              </p>
            </div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)' }}>
                  {['#', 'Task', 'Urgency', 'Extracted From', 'Context', 'Actions'].map(h => (
                    <th key={h} style={{
                      padding: '10px 14px', textAlign: 'left',
                      fontSize: '0.73rem', fontWeight: 600, color: 'var(--text-3)',
                      letterSpacing: '0.04em', whiteSpace: 'nowrap',
                    }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map((task, i) => (
                  <tr
                    key={task.id}
                    className={`task-row${selected?.id === task.id ? ' sel' : ''}`}
                    onClick={() => setSelected(task)}
                  >
                    <td style={{ padding: '12px 14px', fontSize: '0.82rem', color: 'var(--text-3)', width: 36 }}>
                      {i + 1}
                    </td>
                    <td style={{ padding: '12px 14px', maxWidth: 260 }}>
                      <div style={{ fontWeight: 600, fontSize: '0.85rem', color: 'var(--text-1)', marginBottom: 2 }}>
                        {task.description.length > 65 ? task.description.slice(0, 65) + '…' : task.description}
                      </div>
                      {task.sender && (
                        <div style={{ fontSize: '0.72rem', color: 'var(--text-2)' }}>
                          From {task.sender}
                        </div>
                      )}
                    </td>
                    <td style={{ padding: '12px 14px', whiteSpace: 'nowrap' }}>
                      {task.urgency_band && (
                        <span style={{
                          fontSize: '0.72rem', fontWeight: 700, padding: '3px 9px', borderRadius: 5,
                          color: BAND_COLOR[task.urgency_band], background: BAND_BG[task.urgency_band],
                          textTransform: 'capitalize',
                        }}>
                          {task.urgency_band.charAt(0).toUpperCase() + task.urgency_band.slice(1)}
                        </span>
                      )}
                    </td>
                    <td style={{ padding: '12px 14px', whiteSpace: 'nowrap' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <SourceIcon type={task.source_reference.includes('slack') ? 'slack' : 'email'} />
                        <div>
                          <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-1)' }}>
                            {task.source_reference.includes('slack') ? 'Slack' : 'Email'}
                          </div>
                          <div style={{ fontSize: '0.69rem', color: 'var(--text-2)' }}>
                            {task.source_label ?? task.source_reference}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td style={{ padding: '12px 14px', fontSize: '0.78rem', color: 'var(--text-2)', maxWidth: 180 }}>
                      {task.context_bundle && task.context_bundle.length > 0
                        ? `${task.context_bundle.length} knowledge chunk${task.context_bundle.length !== 1 ? 's' : ''} attached`
                        : task.context_bundle === null ? 'Bundling…' : 'No context found'}
                    </td>
                    <td style={{ padding: '12px 14px', whiteSpace: 'nowrap' }} onClick={e => e.stopPropagation()}>
                      <button
                        onClick={() => setSelected(task)}
                        style={{
                          padding: '5px 12px', background: 'var(--purple-bg)',
                          border: '1px solid var(--purple)', borderRadius: 6,
                          color: 'var(--purple)', fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer',
                        }}
                      >
                        View Context
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Pagination footer */}
        {filtered.length > 0 && (
          <div style={{
            flexShrink: 0, paddingTop: 10, display: 'flex', alignItems: 'center',
            justifyContent: 'space-between', fontSize: '0.78rem', color: 'var(--text-2)',
          }}>
            <span>Showing 1–{filtered.length} of {filtered.length} tasks</span>
          </div>
        )}
      </div>
    </Layout>
  )
}

function FilterDropdown({ label, value, options, onChange }: {
  label: string; value: string; options: string[]; onChange: (v: string) => void
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <label style={{ fontSize: '0.7rem', color: 'var(--text-3)', fontWeight: 600 }}>{label}</label>
      <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
        <select
          value={value}
          onChange={e => onChange(e.target.value)}
          style={{
            padding: '5px 28px 5px 10px', background: 'var(--bg-card)',
            border: '1px solid var(--border)', borderRadius: 7,
            color: 'var(--text-1)', fontSize: '0.82rem', cursor: 'pointer',
            appearance: 'none', minWidth: 90,
          }}
        >
          {options.map(o => <option key={o} value={o}>{o}</option>)}
        </select>
        <span style={{ position: 'absolute', right: 8, pointerEvents: 'none', color: 'var(--text-3)' }}>
          <IconChevronDown size={12} />
        </span>
      </div>
    </div>
  )
}

function TaskContextPanel({ task, onStatusChange }: {
  task: PersonalTask | null
  onStatusChange: (id: string, status: string) => void
}) {
  if (!task) {
    return (
      <div style={{
        padding: '20px 16px', display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center', height: '100%', gap: 10,
      }}>
        <IconCheckSquare size={28} color="var(--text-3)" />
        <p style={{ fontSize: '0.82rem', color: 'var(--text-3)', textAlign: 'center', margin: 0 }}>
          Select a task to see related knowledge
        </p>
      </div>
    )
  }

  const chunks: SearchResult[] = task.context_bundle ?? []

  return (
    <div style={{ padding: '16px 14px', display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Panel header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 8 }}>
        <div>
          <div style={{ fontWeight: 700, fontSize: '0.9rem', color: 'var(--text-1)', marginBottom: 2 }}>
            Task Context
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-2)' }}>Related knowledge from Company Brain.</div>
        </div>
        <span style={{
          display: 'flex', alignItems: 'center', gap: 4, fontSize: '0.65rem', fontWeight: 600,
          color: 'var(--accent)', background: 'var(--accent-bg)', padding: '3px 8px', borderRadius: 5, whiteSpace: 'nowrap',
        }}>
          <IconSparkles size={10} /> Auto-attached
        </span>
      </div>

      {/* Knowledge chunks */}
      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 12 }}>
        {task.context_bundle === null ? (
          <p style={{ fontSize: '0.8rem', color: 'var(--text-2)', fontStyle: 'italic', padding: '8px 0' }}>
            Bundling context… check back in a moment.
          </p>
        ) : chunks.length === 0 ? (
          <p style={{ fontSize: '0.8rem', color: 'var(--text-2)', fontStyle: 'italic', padding: '8px 0' }}>
            No relevant context found.
          </p>
        ) : chunks.map((chunk, i) => (
          <div key={i} style={{
            background: 'var(--bg-card)', border: '1px solid var(--border)',
            borderRadius: 8, padding: '10px 12px',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <SourceIcon type={chunk.source_type} />
                <span style={{ fontSize: '0.72rem', fontWeight: 600, color: 'var(--text-1)' }}>
                  {chunk.source_id.split('/').pop() ?? chunk.source_id}
                </span>
              </div>
              <span style={{
                fontSize: '0.7rem', fontWeight: 700,
                color: chunk.combined_score > 0.8 ? 'var(--green)' : chunk.combined_score > 0.6 ? 'var(--mid)' : 'var(--text-2)',
                background: 'var(--bg-card2)', padding: '2px 6px', borderRadius: 4,
              }}>
                {Math.round(chunk.combined_score * 100)}%
              </span>
            </div>
            <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--text-2)', lineHeight: 1.5 }}>
              "{chunk.text.length > 220 ? chunk.text.slice(0, 220) + '…' : chunk.text}"
            </p>
          </div>
        ))}

        {/* Why this task */}
        {task.urgency_band && (
          <div style={{
            background: 'var(--purple-bg)', border: '1px solid var(--purple-bg)',
            borderRadius: 8, padding: '10px 12px',
          }}>
            <div style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--purple)', marginBottom: 4, display: 'flex', alignItems: 'center', gap: 5 }}>
              <IconSparkles size={12} /> Why this task?
            </div>
            <p style={{ margin: 0, fontSize: '0.78rem', color: 'var(--text-2)', lineHeight: 1.45 }}>
              Extracted and marked <strong style={{ color: BAND_COLOR[task.urgency_band] }}>
                {task.urgency_band}
              </strong> urgency (score {task.urgency_score?.toFixed(1)}).
              {task.sender ? ` From: ${task.sender}.` : ''}
              {task.deadline ? ` Deadline: ${new Date(task.deadline).toLocaleDateString()}.` : ''}
            </p>
          </div>
        )}
      </div>

      {/* Actions */}
      {task.status === 'open' && (
        <div style={{ flexShrink: 0, display: 'flex', flexDirection: 'column', gap: 6 }}>
          <button
            onClick={() => onStatusChange(task.id, 'complete')}
            style={{
              padding: '9px 0', background: 'var(--purple)', color: '#fff',
              border: 'none', borderRadius: 8, fontSize: '0.83rem', fontWeight: 600,
              cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
            }}
          >
            ✓ Mark Done
          </button>
          <div style={{ display: 'flex', gap: 6 }}>
            <button onClick={() => onStatusChange(task.id, 'snoozed')} className="btn-ghost" style={{
              flex: 1, padding: '7px 0', background: 'none', border: '1px solid var(--border)',
              borderRadius: 8, fontSize: '0.78rem', color: 'var(--text-2)', cursor: 'pointer',
            }}>
              Snooze
            </button>
            <button onClick={() => onStatusChange(task.id, 'dismissed')} className="btn-ghost" style={{
              flex: 1, padding: '7px 0', background: 'none', border: '1px solid var(--border)',
              borderRadius: 8, fontSize: '0.78rem', color: 'var(--text-2)', cursor: 'pointer',
            }}>
              Dismiss
            </button>
          </div>
          <button className="btn-ghost" style={{
            padding: '7px 0', background: 'none', border: '1px solid var(--border)',
            borderRadius: 8, fontSize: '0.78rem', color: 'var(--text-2)', cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5,
          }}>
            Open in Company Brain <IconArrowRight size={12} />
          </button>
        </div>
      )}
    </div>
  )
}
