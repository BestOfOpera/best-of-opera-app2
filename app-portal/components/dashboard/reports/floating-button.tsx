"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Camera, AlertCircle } from "lucide-react"
import { useParams, usePathname } from "next/navigation"

// This is a simplified FAB, in a real scenario we'd import the Modal we created
// But to avoid circular dependencies or complex imports, we'll suggest using a global event or store

export function FloatingReportButton() {
    const pathname = usePathname()
    const params = useParams()

    // We can't easily trigger the modal from here without a global state (Zustand/Context)
    // For this exercise, we'll make it redirect to the reports page with a query param
    // if we wanted it to open the modal directly.

    const handleClick = () => {
        let url = "/dashboard/reports?action=create"
        if (pathname.includes("/editor/") && params.id) {
            url += `&projeto_id=${params.id}`
        }
        window.location.href = url
    }

    return (
        <div className="fixed bottom-8 right-8 z-[100] group">
            <div className="absolute -top-14 right-0 bg-primary text-white text-[10px] font-black uppercase tracking-widest px-4 py-2 rounded-xl shadow-2xl opacity-0 group-hover:opacity-100 transition-all transform translate-y-2 group-hover:translate-y-0 whitespace-nowrap pointer-events-none border border-white/10">
                Reportar Problema
            </div>
            <Button
                size="icon"
                className="h-16 w-16 rounded-[2rem] shadow-[0_20px_50px_rgba(26,26,46,0.3)] bg-primary text-white hover:bg-secondary hover:shadow-secondary/30 hover:scale-110 active:scale-95 transition-all duration-500 border-4 border-background group-active:rotate-12"
                onClick={handleClick}
            >
                <Camera className="h-7 w-7 stroke-[2.5px]" />
                <span className="absolute -top-1 -right-1 w-4 h-4 bg-secondary rounded-full border-2 border-background animate-pulse" />
            </Button>
        </div>
    )
}
