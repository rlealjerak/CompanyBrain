import { useState, useRef, useEffect, FormEvent } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { openChatStream, Source } from '../api/client'

interface Message {
  id: number
  role: 'user' | 'assistant'
  content: string
  sources?: Source[]
  streaming?: boolean
}

let msgCounter = 0

export default function ChatPage() {
  const { token, email, logout } = useAuth()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  function sendMessage(e: FormEvent) {
    e.preventDefault()
    const query = input.trim()
    if (!query || busy) return

    setInput('')
    setBusy(true)

    const userMsg: Message = { id: ++msgCounter, role: 'user', content: query }
    const assistantId = ++msgCounter
    const assistantMsg: Message = {
      id: assistantId,
      role: 'assistant',
      content: '',
      sources: [],
      streaming: true,
    }
    setMessages(prev => [...prev, userMsg, assistantMsg])

    const ws = openChatStream(token!)
    ws.onopen = () => {
      ws.send(JSON.stringify({ token, query }))
    }
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'token') {
        setMessages(prev =>
          prev.map(m =>
            m.id === assistantId ? { ...m, content: m.content + data.content } : m
          )
        )
      } else if (data.type === 'done') {
        setMessages(prev =>
          prev.map(m =>
            m.id === assistantId ? { ...m, sources: data.sources, streaming: false } : m
          )
        )
        setBusy(false)
        ws.close()
      } else if (data.type === 'error') {
        setMessages(prev =>
          prev.map(m =>
            m.id === assistantId
              ? { ...m, content: `Error: ${data.content}`, streaming: false }
              : m
          )
        )
        setBusy(false)
        ws.close()
      }
    }
    ws.onerror = () => {
      setMessages(prev =>
        prev.map(m =>
          m.id === assistantId
            ? { ...m, content: 'Connection error. Please try again.', streaming: false }
            : m
        )
      )
      setBusy(false)
    }
  }

  return (
    <div style={styles.page}>
      <header style={styles.header}>
        <span style={styles.logo}>Company Brain</span>
        <nav style={styles.nav}>
          <a href="/dashboard" style={styles.navLink}>Dashboard</a>
          <a href="/ingest" style={styles.navLink}>Ingestion</a>
          <span style={styles.userLabel}>{email}</span>
          <button onClick={logout} style={styles.logoutBtn}>Sign out</button>
        </nav>
      </header>

      <div style={styles.thread}>
        {messages.length === 0 && (
          <div style={styles.empty}>
            Ask anything about company policies, tickets, or Slack threads.
          </div>
        )}
        {messages.map(msg => (
          <div key={msg.id} style={msg.role === 'user' ? styles.userBubble : styles.aiBubble}>
            <div style={styles.bubbleLabel}>{msg.role === 'user' ? 'You' : 'Brain'}</div>
            <div style={styles.bubbleText}>
              {msg.content}
              {msg.streaming && <span style={styles.cursor}>▌</span>}
            </div>
            {!msg.streaming && msg.sources && msg.sources.length > 0 && (
              <div style={styles.sources}>
                <div style={styles.sourcesLabel}>Sources</div>
                {msg.sources.map((s, i) => (
                  <div key={i} style={styles.sourceItem}>
                    <span style={styles.sourceName}>{s.source_id}</span>
                    <span style={styles.sourceType}>{s.source_type}</span>
                    <p style={styles.sourceExcerpt}>{s.excerpt}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <form onSubmit={sendMessage} style={styles.inputRow}>
        <input
          style={styles.textInput}
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Ask a question…"
          disabled={busy}
          autoFocus
        />
        <button style={styles.sendBtn} type="submit" disabled={busy || !input.trim()}>
          {busy ? '…' : 'Send'}
        </button>
      </form>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  page: { display: 'flex', flexDirection: 'column', height: '100vh', fontFamily: 'system-ui, sans-serif', background: '#fafafa' },
  header: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 1.5rem', height: 52, background: '#fff', borderBottom: '1px solid #e5e7eb' },
  logo: { fontWeight: 700, fontSize: '1.1rem', color: '#111' },
  nav: { display: 'flex', alignItems: 'center', gap: 16 },
  navLink: { color: '#2563eb', textDecoration: 'none', fontSize: '0.9rem' },
  userLabel: { color: '#666', fontSize: '0.85rem' },
  logoutBtn: { background: 'none', border: 'none', color: '#666', cursor: 'pointer', fontSize: '0.85rem' },
  thread: { flex: 1, overflowY: 'auto', padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: 20 },
  empty: { color: '#9ca3af', textAlign: 'center', marginTop: '4rem', fontSize: '0.95rem' },
  userBubble: { alignSelf: 'flex-end', maxWidth: 640, background: '#2563eb', color: '#fff', borderRadius: 12, padding: '0.75rem 1rem' },
  aiBubble: { alignSelf: 'flex-start', maxWidth: 720, background: '#fff', border: '1px solid #e5e7eb', borderRadius: 12, padding: '0.75rem 1rem' },
  bubbleLabel: { fontSize: '0.75rem', fontWeight: 600, marginBottom: 4, opacity: 0.7, textTransform: 'uppercase', letterSpacing: '0.05em' },
  bubbleText: { lineHeight: 1.6, whiteSpace: 'pre-wrap' },
  cursor: { animation: 'blink 1s step-end infinite' },
  sources: { marginTop: 12, paddingTop: 12, borderTop: '1px solid #e5e7eb' },
  sourcesLabel: { fontSize: '0.75rem', fontWeight: 600, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 },
  sourceItem: { background: '#f9fafb', borderRadius: 6, padding: '0.5rem 0.75rem', marginBottom: 6 },
  sourceName: { fontWeight: 600, fontSize: '0.85rem', color: '#111', marginRight: 8 },
  sourceType: { fontSize: '0.75rem', color: '#6b7280', background: '#e5e7eb', borderRadius: 4, padding: '1px 6px' },
  sourceExcerpt: { margin: '4px 0 0', fontSize: '0.8rem', color: '#4b5563', lineHeight: 1.5 },
  inputRow: { display: 'flex', gap: 8, padding: '1rem 1.5rem', background: '#fff', borderTop: '1px solid #e5e7eb' },
  textInput: { flex: 1, padding: '10px 14px', border: '1px solid #d1d5db', borderRadius: 8, fontSize: '0.95rem', outline: 'none' },
  sendBtn: { padding: '10px 20px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: '0.95rem', fontWeight: 600 },
}
