"use client"

import { use, useState, useEffect, useCallback } from "react"
import { redatorApi, type Project } from "@/lib/api/redator"
import { PipelineStepper } from "@/components/redator/pipeline-stepper"
import { usePathname } from "next/navigation"

export default function ProjetoLayout({
  children,
  params,
}: {
  children: React.ReactNode
  params: Promise<{ id: string }>
}) {
  const { id } = use(params)
  const projectId = Number(id)
  const pathname = usePathname()
  const [project, setProject] = useState<Project | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchProject = useCallback(async () => {
    if (!projectId) return
    try {
      const data = await redatorApi.getProject(projectId)
      setProject(data)
    } catch (error) {
      console.error("Erro ao carregar projeto:", error)
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    fetchProject()
  }, [fetchProject])

  // Refresh stepper data when navigating between sub-routes
  useEffect(() => {
    if (!loading) fetchProject()
  }, [pathname]) // eslint-disable-line react-hooks/exhaustive-deps

  if (loading) {
    return (
      <div>
        <div className="mx-auto max-w-3xl animate-pulse mb-6">
          <div className="h-6 bg-muted rounded w-48 mb-4" />
          <div className="flex gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="flex flex-col items-center gap-1 flex-1">
                <div className="h-8 w-8 rounded-full bg-muted" />
                <div className="h-3 bg-muted rounded w-12" />
              </div>
            ))}
          </div>
        </div>
        {children}
      </div>
    )
  }

  if (!project) {
    return <>{children}</>
  }

  return (
    <div>
      <PipelineStepper projectId={projectId} project={project} />
      {children}
    </div>
  )
}
