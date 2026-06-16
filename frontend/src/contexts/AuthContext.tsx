import { createContext, useContext, useState, useCallback, ReactNode } from 'react'

interface AuthState {
  token: string | null
  email: string | null
  role: string | null
}

interface AuthContextValue extends AuthState {
  login: (token: string, email: string, role: string) => void
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

const STORAGE_KEY = 'cb_token'

function loadStored(): AuthState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return { token: null, email: null, role: null }
    return JSON.parse(raw)
  } catch {
    return { token: null, email: null, role: null }
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [auth, setAuth] = useState<AuthState>(loadStored)

  const login = useCallback((token: string, email: string, role: string) => {
    const state = { token, email, role }
    setAuth(state)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  }, [])

  const logout = useCallback(() => {
    setAuth({ token: null, email: null, role: null })
    localStorage.removeItem(STORAGE_KEY)
  }, [])

  return (
    <AuthContext.Provider value={{ ...auth, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
