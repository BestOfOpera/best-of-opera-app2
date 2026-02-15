"use client"

import { useState } from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { Search, LayoutDashboard, Download, PenTool, ListPlus, FileCheck, FileText, Globe, Send, Film, ListOrdered, Music, AlignLeft, HardDrive, Settings, ChevronDown } from "lucide-react"

interface NavItem { label: string; href: string; icon: React.ElementType }
interface ToolSection { id: string; label: string; icon: React.ElementType; items: NavItem[] }

const tools: ToolSection[] = [
  { id: "curadoria", label: "Curadoria", icon: Search, items: [
    { label: "Dashboard", href: "/curadoria", icon: LayoutDashboard },
    { label: "Downloads", href: "/curadoria/downloads", icon: Download },
  ]},
  { id: "redator", label: "Redator", icon: PenTool, items: [
    { label: "Projetos", href: "/redator", icon: ListPlus },
    { label: "Novo Projeto", href: "/redator/novo", icon: FileText },
  ]},
  { id: "editor", label: "Editor", icon: Film, items: [
    { label: "Fila de Edicao", href: "/editor", icon: ListOrdered },
  ]},
]

function deriveActiveTool(pathname: string): string {
  if (pathname.startsWith("/curadoria")) return "curadoria"
  if (pathname.startsWith("/redator")) return "redator"
  if (pathname.startsWith("/editor")) return "editor"
  return "curadoria"
}

export function AppSidebar() {
  const pathname = usePathname()
  const activeTool = deriveActiveTool(pathname)
  const [expandedTools, setExpandedTools] = useState<string[]>([activeTool])

  function toggleTool(toolId: string) {
    setExpandedTools((prev) => prev.includes(toolId) ? prev.filter((t) => t !== toolId) : [...prev, toolId])
  }

  return (
    <aside className="flex h-full w-56 flex-col border-r border-border bg-card">
      <div className="flex items-center gap-2 px-5 py-5">
        <span className="font-serif text-lg tracking-tight text-foreground">Arias</span>
        <span className="font-serif text-lg tracking-tight text-muted-foreground">Conteudo</span>
      </div>
      <div className="mx-4 mb-4 h-px bg-border" />
      <nav className="flex-1 overflow-y-auto px-3">
        <div className="flex flex-col gap-0.5">
          {tools.map((tool) => {
            const isExpanded = expandedTools.includes(tool.id)
            return (
              <div key={tool.id}>
                <button onClick={() => toggleTool(tool.id)} className="flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 transition-colors hover:bg-muted/60">
                  <tool.icon className="h-4 w-4 shrink-0 text-muted-foreground" />
                  <span className="truncate text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">{tool.label}</span>
                  <ChevronDown className={cn("ml-auto h-3 w-3 text-muted-foreground/40 transition-transform", isExpanded && "rotate-180")} />
                </button>
                {isExpanded && (
                  <div className="mb-3 ml-3 mt-0.5 flex flex-col gap-px border-l border-border pl-3">
                    {tool.items.map((item) => {
                      const isPageActive = pathname === item.href
                      return (
                        <Link key={item.href} href={item.href} className={cn("flex w-full items-center gap-2 rounded-md px-2.5 py-1.5 text-left text-[13px] transition-colors", isPageActive ? "bg-muted font-medium text-foreground" : "text-muted-foreground hover:bg-muted/40 hover:text-foreground")}>
                          <item.icon className="h-3.5 w-3.5 shrink-0" />
                          <span className="truncate">{item.label}</span>
                        </Link>
                      )
                    })}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </nav>
      <div className="border-t border-border px-4 py-3">
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-muted text-[11px] font-semibold text-muted-foreground">A</div>
          <div className="flex-1 truncate">
            <p className="truncate text-xs font-medium text-foreground">Admin</p>
            <p className="text-[10px] text-muted-foreground">admin@arias.com</p>
          </div>
          <button className="rounded-md p-1 transition-colors hover:bg-muted" aria-label="Configuracoes">
            <Settings className="h-3.5 w-3.5 text-muted-foreground" />
          </button>
        </div>
      </div>
    </aside>
  )
}
