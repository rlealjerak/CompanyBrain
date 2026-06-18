const BASE = '/api'

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
  }
}

async function request<T>(path: string, init: RequestInit = {}, token?: string | null): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init.headers as Record<string, string> | undefined),
  }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${BASE}${path}`, { ...init, headers })
  const body = await res.json()
  if (!res.ok) throw new ApiError(res.status, body.message ?? 'Request failed')
  return body as T
}

export interface Source {
  source_id: string
  source_type: string
  source_timestamp: string | null
  excerpt: string
  similarity: number
}

export interface ChatResponse {
  answer: string
  sources: Source[]
}

export interface SearchResult {
  chunk_id: string
  source_id: string
  source_type: string
  source_timestamp: string | null
  text: string
  similarity: number
  combined_score: number
}

export interface IngestionJob {
  id: string
  source_id: string
  status: string
  locked_at: string | null
  attempt_number: number
  error_message: string | null
}

export interface PersonalTask {
  id: string
  description: string
  urgency_score: number | null
  urgency_band: string | null
  status: string
  deadline: string | null
  context_bundle: SearchResult[] | null
  source_reference: string
  source_label: string | null
  sender: string | null
  action_type: string | null
  created_at: string | null
}

export interface TaskSummary {
  high: number
  medium: number
  low: number
  total: number
}

export const api = {
  login: (email: string, password: string) =>
    request<{ access_token: string; token_type: string }>('/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  me: (token: string) =>
    request<{ id: string; email: string; role: string }>('/v1/auth/me', {}, token),

  chat: (query: string, token: string) =>
    request<ChatResponse>('/v1/query/chat', {
      method: 'POST',
      body: JSON.stringify({ query }),
    }, token),

  search: (query: string, token: string, top_k = 5) =>
    request<{ results: SearchResult[]; count: number }>('/v1/query/search', {
      method: 'POST',
      body: JSON.stringify({ query, top_k }),
    }, token),

  triggerIngest: (token: string, source?: string) =>
    request<{ status: string; source: string }>('/v1/ingest/trigger', {
      method: 'POST',
      body: JSON.stringify({ source: source ?? null }),
    }, token),

  listJobs: (token: string, limit = 50) =>
    request<{ jobs: IngestionJob[] }>(`/v1/ingest/jobs?limit=${limit}`, {}, token),

  getJob: (token: string, jobId: string) =>
    request<IngestionJob>(`/v1/ingest/jobs/${jobId}`, {}, token),

  listTasks: (token: string, statusFilter?: string) => {
    const qs = statusFilter ? `?status_filter=${statusFilter}` : ''
    return request<{ tasks: PersonalTask[]; count: number }>(
      `/v1/personal/tasks${qs}`, {}, token,
    )
  },

  getTask: (token: string, taskId: string) =>
    request<PersonalTask>(`/v1/personal/tasks/${taskId}`, {}, token),

  patchTask: (token: string, taskId: string, status: string) =>
    request<PersonalTask>(`/v1/personal/tasks/${taskId}`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    }, token),

  getTaskSummary: (token: string) =>
    request<TaskSummary>('/v1/personal/summary', {}, token),

  triggerPersonalExtraction: (token: string) =>
    request<{ enqueued: number }>('/v1/personal/trigger', { method: 'POST' }, token),
}

export function openChatStream(_token: string): WebSocket {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return new WebSocket(`${proto}://${window.location.host}/api/v1/query/chat/stream`)
}
