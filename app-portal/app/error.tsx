"use client"

import { useEffect } from "react"
import { Button } from "@/components/ui/button"
import { AlertTriangle, RefreshCcw, Home } from "lucide-react"
import Link from "next/link"
import * as Sentry from "@sentry/nextjs"

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    // Log the error to Sentry
    Sentry.captureException(error)
    console.error("Global Error Boundary caught:", error)
  }, [error])

  return (
    <div className="flex h-screen w-full flex-col items-center justify-center bg-background p-4 text-center">
      <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-destructive/10 text-destructive shadow-sm">
        <AlertTriangle className="h-10 w-10" />
      </div>
      
      <h2 className="mb-2 text-2xl font-black tracking-tight text-foreground uppercase">
        Ocorreu um erro inesperado
      </h2>
      
      <p className="mb-8 max-w-md text-muted-foreground font-medium leading-relaxed">
        Não conseguimos processar esta página no momento. Os detalhes técnicos foram enviados automaticamente para nossa equipe.
      </p>

      {error.digest && (
        <code className="mb-8 rounded bg-muted px-2 py-1 text-[10px] font-mono text-muted-foreground">
          Error ID: {error.digest}
        </code>
      )}
      
      <div className="flex flex-col sm:flex-row items-center gap-3">
        <Button 
          onClick={() => reset()} 
          size="lg"
          className="rounded-full px-8 font-black gap-2 h-12 shadow-lg shadow-primary/10"
        >
          <RefreshCcw className="h-4 w-4" />
          Tentar Novamente
        </Button>
        
        <Button 
          variant="outline" 
          asChild
          size="lg"
          className="rounded-full px-8 font-black gap-2 h-12"
        >
          <Link href="/">
            <Home className="h-4 w-4" />
            Voltar ao Início
          </Link>
        </Button>
      </div>

      <div className="mt-12 text-[10px] uppercase tracking-[0.2em] text-muted-foreground/30 font-black">
        Best of Opera &bull; System Recovery
      </div>
    </div>
  )
}
