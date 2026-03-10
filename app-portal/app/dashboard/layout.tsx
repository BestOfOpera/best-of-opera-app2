"use client"

import { DashboardHeader } from "@/components/dashboard/header"
import { FloatingReportButton } from "@/components/dashboard/reports/floating-button"
import { Toaster } from "sonner"

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
    return (
        <div className="min-h-screen bg-background">
            <DashboardHeader />
            <main className="relative pb-20 md:pb-8">
                {children}
            </main>
            <FloatingReportButton />
            <Toaster position="top-right" richColors />
        </div>
    )
}
