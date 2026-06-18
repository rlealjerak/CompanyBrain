import { useState, FormEvent } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { api, SearchResult } from '../api/client'
import Layout from '../components/Layout'
import RightPanel from '../components/RightPanel'
import { IconSearch, SourceIcon } from '../components/Icons'

export default function SearchPage() {
  const { token } = useAuth()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)

  async function doSearch(e: FormEvent) {
    e.preventDefault()
    if (!query.trim() || !token) return
    setLoading(true)
    setSearched(true)
    try {
      const data = await api.search(query, token, 10)
      setResults(data.results)
    } catch { setResults([]) }
    finally { setLoading(false) }
  }

  return (
    <Layout rightPanel={<RightPanel />}>
      <div style={{ padding: '20px 24px' }}>
        <div style={{ marginBottom: 20 }}>
          <h1 style={{ margin: '0 0 4px', fontSize: '1.6rem', fontWeight: 800, color: 'var(--accent)' }}>Search</h1>
          <p style={{ margin: 0, color: 'var(--text-2)', fontSize: '0.88rem' }}>
            Semantic search across all indexed company knowledge.
          </p>
        </div>

        <form onSubmit={doSearch} style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
          <div style={{
            flex: 1, display: 'flex', alignItems: 'center', gap: 8,
            background: 'var(--bg-card)', border: '1px solid var(--border-s)',
            borderRadius: 10, padding: '0 14px', height: 46,
          }}>
            <IconSearch size={16} color="var(--text-3)" />
            <input
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="Search company knowledge semantically…"
              autoFocus
              style={{ flex: 1, background: 'none', border: 'none', fontSize: '0.92rem', color: 'var(--text-1)' }}
            />
          </div>
          <button type="submit" disabled={loading || !query.trim()} style={{
            padding: '0 22px', background: 'var(--accent)', color: '#000',
            border: 'none', borderRadius: 10, fontSize: '0.88rem', fontWeight: 700,
            cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.7 : 1,
          }}>
            {loading ? '…' : 'Search'}
          </button>
        </form>

        {results.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-2)', marginBottom: 2 }}>
              {results.length} results for "{query}"
            </div>
            {results.map((r, i) => (
              <div key={i} className="card-hover" style={{
                background: 'var(--bg-card)', border: '1px solid var(--border)',
                borderRadius: 10, padding: '14px 16px',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <SourceIcon type={r.source_type} />
                    <span style={{ fontWeight: 700, fontSize: '0.85rem', color: 'var(--text-1)' }}>
                      {r.source_id}
                    </span>
                    <span style={{
                      fontSize: '0.7rem', fontWeight: 600, padding: '1px 7px', borderRadius: 4,
                      background: 'var(--bg-card2)', color: 'var(--text-2)',
                      textTransform: 'capitalize',
                    }}>
                      {r.source_type}
                    </span>
                  </div>
                  <span style={{
                    fontSize: '0.78rem', fontWeight: 700,
                    color: r.combined_score > 0.8 ? 'var(--green)' : r.combined_score > 0.6 ? 'var(--mid)' : 'var(--text-2)',
                  }}>
                    {Math.round(r.combined_score * 100)}% match
                  </span>
                </div>
                <p style={{ margin: 0, fontSize: '0.83rem', color: 'var(--text-2)', lineHeight: 1.6 }}>
                  {r.text.length > 300 ? r.text.slice(0, 300) + '…' : r.text}
                </p>
              </div>
            ))}
          </div>
        )}

        {searched && results.length === 0 && !loading && (
          <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-3)', fontSize: '0.88rem' }}>
            No results found for "{query}"
          </div>
        )}

        {!searched && (
          <div style={{ textAlign: 'center', padding: '4rem', color: 'var(--text-3)' }}>
            <IconSearch size={36} color="var(--text-3)" />
            <p style={{ marginTop: 12, fontSize: '0.88rem' }}>
              Enter a query to search across all company knowledge
            </p>
          </div>
        )}
      </div>
    </Layout>
  )
}
