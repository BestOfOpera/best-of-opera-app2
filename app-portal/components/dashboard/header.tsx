"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { LayoutDashboard, FileText, Bell } from "lucide-react"

export function DashboardHeader() {
    const pathname = usePathname()

    const navItems = [
        {
            label: "Projetos",
            href: "/dashboard",
            icon: LayoutDashboard,
            active: pathname === "/dashboard" || pathname.includes("/dashboard/projeto"),
        },
        {
            label: "Reports",
            href: "/dashboard/reports",
            icon: FileText,
            active: pathname.includes("/dashboard/reports"),
            badge: 3,
        },
    ]

    return (
        <header className="sticky top-0 z-40 w-full border-b bg-background/80 backdrop-blur-md">
            <div className="container mx-auto px-4 h-16 flex items-center justify-between">
                <div className="flex items-center gap-8">
                    <Link href="/dashboard" className="flex items-center gap-2 group">
                        <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center transition-transform group-hover:rotate-12">
                            <span className="text-primary-foreground font-black text-xs">BO</span>
                        </div>
                        <span className="font-bold text-lg tracking-tight hidden sm:inline-block">
                            Best of Opera <span className="text-secondary">— Dashboard</span>
                        </span>
                    </Link>

                    <nav className="flex items-center gap-1">
                        {navItems.map((item) => (
                            <Link
                                key={item.href}
                                href={item.href}
                                className={cn(
                                    "flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all relative",
                                    item.active
                                        ? "bg-primary/5 text-primary"
                                        : "text-muted-foreground hover:bg-muted"
                                )}
                            >
                                <item.icon className="w-4 h-4" />
                                {item.label}
                                {item.badge && (
                                    <span className="flex h-4 w-4 items-center justify-center rounded-full bg-secondary text-[10px] font-bold text-secondary-foreground">
                                        {item.badge}
                                    </span>
                                )}
                                {item.active && (
                                    <div className="absolute bottom-0 left-2 right-2 h-0.5 bg-primary rounded-full" />
                                )}
                            </Link>
                        ))}
                    </nav>
                </div>

                <div className="flex items-center gap-4">
                    <button className="relative p-2 rounded-full hover:bg-muted transition-colors">
                        <Bell className="w-5 h-5 text-muted-foreground" />
                        <span className="absolute top-2 right-2 w-2 h-2 bg-secondary rounded-full border-2 border-background animate-pulse" />
                    </button>
                    <div className="w-8 h-8 rounded-full bg-accent border-2 border-primary/10" />
                </div>
            </div>
        </header>
    )
}
