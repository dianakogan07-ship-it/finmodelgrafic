import type { Cur, ModelData } from './model'

export interface User { login: string; is_admin: boolean }
export interface ObjectNode { id: number; name: string; style: string; angle: number; tag: string; has_dashboard: boolean }
export interface Project { id: number; name: string; title: string }
export interface Competitor {
  id: string; name: string; color: string; enabled_default: boolean
  series: { quarter: string; price: number | null; pace: number | null }[]
}
export interface RecalcResult { fr: number; llcr: number; calc_ms: number }
export interface ScenarioState { chips?: Record<string, boolean>; cur?: Cur; model_version?: string; q?: string }

const TOKEN_KEY = 'suz.token'
export const token = {
  get: () => { try { return localStorage.getItem(TOKEN_KEY) } catch { return null } },
  set: (t: string | null) => { try { t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY) } catch { /* приватный режим */ } },
}

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message) }
}

let onUnauthorized = () => {}
export const setUnauthorizedHandler = (f: () => void) => { onUnauthorized = f }

async function req<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  const t = token.get()
  if (t) headers.set('Authorization', `Bearer ${t}`)
  if (init.body && !(init.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  const r = await fetch(path, { ...init, headers })
  if (!r.ok) {
    let msg = r.statusText
    try { const j = await r.json(); msg = typeof j.detail === 'string' ? j.detail : msg } catch { /* не JSON */ }
    if (r.status === 401 && path !== '/api/auth/login') onUnauthorized()
    throw new ApiError(r.status, msg)
  }
  return r.json()
}

export const api = {
  login: (login: string, password: string) =>
    req<{ token: string; user: User }>('/api/auth/login', { method: 'POST', body: JSON.stringify({ login, password }) }),
  me: () => req<User>('/api/auth/me'),
  objects: () => req<ObjectNode[]>('/api/objects'),
  project: (id: number) => req<Project>(`/api/projects/${id}`),
  model: (id: number) => req<ModelData>(`/api/projects/${id}/model`),
  competitors: (id: number) => req<Competitor[]>(`/api/projects/${id}/competitors`),
  recalc: (id: number, model_version: string, queues: Cur, signal: AbortSignal) =>
    req<RecalcResult>(`/api/projects/${id}/recalc`, { method: 'POST', body: JSON.stringify({ model_version, queues }), signal }),
  scenario: (id: number) => req<ScenarioState>(`/api/projects/${id}/scenario`),
  saveScenario: (id: number, state: ScenarioState) =>
    req<{ ok: boolean }>(`/api/projects/${id}/scenario`, { method: 'PUT', body: JSON.stringify({ state }) }),
  uploadModel: (id: number, file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return req<{ model_version: string; warnings: string[] }>(`/api/projects/${id}/model`, { method: 'POST', body: fd })
  },
}
