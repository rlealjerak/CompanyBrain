import { useState, FormEvent, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, ApiError } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import { useTheme } from '../contexts/ThemeContext'
import { IconBrain, IconSun, IconMoon } from '../components/Icons'

export default function LoginPage() {
  const { login } = useAuth()
  const { theme, toggle } = useTheme()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    document.documentElement.className = theme
  }, [theme])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { access_token } = await api.login(email, password)
      const user = await api.me(access_token)
      login(access_token, user.email, user.role)
      navigate('/')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'var(--bg-base)', position: 'relative',
    }}>
      {/* Theme toggle */}
      <button
        onClick={toggle}
        style={{
          position: 'absolute', top: 16, right: 16,
          background: 'var(--bg-card)', border: '1px solid var(--border)',
          borderRadius: 8, width: 36, height: 36, cursor: 'pointer',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: 'var(--text-2)',
        }}
      >
        {theme === 'dark' ? <IconSun size={16} /> : <IconMoon size={16} />}
      </button>

      <div style={{
        background: 'var(--bg-card)', border: '1px solid var(--border)',
        borderRadius: 16, padding: '2.5rem', width: 380,
        boxShadow: '0 8px 32px var(--shadow)',
      }}>
        {/* Logo */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginBottom: 28 }}>
          <IconBrain size={56} />
          <h1 style={{ margin: '12px 0 4px', fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-1)' }}>
            Company Brain
          </h1>
          <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-2)' }}>
            Organizational knowledge assistant
          </p>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-2)', marginBottom: 5 }}>
              Email
            </label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="you@company.com"
              required
              autoFocus
              style={{
                width: '100%', padding: '9px 12px',
                background: 'var(--bg-input)', border: '1px solid var(--border)',
                borderRadius: 8, fontSize: '0.9rem', color: 'var(--text-1)',
                transition: 'border-color 0.15s',
              }}
            />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-2)', marginBottom: 5 }}>
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              style={{
                width: '100%', padding: '9px 12px',
                background: 'var(--bg-input)', border: '1px solid var(--border)',
                borderRadius: 8, fontSize: '0.9rem', color: 'var(--text-1)',
                transition: 'border-color 0.15s',
              }}
            />
          </div>

          {error && (
            <p style={{
              margin: 0, padding: '8px 12px', borderRadius: 6,
              background: 'var(--red-bg)', color: 'var(--red)',
              fontSize: '0.82rem', border: '1px solid var(--high-bg)',
            }}>
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            style={{
              marginTop: 4, padding: '10px 0',
              background: 'var(--purple)', color: '#fff', border: 'none',
              borderRadius: 8, fontSize: '0.9rem', fontWeight: 600,
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.7 : 1,
              transition: 'opacity 0.15s',
            }}
          >
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <p style={{ textAlign: 'center', marginTop: 20, fontSize: '0.75rem', color: 'var(--text-3)' }}>
          Demo: roberto.leal@acme.com / user123
        </p>
      </div>
    </div>
  )
}
