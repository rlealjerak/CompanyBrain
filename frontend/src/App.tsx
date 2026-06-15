import { Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import LoginPage from './pages/LoginPage'
import ChatPage from './pages/ChatPage'
import IngestionPage from './pages/IngestionPage'

function RequireAuth({ children }: { children: JSX.Element }) {
  const { token } = useAuth()
  return token ? children : <Navigate to="/login" replace />
}

function RequireAdmin({ children }: { children: JSX.Element }) {
  const { token, role } = useAuth()
  if (!token) return <Navigate to="/login" replace />
  if (role !== 'admin') return <Navigate to="/chat" replace />
  return children
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/chat"
        element={<RequireAuth><ChatPage /></RequireAuth>}
      />
      <Route
        path="/ingest"
        element={<RequireAdmin><IngestionPage /></RequireAdmin>}
      />
      <Route path="*" element={<Navigate to="/chat" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  )
}
