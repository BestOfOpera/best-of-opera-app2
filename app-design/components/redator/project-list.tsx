"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { StatusBadge } from "@/components/status-badge"
import { Plus, Music } from "lucide-react"
import { redatorApi, type Project } from "@/lib/api/redator"

function nextStepLink(p: Project): string {
  if (p.status === "input_complete" || p.status === "generating") return `/redator/projeto/${p.id}/overlay`
  if (!p.overlay_approved) return `/redator/projeto/${p.id}/overlay`
  if (!p.post_approved) return `/redator/projeto/${p.id}/post`
  if (!p.youtube_approved) return `/redator/projeto/${p.id}/youtube`
  return `/redator/projeto/${p.id}/exportar`
}

export function RedatorProjectList() {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    redatorApi.listProjects().then(setProjects).finally(() => setLoading(false))
  }, [])

  if (loading) {
    return <div className="flex items-center justify-center py-12 text-sm text-muted-foreground">Carregando projetos...</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-foreground">Projetos</h1>
          <p className="text-sm text-muted-foreground">{projects.length} projetos</p>
        </div>
        <Link href="/redator/novo">
          <Button size="sm">
            <Plus className="mr-2 h-3.5 w-3.5" />
            Novo Projeto
          </Button>
        </Link>
      </div>

      {projects.length === 0 ? (
        <Card className="text-center">
          <CardContent className="py-12">
            <p className="text-sm text-muted-foreground mb-4">Nenhum projeto ainda.</p>
            <Link href="/redator/novo">
              <Button>Crie seu primeiro projeto</Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {projects.map((project) => (
            <Link key={project.id} href={nextStepLink(project)}>
              <Card className="cursor-pointer transition-colors hover:bg-muted/20">
                <CardContent className="flex items-center gap-4 p-4">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                    <Music className="h-5 w-5 text-primary" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-foreground">{project.artist} — {project.work}</p>
                    <p className="text-xs text-muted-foreground">
                      {project.composer} {project.category ? `· ${project.category}` : ""}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 text-right text-xs text-muted-foreground">
                    {project.overlay_approved && <span className="text-emerald-600">Legendas OK</span>}
                    {project.post_approved && <span className="text-emerald-600">Post OK</span>}
                    {project.youtube_approved && <span className="text-emerald-600">YouTube OK</span>}
                  </div>
                  <StatusBadge status={project.status as any} />
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
