import { useAuth } from '../contexts/AuthContext'
import { useTheme } from '../contexts/ThemeContext'
import Layout from '../components/Layout'
import RightPanel from '../components/RightPanel'
import { IconSun, IconMoon } from '../components/Icons'

export default function SettingsPage() {
  const { email, role, logout } = useAuth()
  const { theme, toggle } = useTheme()

  return (
    <Layout rightPanel={<RightPanel />}>
      <div style={{ padding: '20px 24px', maxWidth: 640 }}>
        <div style={{ marginBottom: 24 }}>
          <h1 style={{ margin: '0 0 4px', fontSize: '1.6rem', fontWeight: 800, color: 'var(--accent)' }}>Settings</h1>
          <p style={{ margin: 0, color: 'var(--text-2)', fontSize: '0.88rem' }}>
            Manage your account and application preferences.
          </p>
        </div>

        {/* Appearance */}
        <Section title="Appearance">
          <SettingRow
            label="Theme"
            description="Choose between dark and light mode"
            action={
              <div style={{ display: 'flex', gap: 8 }}>
                <ThemeBtn active={theme === 'dark'} onClick={() => theme !== 'dark' && toggle()} icon={<IconMoon size={15} />} label="Dark" />
                <ThemeBtn active={theme === 'light'} onClick={() => theme !== 'light' && toggle()} icon={<IconSun size={15} />} label="Light" />
              </div>
            }
          />
        </Section>

        {/* Account */}
        <Section title="Account">
          <SettingRow
            label="Email"
            description={email ?? '—'}
            action={null}
          />
          <SettingRow
            label="Role"
            description={
              <span style={{
                fontSize: '0.75rem', fontWeight: 700, padding: '2px 9px', borderRadius: 5,
                background: role === 'admin' ? 'var(--purple-bg)' : 'var(--accent-bg)',
                color: role === 'admin' ? 'var(--purple)' : 'var(--accent)',
              }}>
                {role ?? 'user'}
              </span>
            }
            action={null}
          />
          <SettingRow
            label="Sign out"
            description="Sign out of your current session"
            action={
              <button onClick={logout} style={{
                padding: '7px 16px', background: 'none',
                border: '1px solid var(--red)', borderRadius: 8,
                color: 'var(--red)', fontSize: '0.82rem', fontWeight: 600, cursor: 'pointer',
              }}>
                Sign out
              </button>
            }
          />
        </Section>

        {/* About */}
        <Section title="About">
          <div style={{
            display: 'flex', gap: 14, padding: '14px 16px',
            background: 'var(--bg-card2)', borderRadius: 8, border: '1px solid var(--border)',
          }}>
            <div style={{
              width: 40, height: 40, borderRadius: 10, background: 'var(--accent-bg)',
              display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
            }}>
              <span style={{ fontWeight: 800, fontSize: '0.8rem', color: 'var(--accent)' }}>CB</span>
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: '0.88rem', color: 'var(--text-1)', marginBottom: 3 }}>Company Brain</div>
              <div style={{ fontSize: '0.77rem', color: 'var(--text-2)', lineHeight: 1.5 }}>
                AI-powered organizational knowledge assistant. Ingests Slack, email, Notion, and more.
                Extracts knowledge, detects conflicts, and surfaces personal action items using the
                Personal Intelligence Layer.
              </div>
              <div style={{ marginTop: 6, fontSize: '0.72rem', color: 'var(--text-3)' }}>
                Stack: FastAPI · Celery · PostgreSQL + pgvector · React · Claude (Anthropic)
              </div>
            </div>
          </div>
        </Section>
      </div>
    </Layout>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 24 }}>
      <h3 style={{ margin: '0 0 10px', fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
        {title}
      </h3>
      <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
        {children}
      </div>
    </div>
  )
}

function SettingRow({ label, description, action }: {
  label: string
  description: React.ReactNode
  action: React.ReactNode
}) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '14px 16px', borderBottom: '1px solid var(--border)',
    }}
      className="row-hover"
    >
      <div>
        <div style={{ fontWeight: 600, fontSize: '0.85rem', color: 'var(--text-1)', marginBottom: 2 }}>{label}</div>
        {typeof description === 'string'
          ? <div style={{ fontSize: '0.78rem', color: 'var(--text-2)' }}>{description}</div>
          : description}
      </div>
      {action && <div style={{ flexShrink: 0, marginLeft: 16 }}>{action}</div>}
    </div>
  )
}

function ThemeBtn({ active, onClick, icon, label }: {
  active: boolean; onClick: () => void; icon: React.ReactNode; label: string
}) {
  return (
    <button onClick={onClick} style={{
      display: 'flex', alignItems: 'center', gap: 6,
      padding: '7px 14px', borderRadius: 8, cursor: 'pointer',
      border: active ? '1.5px solid var(--accent)' : '1px solid var(--border)',
      background: active ? 'var(--accent-bg)' : 'var(--bg-card2)',
      color: active ? 'var(--accent)' : 'var(--text-2)',
      fontSize: '0.82rem', fontWeight: active ? 700 : 500,
      transition: 'all 0.15s',
    }}>
      {icon} {label}
    </button>
  )
}
