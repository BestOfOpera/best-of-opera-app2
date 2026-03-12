export const API_URLS = {
  curadoria: process.env.NEXT_PUBLIC_API_CURADORIA ?? "http://localhost:8002",
  redator:   process.env.NEXT_PUBLIC_API_REDATOR   ?? "http://localhost:8000",
  editor:    process.env.NEXT_PUBLIC_API_EDITOR     ?? "http://localhost:8001",
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

export async function request<T>(path: string, options?: RequestOptions): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" }

  if (typeof window !== "undefined") {
    const token = localStorage.getItem("bo_auth_token")
    if (token) headers["Authorization"] = `Bearer ${token}`
  }

  const { timeout = 15000, ...fetchOptions } = options ?? {}
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
    const body = await res.json().catch(() => ({ detail: res.statusText }))
    throw new ApiError(res.status, body.detail ?? body)
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

export async function requestFormData<T>(path: string, body: FormData, timeout = 15000): Promise<T> {
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
      throw new Error("Request timeout")
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
    throw new Error(errBody.detail || "Request failed")
  }
  return res.json()
}
