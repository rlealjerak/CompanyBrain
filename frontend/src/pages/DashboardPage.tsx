import { useState, useRef, useEffect, FormEvent } from 'react'
import { useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { openChatStream, Source, api, SearchResult } from '../api/client'
import Layout from '../components/Layout'
import RightPanel from '../components/RightPanel'
import { IconSearch, IconSparkles, IconArrowRight, SourceIcon } from '../components/Icons'

interface Message {
  id: number
  role: 'user' | 'assistant'
  content: string
  sources?: Source[]
  streaming?: boolean
}

let msgId = 0

export default function DashboardPage() {
  const { token } = useAuth()
  const location = useLocation()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [knowledgeItems, setKnowledgeItems] = useState<SearchResult[]>([])
  const bottomRef = useRef<HTMLDivElement>(null)

  // Pre-load knowledge on mount
  useEffect(() => {
    if (!token) return
    api.search('company policy refund escalation support', token, 3)
      .then(d => setKnowledgeItems(d.results))
      .catch(() => {})
  }, [token])

  // Auto-submit query from global search bar
  useEffect(() => {
    const params = new URLSearchParams(location.search)
    const q = params.get('q')
    if (q && !busy) { setInput(q); setTimeout(() => sendQuery(q), 0) }
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  function sendQuery(query: string) {
    if (!query.trim() || busy) return
    setInput('')
    setBusy(true)

    const userId = ++msgId
    const aiId = ++msgId
    setMessages(prev => [
      ...prev,
      { id: userId, role: 'user', content: query },
      { id: aiId, role: 'assistant', content: '', sources: [], streaming: true },
    ])

    const ws = openChatStream(token!)
    ws.onopen = () => ws.send(JSON.stringify({ token, query }))
    ws.onmessage = event => {
      const data = JSON.parse(event.data)
      if (data.type === 'token') {
        setMessages(prev => prev.map(m =>
          m.id === aiId ? { ...m, content: m.content + data.content } : m
        ))
      } else if (data.type === 'done') {
        setMessages(prev => prev.map(m =>
          m.id === aiId ? { ...m, sources: data.sources, streaming: false } : m
        ))
        // Refresh knowledge panel with results relevant to this query
        if (token) {
          api.search(query, token, 3)
            .then(d => setKnowledgeItems(d.results))
            .catch(() => {})
        }
        setBusy(false)
        ws.close()
      } else if (data.type === 'error') {
        setMessages(prev => prev.map(m =>
          m.id === aiId ? { ...m, content: `Error: ${data.content}`, streaming: false } : m
        ))
        setBusy(false)
        ws.close()
      }
    }
    ws.onerror = () => {
      setMessages(prev => prev.map(m =>
        m.id === aiId ? { ...m, content: 'Connection error. Please try again.', streaming: false } : m
      ))
      setBusy(false)
    }
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    sendQuery(input.trim())
  }


  return (
    <Layout rightPanel={<RightPanel />}>
      <div style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: '20px 24px 0' }}>

        {/* ── Header ── */}
        <div style={{ marginBottom: 14, flexShrink: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
            <h1 style={{ margin: 0, fontSize: '1.6rem', fontWeight: 800, color: 'var(--accent)' }}>
              Company Brain
            </h1>
            <span style={{
              fontSize: '0.68rem', fontWeight: 700, padding: '2px 8px', borderRadius: 6,
              background: 'var(--accent-bg)', color: 'var(--accent)', border: '1px solid var(--accent)',
              letterSpacing: '0.05em',
            }}>AI</span>
          </div>
          <p style={{ margin: 0, color: 'var(--text-2)', fontSize: '0.88rem' }}>
            Ask anything. Get answers from your company knowledge.
          </p>
        </div>

        {/* ── Chat card (scrollable, grows to fill space) ── */}
        <div style={{
          flex: 1, minHeight: 0,
          background: 'var(--bg-card)', border: '1px solid var(--border)',
          borderRadius: 12, marginBottom: 16, overflow: 'hidden',
          display: 'flex', flexDirection: 'column',
        }}>
          <div style={{ flex: 1, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: 16 }}>
            {messages.length === 0 ? (
              <EmptyState onSuggest={sendQuery} />
            ) : (
              messages.map(msg => <MessageBubble key={msg.id} msg={msg} />)
            )}
            <div ref={bottomRef} />
          </div>
        </div>

        {/* ── Top relevant knowledge ── */}
        {knowledgeItems.length > 0 && (
          <div style={{ flexShrink: 0, marginBottom: 14 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
              <span style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-1)' }}>Top relevant knowledge</span>
              <button onClick={() => window.location.href = '/knowledge'} style={{
                background: 'none', border: 'none', color: 'var(--accent)',
                fontSize: '0.78rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4,
              }}>
                View all <IconArrowRight size={13} />
              </button>
            </div>
            <div style={{ display: 'flex', gap: 10, overflowX: 'auto', paddingBottom: 4 }}>
              {knowledgeItems.map((item, i) => (
                <KnowledgeCard key={i} item={item} />
              ))}
            </div>
          </div>
        )}

        {/* ── Input bar (always at the bottom) ── */}
        <div style={{ flexShrink: 0, borderTop: '1px solid var(--border)', paddingTop: 14, paddingBottom: 16 }}>
          <form onSubmit={handleSubmit} style={{ display: 'flex', gap: 8 }}>
            <div style={{
              flex: 1, display: 'flex', alignItems: 'center', gap: 8,
              background: 'var(--bg-input)', border: '1px solid var(--border-s)',
              borderRadius: 10, padding: '0 14px', height: 44,
            }}>
              <IconSearch size={16} color="var(--text-3)" />
              <input
                value={input}
                onChange={e => setInput(e.target.value)}
                placeholder="Ask a question about company policies, tickets, or Slack threads…"
                disabled={busy}
                autoFocus
                style={{
                  flex: 1, background: 'none', border: 'none', outline: 'none',
                  fontSize: '0.9rem', color: 'var(--text-1)',
                }}
              />
            </div>
            <button
              type="submit"
              disabled={busy || !input.trim()}
              style={{
                padding: '0 20px', background: 'var(--purple)', color: '#fff',
                border: 'none', borderRadius: 10, fontSize: '0.88rem',
                fontWeight: 600, cursor: busy ? 'not-allowed' : 'pointer',
                opacity: busy || !input.trim() ? 0.6 : 1,
                whiteSpace: 'nowrap',
              }}
            >
              {busy ? '…' : 'Ask'}
            </button>
          </form>
        </div>
      </div>
    </Layout>
  )
}

function EmptyState({ onSuggest }: { onSuggest: (q: string) => void }) {
  const suggestions = [
    'What is our refund policy?',
    'Who handles VIP customer escalations?',
    'What are the SLA requirements for priority tickets?',
  ]
  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 16, padding: '2rem' }}>
      <div style={{
        width: 56, height: 56, borderRadius: 16, background: 'var(--accent-bg)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <IconSparkles size={24} color="var(--accent)" />
      </div>
      <div style={{ textAlign: 'center' }}>
        <h3 style={{ margin: '0 0 6px', fontSize: '1rem', fontWeight: 700, color: 'var(--text-1)' }}>
          Ask Company Brain
        </h3>
        <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-2)' }}>
          Get instant answers with source citations from your company knowledge.
        </p>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6, width: '100%', maxWidth: 420 }}>
        {suggestions.map(s => (
          <button key={s} onClick={() => onSuggest(s)} className="card-hover" style={{
            padding: '9px 14px', background: 'var(--bg-card)', border: '1px solid var(--border)',
            borderRadius: 8, color: 'var(--text-2)', fontSize: '0.83rem', cursor: 'pointer',
            textAlign: 'left',
          }}>
            {s}
          </button>
        ))}
      </div>
    </div>
  )
}

function MessageBubble({ msg }: { msg: Message }) {
  if (msg.role === 'user') {
    return (
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
        <div style={{
          maxWidth: 580, background: 'var(--bg-card)', border: '1px solid var(--border-s)',
          borderRadius: 12, padding: '12px 16px',
        }}>
          <div style={{ fontSize: '0.88rem', color: 'var(--text-1)', lineHeight: 1.55 }}>
            {msg.content}
          </div>
        </div>
        <div style={{
          width: 32, height: 32, borderRadius: '50%', background: 'var(--purple-bg)',
          border: '1.5px solid var(--purple)', display: 'flex', alignItems: 'center',
          justifyContent: 'center', fontSize: '0.75rem', fontWeight: 700, color: 'var(--purple)',
          flexShrink: 0, marginTop: 2,
        }}>U</div>
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', gap: 10, maxWidth: 680 }}>
      <div style={{
        width: 32, height: 32, borderRadius: '50%', background: 'var(--accent-bg)',
        border: '1.5px solid var(--accent)', display: 'flex', alignItems: 'center',
        justifyContent: 'center', flexShrink: 0, marginTop: 2,
      }}>
        <span style={{ fontSize: '0.65rem', fontWeight: 800, color: 'var(--accent)' }}>CB</span>
      </div>
      <div style={{
        flex: 1, background: 'var(--bg-card)', border: '1px solid var(--border-s)',
        borderRadius: 12, padding: '14px 16px',
      }}>
        <div style={{ fontSize: '0.88rem', color: 'var(--text-1)', lineHeight: 1.65, whiteSpace: 'pre-wrap' }}>
          {msg.content}
          {msg.streaming && <span className="blink" style={{ color: 'var(--accent)' }}>▌</span>}
        </div>

        {!msg.streaming && msg.sources && msg.sources.length > 0 && (
          <div style={{ marginTop: 14, paddingTop: 14, borderTop: '1px solid var(--border)' }}>
            <div style={{
              fontSize: '0.75rem', fontWeight: 700, color: 'var(--accent)', marginBottom: 8,
              letterSpacing: '0.04em',
            }}>
              Relevant knowledge excerpt
            </div>
            {msg.sources.slice(0, 1).map((s, i) => (
              <div key={i} style={{
                background: 'var(--bg-card2)', borderLeft: '2px solid var(--accent)',
                borderRadius: '0 8px 8px 0', padding: '10px 12px', marginBottom: 10,
                fontSize: '0.82rem', color: 'var(--text-2)', lineHeight: 1.55, fontStyle: 'italic',
              }}>
                "{s.excerpt}"
              </div>
            ))}
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              background: 'var(--bg-card2)', borderRadius: 8, padding: '8px 12px',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <SourceIcon type={msg.sources[0]?.source_type ?? ''} />
                <span style={{ fontSize: '0.78rem', color: 'var(--text-2)' }}>
                  {msg.sources[0]?.source_id}
                </span>
              </div>
              {msg.sources[0]?.similarity != null && (
                <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--green)' }}>
                  {Math.round(msg.sources[0].similarity * 100)}%
                </span>
              )}
            </div>

            {/* Action buttons */}
            <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
              <ActionBtn label="✦ Summarize" />
              <ActionBtn label="↗ Open Source" />
              <button style={{
                padding: '6px 14px', background: 'var(--purple)', color: '#fff',
                border: 'none', borderRadius: 8, fontSize: '0.78rem', fontWeight: 600,
                cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5,
              }}>
                ✓ Create Task
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function ActionBtn({ label }: { label: string }) {
  return (
    <button className="btn-ghost" style={{
      padding: '6px 14px', background: 'none', border: '1px solid var(--border-s)',
      borderRadius: 8, fontSize: '0.78rem', color: 'var(--text-2)', cursor: 'pointer',
    }}>
      {label}
    </button>
  )
}

function KnowledgeCard({ item }: { item: SearchResult }) {
  const name = item.source_id.split('/').pop() ?? item.source_id
  const score = Math.round(item.combined_score * 100)
  return (
    <div className="card-hover" style={{
      minWidth: 220, maxWidth: 260, padding: '12px 14px',
      background: 'var(--bg-card)', border: '1px solid var(--border)',
      borderRadius: 10, flexShrink: 0,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
        <SourceIcon type={item.source_type} />
        <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-1)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {name}
        </span>
      </div>
      <p style={{ margin: '0 0 8px', fontSize: '0.77rem', color: 'var(--text-2)', lineHeight: 1.45 }}>
        {item.text.length > 110 ? item.text.slice(0, 110) + '…' : item.text}
      </p>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{
          fontSize: '0.68rem', padding: '2px 7px', borderRadius: 4,
          background: 'var(--accent-bg)', color: 'var(--accent)', fontWeight: 600,
          textTransform: 'capitalize',
        }}>
          {item.source_type}
        </span>
        <span style={{ fontSize: '0.72rem', color: 'var(--green)', fontWeight: 700 }}>
          {score}%
        </span>
      </div>
    </div>
  )
}
