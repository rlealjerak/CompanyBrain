import { Routes, Route } from 'react-router-dom'

export default function App() {
  return (
    <Routes>
      <Route
        path="*"
        element={
          <div style={{ fontFamily: 'sans-serif', padding: '2rem' }}>
            <h1>Company Brain</h1>
            <p>Phase 1 — infrastructure running. UI pages added in Phase 4.</p>
          </div>
        }
      />
    </Routes>
  )
}
