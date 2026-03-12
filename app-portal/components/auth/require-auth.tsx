"use client"

import { useEffect } from "react"
import { useRouter, usePathname } from "next/navigation"
import { useAuth } from "@/lib/auth-context"

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth()
  const router = useRouter()
  const pathname = usePathname()

  useEffect(() => {
    if (isLoading) return
    if (!user) {
      router.push("/login")
    } else if (user.must_change_password && pathname !== "/alterar-senha") {
      router.push("/alterar-senha")
    }
  }, [user, isLoading, router, pathname])

  if (isLoading || !user) {
    return (
      <div className="flex h-screen w-full items-center justify-center">
        <div className="text-muted-foreground animate-pulse text-sm">Carregando...</div>
      </div>
    )
  }

  return <>{children}</>
}
