import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { api, IngestionJob } from '../api/client'
import Layout from '../components/Layout'
import RightPanel from '../components/RightPanel'
import { IconPlus, IconRefresh, IconClock, IconDoc, SourceIcon } from '../components/Icons'

interface SourceDef {
  id: string
  name: string
  type: string
  docCount: number
  status: 'connected' | 'syncing' | 'error'
  lastSynced: string
  progress: number
  autoSync: boolean
}

const MOCK_SOURCES: SourceDef[] = [
  { id: 'slack', name: 'Slack', type: 'slack', docCount: 8, status: 'connected', lastSynced: 'Just now', progress: 100, autoSync: true },
  { id: 'email', name: 'Email', type: 'email', docCount: 6, status: 'connected', lastSynced: '2 min ago', progress: 100, autoSync: true },
]

export default function SourcesPage() {
  const { token, role } = useAuth()
  const [jobs, setJobs] = useState<IngestionJob[]>([])
  const [triggering, setTriggering] = useState(false)
  const [notice, setNotice] = useState('')
  const [docTotal] = useState(50)
  const isAdmin = role === 'admin'

  useEffect(() => {
    if (!token) return
    api.listJobs(token, 20).then(d => setJobs(d.jobs)).catch(() => {})
  }, [token])

  async function triggerSync() {
    if (!token) return
    setTriggering(true)
    setNotice('')
    try {
      await api.triggerIngest(token)
      setNotice('Ingestion triggered — jobs will appear below.')
      setTimeout(() => api.listJobs(token, 20).then(d => setJobs(d.jobs)).catch(() => {}), 3000)
    } catch { setNotice('Trigger failed. Admin access required.') }
    finally { setTriggering(false) }
  }

  const statusBadge = (s: SourceDef['status']) => {
    const map = {
      connected: { label: 'Connected', color: 'var(--green)', bg: 'var(--green-bg)' },
      syncing: { label: 'Syncing…', color: 'var(--mid)', bg: 'var(--mid-bg)' },
      error: { label: 'Auth expired', color: 'var(--orange)', bg: 'var(--orange-bg)' },
    }
    const s2 = map[s]
    return (
      <span style={{
        fontSize: '0.7rem', fontWeight: 700, padding: '3px 9px', borderRadius: 5,
        color: s2.color, background: s2.bg, border: `1px solid ${s2.color}22`,
      }}>
        {s2.label}
      </span>
    )
  }

  const jobStatusColor = (s: string) => {
    if (s === 'complete') return 'var(--green)'
    if (s === 'running') return 'var(--accent)'
    if (s === 'failed') return 'var(--red)'
    return 'var(--text-2)'
  }

  return (
    <Layout rightPanel={<RightPanel />}>
      <div style={{ padding: '20px 24px' }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 20 }}>
          <div>
            <h1 style={{ margin: '0 0 4px', fontSize: '1.6rem', fontWeight: 800, color: 'var(--accent)' }}>
              Sources
            </h1>
            <p style={{ margin: 0, color: 'var(--text-2)', fontSize: '0.88rem' }}>
              Connect and manage your company data sources.
            </p>
          </div>
          {isAdmin && (
            <button onClick={triggerSync} disabled={triggering} style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '8px 16px', background: 'var(--accent)', color: '#000',
              border: 'none', borderRadius: 8, fontSize: '0.85rem', fontWeight: 700,
              cursor: triggering ? 'not-allowed' : 'pointer', opacity: triggering ? 0.7 : 1,
            }}>
              <IconRefresh size={15} /> {triggering ? 'Syncing…' : 'Sync Now'}
            </button>
          )}
        </div>

        {notice && (
          <div style={{
            marginBottom: 16, padding: '8px 14px', borderRadius: 8,
            background: 'var(--accent-bg)', border: '1px solid var(--accent)',
            color: 'var(--accent)', fontSize: '0.82rem',
          }}>
            {notice}
          </div>
        )}

        {/* Stats row */}
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 20,
          background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 12, padding: '16px 20px',
        }}>
          <StatItem icon={<SourceIcon type="slack" />} value={MOCK_SOURCES.length.toString()} label="Total sources connected" />
          <StatItem icon={<IconDoc size={18} color="var(--accent)" />} value={docTotal.toString() + '+'} label="Total documents indexed" />
          <StatItem icon={<IconClock size={18} color="var(--mid)" />} value="Auto" label="Last full sync time" />
        </div>

        {/* Source cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12, marginBottom: 24 }}>
          {MOCK_SOURCES.map(src => (
            <div key={src.id} style={{
              background: 'var(--bg-card)', border: '1px solid var(--border)',
              borderRadius: 12, padding: '16px', display: 'flex', flexDirection: 'column', gap: 12,
            }}>
              {/* Card header */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <SourceIcon type={src.type} />
                  <span style={{ fontWeight: 700, fontSize: '0.95rem', color: 'var(--text-1)' }}>{src.name}</span>
                </div>
                {statusBadge(src.status)}
              </div>

              {/* Meta */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.78rem', color: 'var(--text-2)' }}>
                  Last synced: {src.lastSynced}
                </span>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontWeight: 700, fontSize: '1rem', color: 'var(--text-1)' }}>{src.docCount}</div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-2)' }}>Documents</div>
                </div>
              </div>

              {/* Progress */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5, fontSize: '0.72rem', color: 'var(--text-2)' }}>
                  <span>Last ingestion run</span>
                  <span style={{ fontWeight: 700, color: 'var(--text-1)' }}>{src.progress}%</span>
                </div>
                <div className="progress-track">
                  <div className="progress-fill" style={{
                    width: `${src.progress}%`,
                    background: src.status === 'error' ? 'var(--mid)' : 'var(--accent)',
                  }} />
                </div>
              </div>

              {/* Auto-sync */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '0.78rem', color: 'var(--text-2)' }}>Auto-sync</span>
                <label className="toggle-wrap">
                  <input type="checkbox" defaultChecked={src.autoSync} onChange={() => {}} />
                  <div className="toggle-track" />
                </label>
              </div>
            </div>
          ))}

          {/* Add Source placeholder */}
          <button className="btn-ghost" style={{
            background: 'var(--bg-card)', border: '1px dashed var(--border-s)',
            borderRadius: 12, padding: '16px', cursor: 'pointer',
            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
            gap: 8, minHeight: 180,
          }}>
            <div style={{
              width: 36, height: 36, borderRadius: '50%',
              background: 'var(--bg-hover)', display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <IconPlus size={18} color="var(--text-2)" />
            </div>
            <span style={{ fontSize: '0.83rem', color: 'var(--text-2)', fontWeight: 600 }}>Add Source</span>
          </button>
        </div>

        {/* Recent ingestion jobs */}
        {jobs.length > 0 && (
          <div>
            <h3 style={{ margin: '0 0 12px', fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-1)' }}>
              Recent Ingestion Jobs
            </h3>
            <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border)' }}>
                    {['Source', 'Status', 'Attempt', 'Error'].map(h => (
                      <th key={h} style={{
                        padding: '9px 14px', textAlign: 'left',
                        fontSize: '0.72rem', fontWeight: 600, color: 'var(--text-3)', letterSpacing: '0.04em',
                      }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {jobs.slice(0, 10).map(job => (
                    <tr key={job.id} className="row-hover" style={{ borderBottom: '1px solid var(--border)' }}>
                      <td style={{ padding: '9px 14px', fontSize: '0.8rem', color: 'var(--text-1)', fontFamily: 'monospace', maxWidth: 200 }}>
                        {job.source_id.length > 40 ? '…' + job.source_id.slice(-40) : job.source_id}
                      </td>
                      <td style={{ padding: '9px 14px' }}>
                        <span style={{
                          fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase',
                          color: jobStatusColor(job.status),
                          background: `${jobStatusColor(job.status)}22`,
                          padding: '2px 8px', borderRadius: 4,
                        }}>
                          {job.status}
                        </span>
                      </td>
                      <td style={{ padding: '9px 14px', fontSize: '0.8rem', color: 'var(--text-2)' }}>
                        #{job.attempt_number}
                      </td>
                      <td style={{ padding: '9px 14px', fontSize: '0.75rem', color: 'var(--red)', maxWidth: 200 }}>
                        {job.error_message ? job.error_message.slice(0, 60) + (job.error_message.length > 60 ? '…' : '') : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </Layout>
  )
}

function StatItem({ icon, value, label }: { icon: React.ReactNode; value: string; label: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
      <div style={{
        width: 40, height: 40, borderRadius: 10, background: 'var(--bg-card2)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
      }}>
        {icon}
      </div>
      <div>
        <div style={{ fontWeight: 700, fontSize: '1.1rem', color: 'var(--text-1)' }}>{value}</div>
        <div style={{ fontSize: '0.72rem', color: 'var(--text-2)' }}>{label}</div>
      </div>
    </div>
  )
}
