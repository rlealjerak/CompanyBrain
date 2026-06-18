import { Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { ThemeProvider } from './contexts/ThemeContext'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import SourcesPage from './pages/SourcesPage'
import KnowledgePage from './pages/KnowledgePage'
import SearchPage from './pages/SearchPage'
import TasksPage from './pages/TasksPage'
import SettingsPage from './pages/SettingsPage'

function RequireAuth({ children }: { children: JSX.Element }) {
  const { token } = useAuth()
  return token ? children : <Navigate to="/login" replace />
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<RequireAuth><DashboardPage /></RequireAuth>} />
      <Route path="/sources" element={<RequireAuth><SourcesPage /></RequireAuth>} />
      <Route path="/knowledge" element={<RequireAuth><KnowledgePage /></RequireAuth>} />
      <Route path="/search" element={<RequireAuth><SearchPage /></RequireAuth>} />
      <Route path="/tasks" element={<RequireAuth><TasksPage /></RequireAuth>} />
      <Route path="/settings" element={<RequireAuth><SettingsPage /></RequireAuth>} />
      {/* Legacy redirects */}
      <Route path="/chat" element={<Navigate to="/" replace />} />
      <Route path="/dashboard" element={<Navigate to="/tasks" replace />} />
      <Route path="/ingest" element={<Navigate to="/sources" replace />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </ThemeProvider>
  )
}
