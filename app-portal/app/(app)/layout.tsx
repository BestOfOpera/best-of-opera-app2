"use client"

import { AppShell } from "@/components/app-shell"
import { RequireAuth } from "@/components/auth/require-auth"
import { FloatingReportButton } from "@/components/dashboard/reports/floating-button"

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <RequireAuth>
      <AppShell>
        {children}
        <FloatingReportButton />
      </AppShell>
    </RequireAuth>
  )
}
