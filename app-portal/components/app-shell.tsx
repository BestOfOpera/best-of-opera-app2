"use client"

import { usePathname } from "next/navigation"
import { AppSidebar } from "@/components/app-sidebar"
import { AppBreadcrumb } from "@/components/app-breadcrumb"
import { BrandSelector } from "@/components/brand-selector"

const breadcrumbMap: Record<string, string[]> = {
  "/curadoria": ["Curadoria", "Dashboard"],
  "/curadoria/resultados": ["Curadoria", "Resultados"],
  "/curadoria/downloads": ["Curadoria", "Downloads"],
  "/redator": ["Redator", "Projetos"],
  "/redator/novo": ["Redator", "Novo Projeto"],
  "/editor": ["Editor", "Fila de Edicao"],
}

function deriveBreadcrumb(pathname: string): string[] {
  if (breadcrumbMap[pathname]) return breadcrumbMap[pathname]
  if (pathname.startsWith("/redator/projeto/")) {
    if (pathname.endsWith("/overlay")) return ["Redator", "Aprovar Overlay"]
    if (pathname.endsWith("/post")) return ["Redator", "Aprovar Post"]
    if (pathname.endsWith("/youtube")) return ["Redator", "Aprovar YouTube"]
    if (pathname.endsWith("/exportar")) return ["Redator", "Exportar"]
    return ["Redator", "Projeto"]
  }
  if (pathname.startsWith("/editor/edicao/")) {
    if (pathname.endsWith("/letra")) return ["Editor", "Validar Letra"]
    if (pathname.endsWith("/alinhamento")) return ["Editor", "Validar Alinhamento"]
    if (pathname.endsWith("/conclusao")) return ["Editor", "Conclusao"]
    return ["Editor", "Edicao"]
  }
  return ["Arias"]
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const breadcrumb = deriveBreadcrumb(pathname)

  return (
    <div className="flex h-screen w-full overflow-hidden">
      <AppSidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex h-12 shrink-0 items-center justify-between border-b border-border bg-card px-8">
          <AppBreadcrumb items={breadcrumb} />
          <BrandSelector />
        </header>
        <main className="flex-1 overflow-y-auto px-8 py-6">{children}</main>
      </div>
    </div>
  )
}
