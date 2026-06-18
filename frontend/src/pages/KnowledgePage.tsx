import { useState } from 'react'
import Layout from '../components/Layout'
import RightPanel from '../components/RightPanel'
import { IconSearch, IconChevronDown, IconAlertTriangle, IconCheck, SourceIcon } from '../components/Icons'

interface KnowledgeItem {
  id: string
  statement: string
  sourceType: string
  sourceChannel: string
  dateExtracted: string
  confidence: number
  status: 'conflict' | 'verified' | 'unverified'
  conflictDetail?: { older: string; olderSource: string; newer: string; newerSource: string }
}

const MOCK_KNOWLEDGE: KnowledgeItem[] = [
  {
    id: '1',
    statement: 'Refunds over $500 require Operations approval before processing',
    sourceType: 'slack',
    sourceChannel: '#ops-team',
    dateExtracted: 'Jun 3, 2025',
    confidence: 94,
    status: 'conflict',
    conflictDetail: {
      older: 'Refunds up to $750 may be processed without Operations approval',
      olderSource: 'Customer Support Handbook · Jun 1, 2025',
      newer: 'Refunds over $500 require Operations approval',
      newerSource: '#ops-team · Jun 3, 2025',
    },
  },
  {
    id: '2',
    statement: 'Customer Handbook states refunds up to $750 may be processed without Operations approval',
    sourceType: 'notion',
    sourceChannel: 'Customer Support Handbook',
    dateExtracted: 'Jun 1, 2025',
    confidence: 95,
    status: 'conflict',
  },
  {
    id: '3',
    statement: 'Enterprise pricing exceptions above 12% require Finance sign-off',
    sourceType: 'email',
    sourceChannel: 'Finance Approval Note',
    dateExtracted: 'Jun 2, 2025',
    confidence: 91,
    status: 'verified',
  },
  {
    id: '4',
    statement: 'Priority tickets must receive first response within 2 hours',
    sourceType: 'zendesk',
    sourceChannel: 'Support SLA Rules',
    dateExtracted: 'May 28, 2025',
    confidence: 96,
    status: 'verified',
  },
  {
    id: '5',
    statement: 'Escalate warehouse delivery issues after 24 hours of no carrier update',
    sourceType: 'notion',
    sourceChannel: 'Fulfillment Playbook',
    dateExtracted: 'May 29, 2025',
    confidence: 89,
    status: 'verified',
  },
  {
    id: '6',
    statement: 'VIP support requests should be routed to Tier 2 immediately',
    sourceType: 'slack',
    sourceChannel: '#support-leads',
    dateExtracted: 'May 30, 2025',
    confidence: 84,
    status: 'unverified',
  },
  {
    id: '7',
    statement: 'Discounts over 20% on wholesale accounts require Sales Director approval',
    sourceType: 'email',
    sourceChannel: 'Pricing Exceptions Policy',
    dateExtracted: 'Jun 4, 2025',
    confidence: 92,
    status: 'verified',
  },
  {
    id: '8',
    statement: 'Chargeback cases must be acknowledged within 1 business day',
    sourceType: 'notion',
    sourceChannel: 'Risk Operations SOP',
    dateExtracted: 'Jun 5, 2025',
    confidence: 90,
    status: 'verified',
  },
]

export default function KnowledgePage() {
  const [items] = useState<KnowledgeItem[]>(MOCK_KNOWLEDGE)
  const [expanded, setExpanded] = useState<string | null>(null)
  const [sourceFilter, setSourceFilter] = useState('All Sources')
  const [statusFilter, setStatusFilter] = useState('All')
  const [confidenceThreshold, setConfidenceThreshold] = useState(70)
  const [liveSearch, setLiveSearch] = useState('')

  const filtered = items.filter(item => {
    if (sourceFilter !== 'All Sources' && item.sourceType !== sourceFilter.toLowerCase()) return false
    if (statusFilter !== 'All' && item.status !== statusFilter.toLowerCase()) return false
    if (item.confidence < confidenceThreshold) return false
    if (liveSearch && !item.statement.toLowerCase().includes(liveSearch.toLowerCase())) return false
    return true
  })

  const statusBadge = (status: KnowledgeItem['status']) => {
    if (status === 'conflict') return (
      <span style={{
        display: 'flex', alignItems: 'center', gap: 4, fontSize: '0.72rem', fontWeight: 700,
        color: 'var(--red)', background: 'var(--red-bg)', padding: '3px 9px', borderRadius: 5,
        border: '1px solid var(--red-bg)',
      }}>
        <IconAlertTriangle size={12} /> Conflict
      </span>
    )
    if (status === 'verified') return (
      <span style={{
        display: 'flex', alignItems: 'center', gap: 4, fontSize: '0.72rem', fontWeight: 700,
        color: 'var(--green)', background: 'var(--green-bg)', padding: '3px 9px', borderRadius: 5,
      }}>
        <IconCheck size={12} /> Verified
      </span>
    )
    return (
      <span style={{
        fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-2)',
        background: 'var(--bg-card2)', padding: '3px 9px', borderRadius: 5,
        border: '1px solid var(--border)',
      }}>
        ○ Unverified
      </span>
    )
  }

  return (
    <Layout rightPanel={<RightPanel />}>
      <div style={{ padding: '20px 24px' }}>
        {/* Header */}
        <div style={{ marginBottom: 16 }}>
          <h1 style={{ margin: '0 0 4px', fontSize: '1.6rem', fontWeight: 800, color: 'var(--accent)' }}>
            Knowledge
          </h1>
          <p style={{ margin: 0, color: 'var(--text-2)', fontSize: '0.88rem' }}>
            Review and manage extracted knowledge from your company sources.
          </p>
        </div>

        {/* Filters */}
        <div style={{
          background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 10,
          padding: '12px 16px', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap',
        }}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 7,
            background: 'var(--bg-input)', border: '1px solid var(--border)',
            borderRadius: 7, padding: '0 10px', height: 32, flex: 1, minWidth: 200,
          }}>
            <IconSearch size={14} color="var(--text-3)" />
            <input
              value={liveSearch}
              onChange={e => setLiveSearch(e.target.value)}
              placeholder="Search knowledge items..."
              style={{ flex: 1, background: 'none', border: 'none', fontSize: '0.82rem', color: 'var(--text-1)' }}
            />
          </div>

          <SelectFilter label="Source Type" value={sourceFilter}
            options={['All Sources', 'slack', 'email', 'notion', 'zendesk']}
            onChange={setSourceFilter} />
          <SelectFilter label="Status" value={statusFilter}
            options={['All', 'conflict', 'verified', 'unverified']}
            onChange={setStatusFilter} />

          <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <label style={{ fontSize: '0.7rem', color: 'var(--text-3)', fontWeight: 600 }}>Confidence Threshold</label>
              <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--accent)', marginLeft: 8 }}>{confidenceThreshold}%</span>
            </div>
            <input
              type="range" min={0} max={100} value={confidenceThreshold}
              onChange={e => setConfidenceThreshold(Number(e.target.value))}
              style={{ width: 120 }}
            />
          </div>
        </div>

        {/* Table */}
        <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                {['Knowledge Statement', 'Source Type', 'Source / Channel', 'Date Extracted ↓', 'Confidence', 'Status'].map(h => (
                  <th key={h} style={{
                    padding: '10px 14px', textAlign: 'left',
                    fontSize: '0.72rem', fontWeight: 600, color: 'var(--text-3)', letterSpacing: '0.04em',
                    whiteSpace: 'nowrap',
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((item, i) => (
                <>
                  <tr
                    key={item.id}
                    className="row-hover"
                    onClick={() => setExpanded(expanded === item.id ? null : item.id)}
                    style={{
                      borderBottom: expanded === item.id ? 'none' : '1px solid var(--border)',
                      cursor: 'pointer',
                    }}
                  >
                    <td style={{ padding: '12px 14px', maxWidth: 300 }}>
                      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                        {item.status === 'conflict' && (
                          <IconAlertTriangle size={14} color="var(--red)" />
                        )}
                        <span style={{ fontSize: '0.83rem', color: 'var(--text-1)', lineHeight: 1.4 }}>
                          {i + 1}. {item.statement}
                        </span>
                      </div>
                    </td>
                    <td style={{ padding: '12px 14px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <SourceIcon type={item.sourceType} />
                        <span style={{
                          fontSize: '0.72rem', fontWeight: 600, padding: '2px 8px', borderRadius: 4,
                          background: 'var(--bg-card2)', color: 'var(--text-1)',
                          textTransform: 'capitalize',
                        }}>
                          {item.sourceType}
                        </span>
                      </div>
                    </td>
                    <td style={{ padding: '12px 14px', fontSize: '0.8rem', color: 'var(--text-2)' }}>
                      {item.sourceChannel}
                    </td>
                    <td style={{ padding: '12px 14px', fontSize: '0.8rem', color: 'var(--text-2)', whiteSpace: 'nowrap' }}>
                      {item.dateExtracted}
                    </td>
                    <td style={{ padding: '12px 14px' }}>
                      <span style={{
                        fontSize: '0.83rem', fontWeight: 700,
                        color: item.confidence >= 90 ? 'var(--green)' : item.confidence >= 75 ? 'var(--mid)' : 'var(--red)',
                      }}>
                        {item.confidence}%
                      </span>
                    </td>
                    <td style={{ padding: '12px 14px' }}>
                      {statusBadge(item.status)}
                    </td>
                  </tr>

                  {/* Conflict detail row */}
                  {expanded === item.id && item.conflictDetail && (
                    <tr key={`${item.id}-detail`} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td colSpan={6} style={{ padding: '0 14px 14px' }}>
                        <div className="fade-in" style={{
                          background: 'var(--bg-card2)', border: '1px solid var(--border)',
                          borderRadius: 8, padding: '12px 14px',
                        }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 10, fontSize: '0.78rem', fontWeight: 700, color: 'var(--red)' }}>
                            <IconAlertTriangle size={13} /> Conflict details
                          </div>
                          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                            <div style={{ flex: 1, padding: '10px 12px', background: 'var(--bg-card)', borderRadius: 7, border: '1px solid var(--border)' }}>
                              <span style={{
                                fontSize: '0.65rem', fontWeight: 700, color: 'var(--mid)',
                                background: 'var(--mid-bg)', padding: '2px 7px', borderRadius: 4, display: 'inline-block', marginBottom: 6,
                              }}>Older policy</span>
                              <p style={{ margin: '0 0 6px', fontSize: '0.82rem', color: 'var(--text-1)', lineHeight: 1.45 }}>
                                {item.conflictDetail.older}
                              </p>
                              <div style={{ fontSize: '0.7rem', color: 'var(--text-3)' }}>{item.conflictDetail.olderSource}</div>
                            </div>
                            <div style={{
                              width: 28, height: 28, borderRadius: '50%', background: 'var(--red-bg)',
                              display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, fontSize: '1rem',
                            }}>⇄</div>
                            <div style={{ flex: 1, padding: '10px 12px', background: 'var(--bg-card)', borderRadius: 7, border: '1px solid var(--accent)' }}>
                              <span style={{
                                fontSize: '0.65rem', fontWeight: 700, color: 'var(--accent)',
                                background: 'var(--accent-bg)', padding: '2px 7px', borderRadius: 4, display: 'inline-block', marginBottom: 6,
                              }}>Newer guidance</span>
                              <p style={{ margin: '0 0 6px', fontSize: '0.82rem', color: 'var(--text-1)', lineHeight: 1.45 }}>
                                {item.conflictDetail.newer}
                              </p>
                              <div style={{ fontSize: '0.7rem', color: 'var(--text-3)' }}>{item.conflictDetail.newerSource}</div>
                            </div>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </Layout>
  )
}

function SelectFilter({ label, value, options, onChange }: {
  label: string; value: string; options: string[]; onChange: (v: string) => void
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <label style={{ fontSize: '0.7rem', color: 'var(--text-3)', fontWeight: 600 }}>{label}</label>
      <div style={{ position: 'relative' }}>
        <select
          value={value}
          onChange={e => onChange(e.target.value)}
          style={{
            padding: '5px 28px 5px 10px', background: 'var(--bg-card2)',
            border: '1px solid var(--border)', borderRadius: 7,
            color: 'var(--text-1)', fontSize: '0.82rem', cursor: 'pointer',
            appearance: 'none', minWidth: 110,
          }}
        >
          {options.map(o => <option key={o} value={o}>{o}</option>)}
        </select>
        <span style={{ position: 'absolute', right: 8, top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none', color: 'var(--text-3)' }}>
          <IconChevronDown size={12} />
        </span>
      </div>
    </div>
  )
}
