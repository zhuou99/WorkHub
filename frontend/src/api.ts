/** 后端 API 客户端。
 *
 * 会话是 HttpOnly Cookie，所以所有请求都要带 credentials；
 * 后端在 5277、前端在 5173，属于跨域，靠后端的 CORS 中间件放行。
 */

/** 后端地址。留空走 Vite 同源代理（推荐）：/api 与 /health 由 vite.config.ts 代理到后端，
 *  Cookie 同源、无跨 host 问题。直连后端时才需要在这里填绝对地址。 */
export const API_BASE = import.meta.env.VITE_API_BASE ?? ''

export interface Result<T> {
  code: number
  message: string
  data: T | null
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

/** 未登录时由路由守卫接管：抛 401 即可，调用方不必各自处理。 */
let onUnauthorized: (() => void) | null = null
export function setUnauthorizedHandler(fn: () => void) {
  onUnauthorized = fn
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      credentials: 'include',
      headers: {
        ...(init.body ? { 'Content-Type': 'application/json' } : {}),
        ...(init.headers ?? {}),
      },
    })
  } catch {
    throw new ApiError(0, '连不上后端服务，确认它已经在 5277 跑起来了。')
  }

  if (response.status === 401) {
    onUnauthorized?.()
    throw new ApiError(401, '还没有登录，或登录已失效。')
  }

  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    const message = (payload?.message as string) || `请求失败（HTTP ${response.status}）`
    throw new ApiError(response.status, message)
  }
  return payload as T
}

/** 取信封里的 data；data 为 null 时返回 fallback。 */
function unwrap<T>(result: Result<T>, fallback: T): T {
  return result.data === null || result.data === undefined ? fallback : result.data
}

/** 分页结果（后端 PagingResult 是 { total, rows }，不是 { data }）。 */
export interface Paged<T> {
  code: number
  message: string
  total: number
  rows: T[]
}

export const api = {
  get: <T>(path: string) => request<Result<T>>(path).then((r) => unwrap(r, null as T)),
  post: <T>(path: string, body?: unknown) =>
    request<Result<T>>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) })
      .then((r) => unwrap(r, null as T)),
  del: <T>(path: string) => request<Result<T>>(path, { method: 'DELETE' }).then((r) => unwrap(r, null as T)),
  /** 分页端点：直接返回 { total, rows }。 */
  page: <T>(path: string) => request<Paged<T>>(path),
}
