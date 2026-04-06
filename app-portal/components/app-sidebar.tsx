"use client"

import { useState, useEffect, useCallback } from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { useAuth } from "@/lib/auth-context"
import { useBrand } from "@/lib/brand-context"
import { redatorApi } from "@/lib/api/redator"
import { editorApi } from "@/lib/api/editor"
import { Search, LayoutDashboard, Download, PenTool, ListPlus, FileCheck, FileText, Globe, Send, Film, ListOrdered, Music, AlignLeft, HardDrive, Settings, ChevronDown, User, ShieldCheck, LogOut, CalendarDays, CheckCircle2 } from "lucide-react"

interface NavItem { label: string; href: string; icon: React.ElementType; adminOnly?: boolean; badge?: number }
interface ToolSection { id: string; label: string; icon: React.ElementType; items: NavItem[]; adminOnly?: boolean }

function SidebarBadge({ count }: { count: number }) {
  if (!count || count <= 0) return null
  return (
    <span className="ml-auto text-xs font-medium px-1.5 py-0.5 rounded-full bg-muted text-muted-foreground">
      {count > 99 ? "99+" : count}
    </span>
  )
}

const tools: ToolSection[] = [
  {
    id: "curadoria", label: "Curadoria", icon: Search, items: [
      { label: "Dashboard", href: "/curadoria", icon: LayoutDashboard },
      { label: "Downloads", href: "/curadoria/downloads", icon: Download },
    ]
  },
  {
    id: "redator", label: "Redator de Conteúdo", icon: PenTool, items: [
      { label: "Projetos", href: "/redator", icon: ListPlus },
      { label: "Novo Projeto", href: "/redator/novo", icon: FileText },
    ]
  },
  {
    id: "editor", label: "Editor de Vídeo", icon: Film, items: [
      { label: "Fila de Edicao", href: "/editor", icon: ListOrdered },
    ]
  },
  {
    id: "producao", label: "Produção", icon: CalendarDays, items: [
      { label: "Calendário", href: "/calendario", icon: CalendarDays },
      { label: "Finalizados", href: "/finalizados", icon: CheckCircle2 },
      { label: "Visão Geral", href: "/dashboard", icon: LayoutDashboard },
      { label: "Métricas", href: "/dashboard/producao", icon: ListOrdered },
    ]
  },
  {
    id: "sistema", label: "Sistema", icon: HardDrive, items: [
      { label: "Saúde", href: "/dashboard/saude", icon: HardDrive },
      { label: "Reports", href: "/dashboard/reports", icon: FileText },
    ]
  },
  {
    id: "admin", label: "Administração", icon: ShieldCheck, adminOnly: true, items: [
      { label: "Marcas / Perfis", href: "/admin/marcas", icon: Globe },
      { label: "Usuários", href: "/admin/usuarios", icon: User },
    ]
  },
]

function deriveActiveTool(pathname: string): string {
  if (pathname.startsWith("/curadoria")) return "curadoria"
  if (pathname.startsWith("/calendario")) return "producao"
  if (pathname.startsWith("/finalizados")) return "producao"
  if (pathname.startsWith("/redator")) return "redator"
  if (pathname.startsWith("/editor")) return "editor"
  if (pathname === "/dashboard" || pathname.startsWith("/dashboard/producao") || pathname.startsWith("/dashboard/projeto")) return "producao"
  if (pathname.startsWith("/dashboard/saude") || pathname.startsWith("/dashboard/reports")) return "sistema"
  if (pathname.startsWith("/dashboard")) return "producao"
  if (pathname.startsWith("/admin")) return "admin"
  return "curadoria"
}

export function AppSidebar() {
  const pathname = usePathname()
  const activeTool = deriveActiveTool(pathname)
  const [expandedTools, setExpandedTools] = useState<string[]>([activeTool])
  const { user, isAdmin, logout, isLoading } = useAuth()
  const { selectedBrand } = useBrand()
  const [counts, setCounts] = useState({ redator: 0, editor: 0, finalizados: 0 })

  const fetchCounts = useCallback(async () => {
    if (!selectedBrand) return
    try {
      const [redatorRes, editorTotal, editorConcluido] = await Promise.all([
        redatorApi.listProjects({ brand_slug: selectedBrand.slug, limit: 1 }),
        editorApi.listarEdicoes({ limit: "1" }, selectedBrand.id),
        editorApi.listarEdicoes({ status: "concluido", limit: "1" }, selectedBrand.id),
      ])
      setCounts({
        redator: redatorRes.total || 0,
        editor: Math.max(0, (editorTotal.total || 0) - (editorConcluido.total || 0)),
        finalizados: editorConcluido.total || 0,
      })
    } catch {
      // Silencioso — badges ficam em 0
    }
  }, [selectedBrand])

  useEffect(() => {
    fetchCounts()
    const interval = setInterval(fetchCounts, 60_000)
    return () => clearInterval(interval)
  }, [fetchCounts])

  const badgeMap: Record<string, number> = {
    "/redator": counts.redator,
    "/editor": counts.editor,
    "/finalizados": counts.finalizados,
  }

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
          {tools.filter(t => !t.adminOnly || isAdmin).map((tool, index, array) => {
            const isExpanded = expandedTools.includes(tool.id)
            const isFirstAdmin = tool.adminOnly && (index === 0 || !array[index - 1].adminOnly);
            const isSistema = tool.id === "sistema" && (index === 0 || array[index - 1].id !== "sistema");
            return (
              <div key={tool.id}>
                {(isFirstAdmin || isSistema) && (
                  <div className="my-2.5 px-3">
                    <div className="h-px bg-border/80" />
                  </div>
                )}
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
                          {badgeMap[item.href] > 0 && <SidebarBadge count={badgeMap[item.href]} />}
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
        {!isLoading && user ? (
          <div className="flex items-center gap-2.5">
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary/10 text-[11px] font-semibold text-primary uppercase">
              {user.nome ? user.nome.charAt(0) : "U"}
            </div>
            <div className="flex-1 truncate">
              <p className="truncate text-xs font-medium text-foreground">{user.nome}</p>
              <p className="text-[10px] text-muted-foreground">{user.email}</p>
            </div>
            <button onClick={logout} className="rounded-md p-1.5 transition-colors hover:bg-muted text-destructive hover:text-destructive/80" title="Sair" aria-label="Deslogar">
              <LogOut className="h-3.5 w-3.5" />
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-2.5">
            <div className="h-7 w-7 rounded-full bg-muted animate-pulse" />
            <div className="flex-1 space-y-1">
              <div className="h-3 w-16 bg-muted rounded animate-pulse" />
              <div className="h-2 w-24 bg-muted rounded animate-pulse" />
            </div>
          </div>
        )}
      </div>
    </aside>
  )
}
