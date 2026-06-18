import { ReactNode } from 'react'
type P = { size?: number; color?: string; className?: string }

const ic = (d: string, viewBox = '0 0 24 24') =>
  ({ size = 18, color = 'currentColor', className }: P) => (
    <svg width={size} height={size} viewBox={viewBox} fill="none"
      stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"
      className={className}>
      <path d={d} />
    </svg>
  )

const ic2 = (children: ReactNode, viewBox = '0 0 24 24') =>
  ({ size = 18, color = 'currentColor', className }: P) => (
    <svg width={size} height={size} viewBox={viewBox} fill="none"
      stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"
      className={className}>
      {children}
    </svg>
  )

export const IconGrid = ic2(<>
  <rect x="3" y="3" width="7" height="7" rx="1" />
  <rect x="14" y="3" width="7" height="7" rx="1" />
  <rect x="3" y="14" width="7" height="7" rx="1" />
  <rect x="14" y="14" width="7" height="7" rx="1" />
</>)

export const IconDatabase = ic2(<>
  <ellipse cx="12" cy="5" rx="9" ry="3" />
  <path d="M3 5v14c0 1.66 4.03 3 9 3s9-1.34 9-3V5" />
  <path d="M3 12c0 1.66 4.03 3 9 3s9-1.34 9-3" />
</>)

export const IconBook = ic2(<>
  <path d="M4 19.5A2.5 2.5 0 016.5 17H20" />
  <path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z" />
</>)

export const IconSearch = ic2(<>
  <circle cx="11" cy="11" r="8" />
  <path d="M21 21l-4.35-4.35" />
</>)

export const IconCheckSquare = ic2(<>
  <path d="M9 11l3 3L22 4" />
  <path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11" />
</>)

export const IconSettings = ic2(<>
  <circle cx="12" cy="12" r="3" />
  <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" />
</>)

export const IconBell = ic2(<>
  <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9" />
  <path d="M13.73 21a2 2 0 01-3.46 0" />
</>)

export const IconChevronLeft = ic('M15 18l-6-6 6-6')
export const IconChevronRight = ic('M9 18l6-6-6-6')
export const IconChevronDown = ic('M6 9l6 6 6-6')

export const IconSun = ic2(<>
  <circle cx="12" cy="12" r="5" />
  <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
</>)

export const IconMoon = ic('M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z')

export const IconRefresh = ic2(<>
  <polyline points="23 4 23 10 17 10" />
  <polyline points="1 20 1 14 7 14" />
  <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15" />
</>)

export const IconPlus = ic('M12 5v14M5 12h14')

export const IconArrowRight = ic('M5 12h14M12 5l7 7-7 7')

export const IconFilter = ic2(<>
  <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
</>)

export const IconTrendUp = ic2(<>
  <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
  <polyline points="17 6 23 6 23 12" />
</>)

export const IconDoc = ic2(<>
  <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
  <polyline points="14 2 14 8 20 8" />
</>)

export const IconClock = ic2(<>
  <circle cx="12" cy="12" r="10" />
  <polyline points="12 6 12 12 16 14" />
</>)

export const IconAlertTriangle = ic2(<>
  <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
  <line x1="12" y1="9" x2="12" y2="13" />
  <line x1="12" y1="17" x2="12.01" y2="17" />
</>)

export const IconCheck = ic2(<>
  <polyline points="20 6 9 17 4 12" />
</>)

export const IconX = ic('M18 6L6 18M6 6l12 12')

export const IconSparkles = ic2(<>
  <path d="M12 3l1.5 4.5L18 9l-4.5 1.5L12 15l-1.5-4.5L6 9l4.5-1.5L12 3z" />
  <path d="M5 17l.75 2.25L8 20l-2.25.75L5 23l-.75-2.25L2 20l2.25-.75L5 17z" />
  <path d="M19 2l.5 1.5L21 4l-1.5.5L19 6l-.5-1.5L17 4l1.5-.5L19 2z" />
</>)

export const IconUser = ic2(<>
  <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
  <circle cx="12" cy="7" r="4" />
</>)

export const IconExternalLink = ic2(<>
  <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6" />
  <polyline points="15 3 21 3 21 9" />
  <line x1="10" y1="14" x2="21" y2="3" />
</>)

export const IconBrain = ({ size = 36 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 100 100" fill="none">
    <circle cx="50" cy="50" r="48" fill="none" stroke="#22d3ee" strokeWidth="3" opacity="0.3" />
    <circle cx="50" cy="50" r="34" fill="none" stroke="#22d3ee" strokeWidth="2" opacity="0.5" />
    <path d="M30 50 Q35 35 50 35 Q65 35 70 50 Q65 65 50 65 Q35 65 30 50Z"
      fill="none" stroke="#22d3ee" strokeWidth="2.5" />
    <circle cx="50" cy="50" r="6" fill="#22d3ee" opacity="0.9" />
    <line x1="50" y1="20" x2="50" y2="35" stroke="#22d3ee" strokeWidth="2" opacity="0.6" />
    <line x1="50" y1="65" x2="50" y2="80" stroke="#22d3ee" strokeWidth="2" opacity="0.6" />
    <line x1="20" y1="50" x2="35" y2="50" stroke="#22d3ee" strokeWidth="2" opacity="0.6" />
    <line x1="65" y1="50" x2="80" y2="50" stroke="#22d3ee" strokeWidth="2" opacity="0.6" />
  </svg>
)

export const SourceIcon = ({ type }: { type: string }) => {
  const t = type.toLowerCase()
  if (t === 'slack') return (
    <svg width="18" height="18" viewBox="0 0 124 124" fill="none">
      <path d="M26.3 78.3a13.1 13.1 0 01-13.2 13.1 13.1 13.1 0 01-13.1-13 13.1 13.1 0 0113-13.2h13.2v13z" fill="#E01E5A"/>
      <path d="M32.8 78.3a13.1 13.1 0 0113.1-13.1 13.1 13.1 0 0113.2 13v33a13.1 13.1 0 01-13.1 13.2 13.1 13.1 0 01-13.2-13.1V78.3z" fill="#E01E5A"/>
      <path d="M45.9 26.3A13.1 13.1 0 0132.8 13.1 13.1 13.1 0 0145.9 0a13.1 13.1 0 0113.2 13v13.2H45.9z" fill="#36C5F0"/>
      <path d="M45.9 32.8a13.1 13.1 0 0113.2 13.1 13.1 13.1 0 01-13.1 13.2H12.9A13.1 13.1 0 01-.2 45.9 13.1 13.1 0 0113 32.8h33z" fill="#36C5F0"/>
      <path d="M97.7 45.9a13.1 13.1 0 0113.1-13.1 13.1 13.1 0 0113.2 13 13.1 13.1 0 01-13 13.2H97.7V45.9z" fill="#2EB67D"/>
      <path d="M91.2 45.9A13.1 13.1 0 0178 32.8a13.1 13.1 0 00-13.1 13V79a13.1 13.1 0 0013.1 13.1 13.1 13.1 0 0013.2-13V45.9z" fill="#2EB67D"/>
      <path d="M78.1 97.7a13.1 13.1 0 0113.1 13.1 13.1 13.1 0 01-13 13.2 13.1 13.1 0 01-13.2-13V97.7h13z" fill="#ECB22E"/>
      <path d="M78.1 91.2A13.1 13.1 0 0165 78a13.1 13.1 0 00-13.2 13v33a13.1 13.1 0 0013.1 13.2 13.1 13.1 0 0013.2-13V91.2z" fill="#ECB22E"/>
    </svg>
  )
  if (t === 'email') return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" strokeWidth="1.8">
      <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
      <polyline points="22,6 12,13 2,6"/>
    </svg>
  )
  if (t === 'notion') return (
    <svg width="18" height="18" viewBox="0 0 100 100" fill="currentColor">
      <path d="M6 4.8l28.7-2.1c3.5-.3 4.4.1 6.6 1.7l9.1 6.4c1.5 1.1 2 1.4 2 2.6v57.2c0 2.3-1 3.7-3.3 3.9l-34.2 2.1c-1.9.1-2.9-.2-3.8-1.4L3.6 65.8C2.6 64.5 2 63.3 2 61.9V8.1C2 6.2 3.4 5 6 4.8z" fill="white"/>
      <path d="M34.7 2.7L6 4.8C3.4 5 2 6.2 2 8.1v53.8c0 1.4.6 2.6 1.6 3.9l7.6 9.4c.9 1.2 1.9 1.5 3.8 1.4l34.2-2.1c2.3-.2 3.3-1.6 3.3-3.9V13.4c0-1.1-.4-1.5-1.8-2.5L41.3 4.4c-2.2-1.6-3.1-2-6.6-1.7zm1.9 5.2L48 16.5c1.3.9 1.8 1.3 1.8 2.4v54.2c0 1.6-.7 2.6-2.3 2.7l-30.3 1.9c-1.5.1-2.3-.2-3-.9L6.5 68.4C5.8 67.6 5.4 66.7 5.4 65.6V11.8c0-1.5.8-2.3 2.5-2.5L36.6 7.9z" fill="black"/>
      <path d="M23.7 21.5c-2.5.2-3.1.3-4.5 1.4L11 29c-1 .8-1.4 1.8-1.4 2.8v36.3c0 1.6.5 2.3 1.6 2.2l4.5-.3c1.3-.1 1.8-.7 1.8-2.3V36.4c0-1.3.5-2 1.6-2.1l5.4-.3c1.2-.1 1.8-.8 1.8-2.1V23.4c0-1.3-.7-2-2.6-1.9z" fill="black"/>
    </svg>
  )
  if (t === 'zendesk') return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#8b5cf6" strokeWidth="1.8">
      <path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>
    </svg>
  )
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
      <polyline points="14 2 14 8 20 8"/>
    </svg>
  )
}
