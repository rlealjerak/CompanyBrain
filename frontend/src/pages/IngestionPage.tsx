import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { api, IngestionJob, ApiError } from '../api/client'

const STATUS_COLOR: Record<string, string> = {
  success: '#16a34a',
  running: '#2563eb',
  retrying: '#d97706',
  failed: '#dc2626',
}

export default function IngestionPage() {
  const { token, email, role, logout } = useAuth()
  const [jobs, setJobs] = useState<IngestionJob[]>([])
  const [loading, setLoading] = useState(true)
  const [triggering, setTriggering] = useState(false)
  const [notice, setNotice] = useState('')

  const fetchJobs = useCallback(async () => {
    if (!token) return
    try {
      const data = await api.listJobs(token)
      setJobs(data.jobs)
    } catch {
      // silently ignore poll errors
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => {
    fetchJobs()
    const id = setInterval(fetchJobs, 10_000)
    return () => clearInterval(id)
  }, [fetchJobs])

  async function triggerAll() {
    if (!token) return
    setTriggering(true)
    setNotice('')
    try {
      await api.triggerIngest(token)
      setNotice('Sync triggered — jobs will appear below within a few seconds.')
      setTimeout(fetchJobs, 2000)
    } catch (err) {
      setNotice(err instanceof ApiError ? err.message : 'Trigger failed')
    } finally {
      setTriggering(false)
    }
  }

  // Group jobs into latest-per-source for the sources table
  const latestBySource: Record<string, IngestionJob> = {}
  for (const job of jobs) {
    if (!latestBySource[job.source_id]) latestBySource[job.source_id] = job
  }
  const sources = Object.values(latestBySource)

  return (
    <div style={styles.page}>
      <header style={styles.header}>
        <span style={styles.logo}>Company Brain</span>
        <nav style={styles.nav}>
          <a href="/chat" style={styles.navLink}>Chat</a>
          <span style={styles.userLabel}>{email}</span>
          <button onClick={logout} style={styles.logoutBtn}>Sign out</button>
        </nav>
      </header>

      <main style={styles.main}>
        <div style={styles.topRow}>
          <h2 style={styles.heading}>Ingestion Dashboard</h2>
          {role === 'admin' && (
            <button style={styles.triggerBtn} onClick={triggerAll} disabled={triggering}>
              {triggering ? 'Triggering…' : 'Sync All Sources'}
            </button>
          )}
        </div>
        {notice && <p style={styles.notice}>{notice}</p>}

        <h3 style={styles.sectionHeading}>Data Sources</h3>
        {loading ? (
          <p style={styles.muted}>Loading…</p>
        ) : sources.length === 0 ? (
          <p style={styles.muted}>No ingestion jobs yet. Trigger a sync to get started.</p>
        ) : (
          <table style={styles.table}>
            <thead>
              <tr>
                {['Source', 'Last sync', 'Status', 'Attempts'].map(h => (
                  <th key={h} style={styles.th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sources.map(job => (
                <tr key={job.source_id} style={styles.tr}>
                  <td style={styles.td}>{job.source_id}</td>
                  <td style={styles.td}>{job.locked_at ? new Date(job.locked_at).toLocaleString() : '—'}</td>
                  <td style={styles.td}>
                    <span style={{ ...styles.badge, color: STATUS_COLOR[job.status] ?? '#374151' }}>
                      {job.status}
                    </span>
                  </td>
                  <td style={styles.td}>{job.attempt_number}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        <h3 style={{ ...styles.sectionHeading, marginTop: '2rem' }}>Job History</h3>
        {jobs.length === 0 ? (
          <p style={styles.muted}>No jobs found.</p>
        ) : (
          <table style={styles.table}>
            <thead>
              <tr>
                {['Source', 'Status', 'Started', 'Attempts', 'Error'].map(h => (
                  <th key={h} style={styles.th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {jobs.map(job => (
                <tr key={job.id} style={styles.tr}>
                  <td style={styles.td}>{job.source_id}</td>
                  <td style={styles.td}>
                    <span style={{ ...styles.badge, color: STATUS_COLOR[job.status] ?? '#374151' }}>
                      {job.status}
                    </span>
                  </td>
                  <td style={styles.td}>{job.locked_at ? new Date(job.locked_at).toLocaleString() : '—'}</td>
                  <td style={styles.td}>{job.attempt_number}</td>
                  <td style={{ ...styles.td, color: '#dc2626', fontSize: '0.8rem' }}>
                    {job.error_message ?? '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </main>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  page: { minHeight: '100vh', fontFamily: 'system-ui, sans-serif', background: '#fafafa' },
  header: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 1.5rem', height: 52, background: '#fff', borderBottom: '1px solid #e5e7eb' },
  logo: { fontWeight: 700, fontSize: '1.1rem', color: '#111' },
  nav: { display: 'flex', alignItems: 'center', gap: 16 },
  navLink: { color: '#2563eb', textDecoration: 'none', fontSize: '0.9rem' },
  userLabel: { color: '#666', fontSize: '0.85rem' },
  logoutBtn: { background: 'none', border: 'none', color: '#666', cursor: 'pointer', fontSize: '0.85rem' },
  main: { maxWidth: 1100, margin: '0 auto', padding: '2rem 1.5rem' },
  topRow: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 },
  heading: { margin: 0, fontSize: '1.4rem' },
  sectionHeading: { fontSize: '1rem', color: '#374151', marginBottom: 12 },
  triggerBtn: { padding: '8px 16px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: '0.9rem' },
  notice: { background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: 6, padding: '0.6rem 1rem', color: '#1d4ed8', fontSize: '0.875rem', marginBottom: 16 },
  muted: { color: '#9ca3af', fontSize: '0.9rem' },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem', background: '#fff', borderRadius: 8, overflow: 'hidden', boxShadow: '0 1px 4px rgba(0,0,0,0.06)' },
  th: { textAlign: 'left', padding: '10px 14px', background: '#f9fafb', borderBottom: '1px solid #e5e7eb', fontWeight: 600, color: '#374151' },
  tr: { borderBottom: '1px solid #f3f4f6' },
  td: { padding: '10px 14px', color: '#111', verticalAlign: 'middle' },
  badge: { fontWeight: 600, fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.03em' },
}
