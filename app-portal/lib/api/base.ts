function isProduction() {
  return typeof window !== "undefined" && window.location.hostname.includes("railway.app")
}

export const API_URLS = {
  get curadoria() { return isProduction() ? "https://curadoria-backend-production.up.railway.app" : "http://localhost:8002" },
  get redator() { return isProduction() ? "https://app-production-870c.up.railway.app" : "http://localhost:8000" },
  get editor() { return isProduction() ? "https://editor-backend-production.up.railway.app" : "http://localhost:8001" },
}

export async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(body.detail || "Request failed")
  }
  return res.json()
}

export async function requestFormData<T>(path: string, body: FormData): Promise<T> {
  const res = await fetch(path, { method: "POST", body })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || "Request failed")
  }
  return res.json()
}
