const PROD_URLS = {
  curadoria: "https://curadoria-backend-production.up.railway.app",
  redator:   "https://app-production-870c.up.railway.app",
  editor:    "https://editor-backend-production.up.railway.app",
}

function isProduction(): boolean {
  if (typeof window !== "undefined") {
    return !["localhost", "127.0.0.1"].includes(window.location.hostname)
  }
  return process.env.NODE_ENV === "production"
}

function resolveUrl(service: keyof typeof PROD_URLS, localPort: number): string {
  const envKeys = {
    curadoria: process.env.NEXT_PUBLIC_API_CURADORIA,
    redator:   process.env.NEXT_PUBLIC_API_REDATOR,
    editor:    process.env.NEXT_PUBLIC_API_EDITOR,
  }
  
  let url = envKeys[service] || (isProduction() ? PROD_URLS[service] : `http://localhost:${localPort}`)
  
  // Force HTTPS for production railway URLs to avoid Mixed Content
  if (isProduction() && url.includes(".up.railway.app") && url.startsWith("http://")) {
    console.warn(`Mixed Content Preventive Fix: Forcing HTTPS for ${service} URL`)
    url = url.replace("http://", "https://")
  }

  return url
}

export const API_URLS = {
  get curadoria() { return resolveUrl("curadoria", 8002) },
  get redator()   { return resolveUrl("redator", 8000) },
  get editor()    { return resolveUrl("editor", 8001) },
}

export class ApiError extends Error {
  status: number
  detail: unknown
  constructor(status: number, detail: unknown) {
    const msg = typeof detail === "string" ? detail : (detail as Record<string, unknown>)?.mensagem as string || "Request failed"
    super(msg)
    this.status = status
    this.detail = detail
  }
}

interface RequestOptions extends RequestInit {
  timeout?: number
}

const MAX_503_RETRIES = 2

/** Only retry 503 on idempotent/generation requests — never on approve/delete/create/translate */
function isSafeToRetry(path: string, method: string | undefined): boolean {
  const m = (method || "GET").toUpperCase()
  if (m === "GET") return true
  if (m !== "POST") return false
  // POST is safe to retry only for AI generation endpoints
  return /\/(generate|regenerate|research|detect)/.test(path)
}

export async function request<T>(path: string, options?: RequestOptions): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" }

  if (typeof window !== "undefined") {
    const token = localStorage.getItem("bo_auth_token")
    if (token) headers["Authorization"] = `Bearer ${token}`
  }

  const { timeout = 30000, ...fetchOptions } = options ?? {}
  const canRetry = isSafeToRetry(path, fetchOptions.method)
  const maxAttempts = canRetry ? MAX_503_RETRIES : 0

  for (let attempt = 0; attempt <= maxAttempts; attempt++) {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), timeout)

    let res: Response
    try {
      res = await fetch(path, {
        headers: { ...headers, ...(fetchOptions.headers as any) },
        ...fetchOptions,
        signal: controller.signal,
      })
    } catch (err: unknown) {
      clearTimeout(timer)
      if (err instanceof Error && err.name === "AbortError") {
        throw new ApiError(408, "Request timeout")
      }
      throw err
    } finally {
      clearTimeout(timer)
    }

    // Auto-retry on 503 (AI overloaded) — only for safe-to-retry requests
    if (res.status === 503 && attempt < maxAttempts) {
      const wait = (attempt + 1) * 15
      if (typeof window !== "undefined") {
        window.dispatchEvent(new CustomEvent("bo:retry", { detail: { wait, attempt: attempt + 1, max: maxAttempts } }))
      }
      await new Promise(r => setTimeout(r, wait * 1000))
      continue
    }

    if (!res.ok) {
      if (res.status === 401 && typeof window !== "undefined") {
        localStorage.removeItem("bo_auth_token")
        window.dispatchEvent(new CustomEvent("bo:unauthorized"))
      }
      const body = await res.json().catch(() => ({ detail: res.statusText }))
      throw new ApiError(res.status, body.detail ?? body)
    }
    if (res.status === 204) return undefined as T
    return res.json()
  }

  // Should not reach here, but TypeScript needs it
  throw new ApiError(503, "Service unavailable after retries")
}

export async function requestFormData<T>(path: string, body: FormData, timeout = 30000): Promise<T> {
  const headers: Record<string, string> = {}

  if (typeof window !== "undefined") {
    const token = localStorage.getItem("bo_auth_token")
    if (token) headers["Authorization"] = `Bearer ${token}`
  }

  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeout)

  let res: Response
  try {
    res = await fetch(path, { method: "POST", headers, body, signal: controller.signal })
  } catch (err: unknown) {
    if (err instanceof Error && err.name === "AbortError") {
      throw new ApiError(408, "Request timeout")
    }
    throw err
  } finally {
    clearTimeout(timer)
  }

  if (!res.ok) {
    if (res.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("bo_auth_token")
      window.dispatchEvent(new CustomEvent("bo:unauthorized"))
    }
    const errBody = await res.json().catch(() => ({ detail: res.statusText }))
    throw new ApiError(res.status, errBody.detail || errBody)
  }
  return res.json()
}
