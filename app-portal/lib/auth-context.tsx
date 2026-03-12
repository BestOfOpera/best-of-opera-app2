"use client"

import { createContext, useContext, useEffect, useRef, useState, ReactNode } from "react"
import { useRouter } from "next/navigation"
import { editorApi } from "@/lib/api/editor"

export interface AuthContextType {
  user: any | null
  isAdmin: boolean
  isLoading: boolean
  login: (token: string, redirectTo?: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  isAdmin: false,
  isLoading: true,
  login: async (_token: string, _redirectTo?: string) => {},
  logout: () => {},
})

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<any | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const router = useRouter()
  const abortRef = useRef<AbortController | null>(null)

  const loadUser = async (): Promise<void> => {
    // Cancel any in-flight loadUser request before starting a new one
    if (abortRef.current) {
      abortRef.current.abort()
    }
    const controller = new AbortController()
    abortRef.current = controller
    const { signal } = controller

    const token = typeof window !== "undefined" ? localStorage.getItem("bo_auth_token") : null
    if (!token) {
      if (!signal.aborted) {
        setUser(null)
        setIsLoading(false)
      }
      return
    }

    try {
      const userData = await editorApi.getMe()
      // Only update state if this call was not superseded or cancelled
      if (!signal.aborted) {
        setUser(userData)
      }
    } catch (err) {
      if (!signal.aborted) {
        console.error("Failed to load user:", err)
        localStorage.removeItem("bo_auth_token")
        setUser(null)
      }
    } finally {
      if (!signal.aborted) {
        setIsLoading(false)
      }
    }
  }

  useEffect(() => {
    // Load user once on mount only — NOT on every pathname change
    loadUser()

    // Listen for 401 events dispatched by base.ts
    const handleUnauthorized = () => {
      logout()
    }
    window.addEventListener("bo:unauthorized", handleUnauthorized)

    return () => {
      window.removeEventListener("bo:unauthorized", handleUnauthorized)
      // Abort any in-flight request when the provider unmounts
      if (abortRef.current) {
        abortRef.current.abort()
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const login = async (token: string, redirectTo = "/dashboard"): Promise<void> => {
    localStorage.setItem("bo_auth_token", token)
    // Await loadUser so the user is populated before the redirect renders the next page
    await loadUser()
    router.push(redirectTo)
  }

  const logout = () => {
    // Cancel any in-flight request before wiping state
    if (abortRef.current) {
      abortRef.current.abort()
      abortRef.current = null
    }
    localStorage.removeItem("bo_auth_token")
    setUser(null)
    router.push("/login")
  }

  const isAdmin = user?.role === "admin"

  return (
    <AuthContext.Provider value={{ user, isAdmin, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
