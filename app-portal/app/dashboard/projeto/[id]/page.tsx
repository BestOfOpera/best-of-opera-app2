"use client"

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { editorApi, Edicao, DashboardR2Inventario, Render } from "@/lib/api/editor"

function deriveInventario(renders: Render[]): DashboardR2Inventario {
    const arquivos = renders.map(r => ({
        nome: `video_${r.idioma}.mp4`,
        status: (r.status === "concluido" ? "ok" : r.status === "erro" ? "erro" : "falta") as "ok" | "falta" | "erro",
        tamanho: r.tamanho_bytes ? `${(r.tamanho_bytes / 1024 / 1024).toFixed(1)} MB` : undefined,
    }))
    return {
        categorias: arquivos.length > 0 ? [{
            nome: "Vídeos Renderizados",
            arquivos,
            concluido: renders.length > 0 && renders.every(r => r.status === "concluido"),
        }] : [],
        total_arquivos: renders.filter(r => r.status === "concluido").length,
        total_tamanho: `${(renders.reduce((acc, r) => acc + (r.tamanho_bytes || 0), 0) / 1024 / 1024).toFixed(1)} MB`,
    }
}
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ArrowLeft, ExternalLink, Download, FileText, Video, Music, CheckCircle2, AlertCircle, Clock, ChevronRight } from "lucide-react"
import Link from "next/link"
import { cn } from "@/lib/utils"

export default function ProjetoDetalhePage() {
    const { id } = useParams()
    const router = useRouter()
    const [projeto, setProjeto] = useState<Edicao | null>(null)
    const [inventario, setInventario] = useState<DashboardR2Inventario | null>(null)
    const [renders, setRenders] = useState<Render[]>([])
    const [loading, setLoading] = useState(true)

    const fetchData = async () => {
        try {
            const projId = parseInt(id as string)
            const [projetoResult, rendersResult] = await Promise.allSettled([
                editorApi.dashboardProjeto(projId),
                editorApi.listarRenders(projId),
            ])
            const p = projetoResult.status === "fulfilled" ? projetoResult.value : null
            const rend = rendersResult.status === "fulfilled" ? rendersResult.value : []
            setProjeto(p)
            setRenders(rend)
            setInventario(deriveInventario(rend))
        } catch (error) {
            console.error("Erro ao carregar projeto:", error)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchData()
    }, [id])

    if (loading) return (
        <div className="p-4 md:p-8 max-w-6xl mx-auto space-y-8 animate-pulse">
            <div className="h-10 w-64 bg-muted rounded-lg" />
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <div className="h-96 bg-muted rounded-2xl" />
                <div className="lg:col-span-2 h-96 bg-muted rounded-2xl" />
            </div>
        </div>
    )

    if (!projeto) return (
        <div className="p-8 text-center flex flex-col items-center justify-center min-h-[50vh] space-y-4">
            <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center">
                <AlertCircle className="w-8 h-8 text-muted-foreground" />
            </div>
            <p className="text-xl font-medium text-muted-foreground">Projeto não encontrado.</p>
            <Button onClick={() => router.push("/dashboard")}>Voltar ao Dashboard</Button>
        </div>
    )

    const steps = [
        { label: "Importação", status: "concluido" },
        { label: "Transcrição", status: projeto.passo_atual > 1 ? "concluido" : projeto.passo_atual === 1 ? "em_andamento" : "pendente" },
        { label: "Tradução", status: projeto.passo_atual > 2 ? "concluido" : projeto.passo_atual === 2 ? "em_andamento" : "pendente" },
        { label: "Renderização", status: projeto.passo_atual > 3 ? "concluido" : projeto.passo_atual === 3 ? "em_andamento" : "pendente" },
        { label: "Pacote Final", status: projeto.passo_atual > 4 ? "concluido" : projeto.passo_atual === 4 ? "em_andamento" : "pendente" },
    ]

    const flags: Record<string, string> = { pt: "🇧🇷", en: "🇬🇧", es: "🇪🇸", de: "🇩🇪", fr: "🇫🇷", it: "🇮🇹", pl: "🇵🇱" }

    const getFileIcon = (category: string) => {
        const lower = category.toLowerCase()
        if (lower.includes("video")) return <Video className="w-4 h-4" />
        if (lower.includes("audio") || lower.includes("music")) return <Music className="w-4 h-4" />
        if (lower.includes("legenda") || lower.includes("texto")) return <FileText className="w-4 h-4" />
        return <FileText className="w-4 h-4" />
    }

    return (
        <div className="p-4 md:p-8 max-w-6xl mx-auto space-y-8 animate-in fade-in duration-500">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 border-b pb-6">
                <div className="flex items-center gap-4">
                    <Button variant="ghost" size="icon" onClick={() => router.back()} className="rounded-full hover:bg-muted">
                        <ArrowLeft className="w-5 h-5" />
                    </Button>
                    <div>
                        <div className="flex items-center gap-3">
                            <h1 className="text-3xl font-black tracking-tight text-primary">{projeto.artista} — {projeto.musica}</h1>
                            <Badge className="bg-secondary text-secondary-foreground hover:bg-secondary/90 uppercase text-[10px] font-bold px-2 py-0.5">
                                {projeto.status}
                            </Badge>
                        </div>
                        <p className="text-muted-foreground font-medium mt-1 flex items-center gap-2">
                            <span className="w-1 h-1 rounded-full bg-primary/20" />
                            {projeto.opera}
                        </p>
                    </div>
                </div>
                <Link href={`/editor/${projeto.id}`}>
                    <Button className="gap-2 px-6 rounded-full shadow-lg hover:shadow-primary/20 transition-all font-bold">
                        <ExternalLink className="w-4 h-4" />
                        Abrir no Editor
                    </Button>
                </Link>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Timeline & Status */}
                <div className="lg:col-span-1 space-y-6">
                    <Card className="border-none shadow-sm bg-card/50 backdrop-blur-sm rounded-2xl overflow-hidden">
                        <CardHeader className="bg-primary/5 py-4">
                            <CardTitle className="text-xs font-black uppercase tracking-widest text-primary/60">Progresso do Workflow</CardTitle>
                        </CardHeader>
                        <CardContent className="pt-6">
                            <div className="space-y-0 relative before:content-[''] before:absolute before:left-[17px] before:top-2 before:bottom-2 before:w-[2px] before:bg-muted">
                                {steps.map((step, i) => (
                                    <div key={i} className="relative pl-12 pb-10 last:pb-0 group">
                                        <div className={cn(
                                            "absolute left-0 top-0 w-9 h-9 rounded-full border-4 flex items-center justify-center bg-background z-10 transition-all duration-500",
                                            step.status === "concluido" ? "border-success text-success scale-100 shadow-success/20 shadow-lg" :
                                                step.status === "em_andamento" ? "border-secondary text-secondary animate-pulse shadow-secondary/20 shadow-lg" :
                                                    "border-muted text-muted-foreground scale-90"
                                        )}>
                                            {step.status === "concluido" ? <CheckCircle2 className="w-4 h-4 stroke-[3px]" /> :
                                                step.status === "em_andamento" ? <Clock className="w-4 h-4 stroke-[3px]" /> :
                                                    <div className="w-2 h-2 rounded-full bg-muted" />}
                                        </div>
                                        <div className="translate-y-1">
                                            <h4 className={cn(
                                                "font-bold text-sm transition-colors",
                                                step.status === "pendente" ? "text-muted-foreground" : "text-primary"
                                            )}>{step.label}</h4>
                                            <p className="text-[11px] text-muted-foreground leading-relaxed mt-0.5 font-medium">
                                                {step.status === "concluido" ? "Etapa finalizada com sucesso" :
                                                    step.status === "em_andamento" ? "Processando no Worker..." : "Aguardando etapas anteriores"}
                                            </p>
                                        </div>
                                        {step.status === "em_andamento" && (
                                            <div className="absolute left-[34px] top-[40px] w-1 h-8 bg-gradient-to-b from-secondary to-transparent animate-pulse" />
                                        )}
                                    </div>
                                ))}
                            </div>
                        </CardContent>
                    </Card>

                    <Card className="border-none shadow-sm rounded-2xl">
                        <CardHeader className="py-4">
                            <CardTitle className="text-xs font-black uppercase tracking-widest text-muted-foreground flex items-center justify-between">
                                Traduções Disponíveis
                                <Badge variant="outline" className="text-[9px] border-muted-foreground/20">{Object.keys(flags).length} Idiomas</Badge>
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="grid grid-cols-4 gap-3">
                            {Object.entries(flags).map(([lang, flag]) => (
                                <div key={lang} className={cn(
                                    "flex flex-col items-center gap-1.5 p-2 rounded-xl transition-all border group",
                                    projeto.passo_atual > 2 ? "bg-success/5 border-success/20" : "bg-muted/30 border-transparent"
                                )}>
                                    <span className="text-2xl group-hover:scale-125 transition-transform duration-300 pointer-events-none">{flag}</span>
                                    <span className={cn(
                                        "text-[9px] font-black uppercase",
                                        projeto.passo_atual > 2 ? "text-success" : "text-muted-foreground/50"
                                    )}>
                                        {lang}
                                    </span>
                                </div>
                            ))}
                        </CardContent>
                    </Card>
                </div>

                {/* Inventory & Renders */}
                <div className="lg:col-span-2 space-y-8">
                    <Card className="border-none shadow-sm rounded-2xl overflow-hidden">
                        <CardHeader className="bg-accent/5 flex flex-row items-center justify-between py-5 px-6">
                            <div className="flex items-center gap-3">
                                <div className="p-2 bg-accent/10 rounded-lg">
                                    <Download className="w-5 h-5 text-accent" />
                                </div>
                                <div>
                                    <CardTitle className="text-lg font-black text-primary">Inventário R2</CardTitle>
                                    <p className="text-[10px] text-muted-foreground font-bold tracking-tight uppercase">Storage Cloud / Asset Tracking</p>
                                </div>
                            </div>
                            <div className="text-right">
                                <p className="text-xl font-black text-primary leading-tight">{inventario?.total_arquivos || 0}</p>
                                <p className="text-[10px] text-muted-foreground font-bold uppercase">{inventario?.total_tamanho || "0.0 MB"}</p>
                            </div>
                        </CardHeader>
                        <CardContent className="p-6 space-y-6">
                            {inventario?.categorias.map((cat, i) => (
                                <div key={i} className="group border border-muted-foreground/10 rounded-2xl overflow-hidden hover:border-accent/30 transition-colors">
                                    <div className={cn(
                                        "px-4 py-3 border-b flex items-center justify-between",
                                        cat.concluido ? "bg-success/5" : "bg-warning/5"
                                    )}>
                                        <div className="flex items-center gap-2">
                                            <div className={cn(
                                                "p-1.5 rounded-lg",
                                                cat.concluido ? "bg-success/10 text-success" : "bg-warning/10 text-warning"
                                            )}>
                                                {getFileIcon(cat.nome)}
                                            </div>
                                            <span className="text-sm font-black text-primary uppercase tracking-tight">
                                                {cat.nome}
                                            </span>
                                        </div>
                                        {cat.concluido ? (
                                            <Badge className="bg-success/10 text-success border-none text-[10px] gap-1 font-bold">
                                                <CheckCircle2 className="w-3 h-3" /> OK
                                            </Badge>
                                        ) : (
                                            <Badge className="bg-warning/10 text-warning border-none text-[10px] gap-1 font-bold animate-pulse-subtle">
                                                <AlertCircle className="w-3 h-3" /> PENDENTE
                                            </Badge>
                                        )}
                                    </div>
                                    <div className="divide-y divide-muted-foreground/5 bg-muted/10">
                                        {cat.arquivos.map((file, j) => (
                                            <div key={j} className="px-4 py-2.5 flex items-center justify-between text-xs hover:bg-background transition-colors group/row">
                                                <span className="flex items-center gap-3 font-medium text-muted-foreground group-hover/row:text-primary transition-colors">
                                                    <span className={cn(
                                                        "w-1.5 h-1.5 rounded-full",
                                                        file.status === "ok" ? "bg-success shadow-[0_0_8px_rgba(16,185,129,0.5)]" :
                                                            file.status === "falta" ? "bg-warning animate-pulse" : "bg-destructive"
                                                    )} />
                                                    {file.nome}
                                                </span>
                                                <span className="text-muted-foreground/60 font-mono text-[10px] flex items-center gap-2">
                                                    {file.tamanho || "--"}
                                                    <ChevronRight className="w-3 h-3 opacity-0 group-hover/row:opacity-100 transition-opacity" />
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            ))}
                        </CardContent>
                    </Card>

                    <Card className="border-none shadow-xl shadow-primary/5 rounded-2xl overflow-hidden border-t-4 border-t-success">
                        <CardHeader className="py-5 px-6">
                            <CardTitle className="text-lg font-black text-primary flex items-center gap-2">
                                <Video className="w-5 h-5 text-success" />
                                Renderizações Finais
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="p-6">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {renders.length === 0 ? (
                                    <div className="col-span-2 py-12 flex flex-col items-center gap-3 bg-muted/20 rounded-2xl border border-dashed border-muted-foreground/20">
                                        <div className="w-12 h-12 bg-muted rounded-full flex items-center justify-center">
                                            <Video className="w-6 h-6 text-muted-foreground/50" />
                                        </div>
                                        <p className="text-sm font-bold text-muted-foreground">Nenhum render concluído ainda.</p>
                                    </div>
                                ) : (
                                    renders.map(render => (
                                        <div key={render.id} className="flex items-center justify-between p-4 bg-background border border-muted hover:border-success/30 hover:shadow-lg hover:shadow-success/5 transition-all rounded-2xl group/card">
                                            <div className="flex items-center gap-4">
                                                <div className="text-3xl filter grayscale group-hover:grayscale-0 transition-all duration-500 scale-100 group-hover:scale-110">
                                                    {flags[render.idioma] || "❓"}
                                                </div>
                                                <div>
                                                    <div className="flex items-center gap-2">
                                                        <h4 className="text-sm font-black text-primary uppercase">{render.idioma}</h4>
                                                        <Badge variant="outline" className="text-[8px] h-3.5 px-1 font-black text-success border-success/30 bg-success/5 uppercase">
                                                            Concluído
                                                        </Badge>
                                                    </div>
                                                    <p className="text-[10px] text-muted-foreground font-mono mt-0.5">
                                                        {(render.tamanho_bytes ? (render.tamanho_bytes / 1024 / 1024).toFixed(1) : "0")} MB
                                                    </p>
                                                </div>
                                            </div>
                                            <Button variant="ghost" size="icon" className="h-10 w-10 rounded-xl hover:bg-success hover:text-white transition-all shadow-sm" disabled={!render.arquivo} asChild>
                                                <a href={editorApi.downloadRenderUrl(projeto.id, render.id)} target="_blank" rel="noreferrer">
                                                    <Download className="w-4 h-4" />
                                                </a>
                                            </Button>
                                        </div>
                                    ))
                                )}
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    )
}
