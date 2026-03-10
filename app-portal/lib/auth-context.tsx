"use client"

import { createContext, useContext, useEffect, useState, ReactNode } from "react"
import { useRouter, usePathname } from "next/navigation"
import { editorApi } from "@/lib/api/editor"

export interface AuthContextType {
  user: any | null
  isAdmin: boolean
  isLoading: boolean
  login: (token: string) => void
  logout: () => void
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  isAdmin: false,
  isLoading: true,
  login: () => {},
  logout: () => {},
})

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<any | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const router = useRouter()
  const pathname = usePathname()

  const loadUser = async () => {
    const token = typeof window !== "undefined" ? localStorage.getItem("bo_auth_token") : null
    if (!token) {
      setUser(null)
      setIsLoading(false)
      return
    }

    try {
      const userData = await editorApi.getMe()
      setUser(userData)
    } catch (err) {
      console.error("Failed to load user:", err)
      localStorage.removeItem("bo_auth_token")
      setUser(null)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadUser()
  }, [pathname]) // Re-check on nav

  const login = (token: string) => {
    localStorage.setItem("bo_auth_token", token)
    loadUser()
  }

  const logout = () => {
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
