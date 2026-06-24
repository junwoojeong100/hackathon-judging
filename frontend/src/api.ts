import type { Criterion, LeaderboardEntry, Submission } from './types'

const BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const TOKEN_KEY = 'hj_admin_token'
export function getAdminToken(): string {
  return localStorage.getItem(TOKEN_KEY) || ''
}
export function setAdminToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}
function authHeaders(): Record<string, string> {
  const t = getAdminToken()
  return t ? { 'X-Admin-Token': t } : {}
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init)
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail || detail
    } catch {
      /* ignore non-JSON error bodies */
    }
    throw new Error(detail)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export interface Health {
  status: string
  azure_configured: boolean
  auth_required: boolean
  execution_enabled: boolean
  execution_weight: number
  azure_points: number
  ms_stack_points: number
  ms_stack_per: number
}

export const api = {
  health: () => req<Health>('/api/health'),

  listSubmissions: (team?: string) =>
    req<Submission[]>(`/api/submissions${team ? `?team=${encodeURIComponent(team)}` : ''}`),
  getSubmission: (id: number) => req<Submission>(`/api/submissions/${id}`),
  createGithub: (body: {
    team_name: string
    project_name: string
    github_url: string
    stage: string
    deployment_url: string
  }) =>
    req<Submission>('/api/submissions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify(body),
    }),
  uploadZip: (form: FormData) =>
    req<Submission>('/api/submissions/upload', {
      method: 'POST',
      headers: { ...authHeaders() },
      body: form,
    }),
  rejudge: (id: number) =>
    req<Submission>(`/api/submissions/${id}/rejudge`, {
      method: 'POST',
      headers: { ...authHeaders() },
    }),
  deleteSubmission: (id: number) =>
    req<void>(`/api/submissions/${id}`, { method: 'DELETE', headers: { ...authHeaders() } }),

  leaderboard: () => req<LeaderboardEntry[]>('/api/leaderboard'),

  getRubric: () => req<Criterion[]>('/api/rubric'),
}
