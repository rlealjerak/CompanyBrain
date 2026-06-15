import { useState, FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, ApiError } from '../api/client'
import { useAuth } from '../contexts/AuthContext'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { access_token } = await api.login(email, password)
      const user = await api.me(access_token)
      login(access_token, user.email, user.role)
      navigate('/chat')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={styles.page}>
      <div style={styles.card}>
        <h1 style={styles.title}>Company Brain</h1>
        <p style={styles.subtitle}>Organizational knowledge assistant</p>
        <form onSubmit={handleSubmit} style={styles.form}>
          <input
            style={styles.input}
            type="email"
            placeholder="Email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            required
            autoFocus
          />
          <input
            style={styles.input}
            type="password"
            placeholder="Password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
          />
          {error && <p style={styles.error}>{error}</p>}
          <button style={styles.button} type="submit" disabled={loading}>
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  page: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: '#f5f5f5',
    fontFamily: 'system-ui, sans-serif',
  },
  card: {
    background: '#fff',
    borderRadius: 8,
    padding: '2.5rem',
    width: 360,
    boxShadow: '0 2px 12px rgba(0,0,0,0.1)',
  },
  title: { margin: 0, fontSize: '1.6rem', color: '#111' },
  subtitle: { marginTop: 6, marginBottom: 24, color: '#666', fontSize: '0.9rem' },
  form: { display: 'flex', flexDirection: 'column', gap: 12 },
  input: {
    padding: '10px 12px',
    border: '1px solid #ddd',
    borderRadius: 6,
    fontSize: '0.95rem',
    outline: 'none',
  },
  button: {
    padding: '10px 0',
    background: '#2563eb',
    color: '#fff',
    border: 'none',
    borderRadius: 6,
    fontSize: '0.95rem',
    cursor: 'pointer',
    marginTop: 4,
  },
  error: { color: '#dc2626', fontSize: '0.875rem', margin: 0 },
}
