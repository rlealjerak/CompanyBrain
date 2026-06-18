import { useState, ReactNode } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useTheme } from '../contexts/ThemeContext'
import {
  IconGrid, IconDatabase, IconBook, IconSearch,
  IconCheckSquare, IconSettings, IconBell, IconSun, IconMoon,
  IconChevronLeft, IconChevronRight, IconBrain, IconChevronDown,
} from './Icons'

interface NavItem {
  label: string
  path: string
  icon: ReactNode
  dot?: boolean
}

const NAV: NavItem[] = [
  { label: 'Dashboard', path: '/', icon: <IconGrid /> },
  { label: 'Sources', path: '/sources', icon: <IconDatabase /> },
  { label: 'Knowledge', path: '/knowledge', icon: <IconBook /> },
  { label: 'Search', path: '/search', icon: <IconSearch /> },
  { label: 'My Tasks', path: '/tasks', icon: <IconCheckSquare />, dot: true },
  { label: 'Settings', path: '/settings', icon: <IconSettings /> },
]

interface LayoutProps {
  children: ReactNode
  rightPanel?: ReactNode
}

export default function Layout({ children, rightPanel }: LayoutProps) {
  const { email, logout } = useAuth()
  const { theme, toggle } = useTheme()
  const navigate = useNavigate()
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(false)

  const sideW = collapsed ? 64 : 240

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', background: 'var(--bg-base)' }}>
      {/* ── Sidebar ── */}
      <aside style={{
        width: sideW, minWidth: sideW, height: '100vh',
        background: 'var(--bg-side)', borderRight: '1px solid var(--border)',
        display: 'flex', flexDirection: 'column',
        transition: 'width 0.2s ease, min-width 0.2s ease',
        overflow: 'hidden', flexShrink: 0, position: 'relative', zIndex: 10,
      }}>
        {/* Logo */}
        <div style={{
          height: 64, display: 'flex', alignItems: 'center',
          padding: collapsed ? '0 13px' : '0 16px',
          borderBottom: '1px solid var(--border)', gap: 10, flexShrink: 0,
          overflow: 'hidden',
        }}>
          <IconBrain size={32} />
          {!collapsed && (
            <span style={{ fontWeight: 700, fontSize: '1.05rem', color: 'var(--text-1)', whiteSpace: 'nowrap' }}>
              Company Brain
            </span>
          )}
        </div>

        {/* Nav */}
        <nav style={{ flex: 1, padding: '12px 8px', display: 'flex', flexDirection: 'column', gap: 2, overflowY: 'auto', overflowX: 'hidden' }}>
          {NAV.map(item => {
            const active = location.pathname === item.path ||
              (item.path !== '/' && location.pathname.startsWith(item.path))
            return (
              <button
                key={item.path}
                className={`nav-item${active ? ' active' : ''}`}
                onClick={() => navigate(item.path)}
                title={collapsed ? item.label : undefined}
                style={{ justifyContent: collapsed ? 'center' : 'flex-start', padding: collapsed ? '9px 0' : '9px 12px' }}
              >
                <span style={{ flexShrink: 0, position: 'relative', display: 'flex' }}>
                  {item.icon}
                  {item.dot && !active && (
                    <span style={{
                      position: 'absolute', top: -2, right: -2,
                      width: 6, height: 6, borderRadius: '50%',
                      background: 'var(--accent)',
                    }} />
                  )}
                </span>
                {!collapsed && <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{item.label}</span>}
              </button>
            )
          })}
        </nav>

        {/* Bottom branding */}
        {!collapsed && (
          <div style={{
            margin: '0 8px 8px', padding: '12px', borderRadius: 10,
            background: 'var(--bg-card)', border: '1px solid var(--border)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
              <div style={{
                width: 28, height: 28, borderRadius: 8,
                background: 'var(--accent-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--accent)' }}>CB</span>
              </div>
              <span style={{ fontWeight: 600, fontSize: '0.82rem', color: 'var(--text-1)' }}>Company Brain</span>
            </div>
            <p style={{ margin: 0, fontSize: '0.73rem', color: 'var(--text-2)', lineHeight: 1.4 }}>
              AI-powered insights from all your company knowledge.
            </p>
          </div>
        )}

        {/* Collapse button */}
        <button
          className="btn-ghost"
          onClick={() => setCollapsed(c => !c)}
          style={{
            display: 'flex', alignItems: 'center', gap: 8,
            padding: '10px 16px', margin: '0 0 8px 0',
            background: 'none', border: 'none', cursor: 'pointer',
            color: 'var(--text-2)', fontSize: '0.8rem', fontWeight: 500,
            borderRadius: 8, width: '100%',
            justifyContent: collapsed ? 'center' : 'flex-start',
          }}
        >
          {collapsed ? <IconChevronRight size={16} /> : <><IconChevronLeft size={16} /><span>Collapse</span></>}
        </button>
      </aside>

      {/* ── Right side (header + content) ── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minWidth: 0 }}>
        {/* Header */}
        <header style={{
          height: 56, background: 'var(--bg-side)', borderBottom: '1px solid var(--border)',
          display: 'flex', alignItems: 'center', gap: 12, padding: '0 16px',
          flexShrink: 0,
        }}>
          {/* Search */}
          <div style={{
            flex: 1, maxWidth: 480, display: 'flex', alignItems: 'center', gap: 8,
            background: 'var(--bg-input)', border: '1px solid var(--border)', borderRadius: 8,
            padding: '0 12px', height: 36,
          }}>
            <IconSearch size={15} color="var(--text-3)" />
            <input
              placeholder="Ask anything about your company..."
              style={{
                flex: 1, background: 'none', border: 'none', outline: 'none',
                fontSize: '0.85rem', color: 'var(--text-1)',
              }}
              onKeyDown={e => {
                if (e.key === 'Enter') {
                  const q = (e.target as HTMLInputElement).value.trim()
                  if (q) { navigate(`/?q=${encodeURIComponent(q)}`);(e.target as HTMLInputElement).value = '' }
                }
              }}
            />
            <span style={{ fontSize: '0.7rem', color: 'var(--text-3)', background: 'var(--border-s)', padding: '2px 5px', borderRadius: 4, whiteSpace: 'nowrap' }}>⌘ K</span>
          </div>

          {/* All Sources */}
          <button className="btn-ghost" style={{
            display: 'flex', alignItems: 'center', gap: 6,
            padding: '6px 12px', borderRadius: 8, border: '1px solid var(--border)',
            background: 'none', color: 'var(--text-2)', fontSize: '0.83rem', cursor: 'pointer',
            whiteSpace: 'nowrap',
          }}>
            <IconDatabase size={14} />
            All Sources
            <IconChevronDown size={13} />
          </button>

          <div style={{ flex: 1 }} />

          {/* Theme toggle */}
          <button className="btn-ghost" onClick={toggle} style={{
            width: 34, height: 34, borderRadius: 8, border: 'none',
            background: 'none', cursor: 'pointer', color: 'var(--text-2)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            {theme === 'dark' ? <IconSun size={16} /> : <IconMoon size={16} />}
          </button>

          {/* Notifications */}
          <button className="btn-ghost" style={{
            position: 'relative', width: 34, height: 34, borderRadius: 8,
            border: 'none', background: 'none', cursor: 'pointer', color: 'var(--text-2)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <IconBell size={17} />
            <span style={{
              position: 'absolute', top: 4, right: 4,
              width: 16, height: 16, borderRadius: '50%',
              background: 'var(--accent)', fontSize: '0.6rem', fontWeight: 700,
              color: '#000', display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>3</span>
          </button>

          {/* User */}
          <button className="btn-ghost" style={{
            display: 'flex', alignItems: 'center', gap: 8,
            padding: '4px 8px', borderRadius: 8, border: 'none',
            background: 'none', cursor: 'pointer',
          }}>
            <div style={{
              width: 28, height: 28, borderRadius: '50%',
              background: 'var(--accent-bg)', border: '1.5px solid var(--accent)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: '0.7rem', fontWeight: 700, color: 'var(--accent)',
            }}>
              {(email?.[0] ?? 'U').toUpperCase()}
            </div>
            <div style={{ textAlign: 'left' }}>
              <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-1)', lineHeight: 1.2 }}>
                {email?.split('@')[0].split('.').map(w => w[0]?.toUpperCase() + w.slice(1)).join(' ') ?? 'User'}
              </div>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-2)', lineHeight: 1.2 }}>Operations</div>
            </div>
            <IconChevronDown size={13} color="var(--text-3)" />
          </button>

          <button onClick={logout} className="btn-ghost" style={{
            padding: '4px 10px', borderRadius: 6, border: '1px solid var(--border)',
            background: 'none', cursor: 'pointer', fontSize: '0.77rem', color: 'var(--text-2)',
          }}>
            Sign out
          </button>
        </header>

        {/* Content row */}
        <div style={{ flex: 1, display: 'flex', overflow: 'hidden', minHeight: 0 }}>
          <main style={{ flex: 1, overflowY: 'auto', minWidth: 0 }}>
            {children}
          </main>
          {rightPanel !== undefined && (
            <aside style={{
              width: 'var(--right-w)', minWidth: 'var(--right-w)',
              borderLeft: '1px solid var(--border)',
              background: 'var(--bg-side)', overflowY: 'auto',
              flexShrink: 0,
            }}>
              {rightPanel}
            </aside>
          )}
        </div>
      </div>
    </div>
  )
}
