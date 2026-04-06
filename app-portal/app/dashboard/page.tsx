"use client"

import { useEffect, useState } from "react"
import { editorApi, DashboardVisaoGeral, Edicao } from "@/lib/api/editor"
import { useAdaptivePolling } from "@/lib/hooks/use-polling"
import { useBrand } from "@/lib/brand-context"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { AlertCircle, CheckCircle2, Clock, PlayCircle, ExternalLink, ArrowRight } from "lucide-react"
import Link from "next/link"
import { cn } from "@/lib/utils"
import { CrossAppKPIs } from "@/components/dashboard/cross-app-kpis"
import { ActivityTimeline } from "@/components/dashboard/activity-timeline"
import { WeeklyProgress } from "@/components/dashboard/weekly-progress"

export default function DashboardPage() {
    const { selectedBrand } = useBrand()
    const [data, setData] = useState<DashboardVisaoGeral | null>(null)
    const [loading, setLoading] = useState(true)
    const [filter, setFilter] = useState("Todos")

    const fetchDashboard = async () => {
        try {
            const res = await editorApi.dashboardVisaoGeral(selectedBrand?.id)
            setData(res)
        } catch (error) {
            console.error("Erro ao carregar dashboard:", error)
        } finally {
            setLoading(false)
        }
    }

    useAdaptivePolling(fetchDashboard, true)

    useEffect(() => {
        setLoading(true)
        fetchDashboard()
    }, [selectedBrand?.id])

    if (loading && !data) {
        return (
            <div className="p-6 space-y-6 animate-pulse">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    {[1, 2, 3, 4].map(i => (
                        <div key={i} className="h-32 bg-muted rounded-xl" />
                    ))}
                </div>
                <div className="space-y-4">
                    {[1, 2, 3].map(i => (
                        <div key={i} className="h-48 bg-muted rounded-xl" />
                    ))}
                </div>
            </div>
        )
    }

    const filteredProjetos = data?.projetos.filter(p => {
        if (filter === "Todos") return true
        if (filter === "Com erro") return p.status === "erro"
        if (filter === "Aguardando ação") return p.status === "aguardando_acao" || p.status === "revisar"
        if (filter === "Em andamento") return p.status === "processando" || p.status === "renderizando"
        if (filter === "Concluídos") return p.status === "concluido"
        return true
    }).sort((a, b) => (a.status === "erro" ? -1 : 1))

    return (
        <div className="p-4 md:p-8 max-w-7xl mx-auto space-y-10 animate-in fade-in duration-500">
            <header className="flex flex-col md:flex-row md:items-end justify-between gap-6 border-b pb-8">
                <div className="space-y-1">
                    <h1 className="text-4xl font-black tracking-tighter text-primary">Operas Ativas</h1>
                    <p className="text-muted-foreground font-medium flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-secondary animate-pulse" />
                        Acompanhe o status e progresso de todos os seus projetos em tempo real.
                    </p>
                </div>
                <div className="flex flex-wrap gap-1.5 p-1.5 bg-muted/40 backdrop-blur-sm rounded-2xl border border-muted-foreground/5 shadow-inner self-start sm:self-end">
                    {["Todos", "Com erro", "Aguardando ação", "Em andamento", "Concluídos"].map(f => (
                        <button
                            key={f}
                            onClick={() => setFilter(f)}
                            className={cn(
                                "px-4 py-2 text-[10px] font-black uppercase tracking-widest rounded-xl transition-all duration-300",
                                filter === f
                                    ? "bg-primary text-white shadow-lg shadow-primary/20 scale-105"
                                    : "text-muted-foreground hover:bg-muted/60 hover:text-primary"
                            )}
                        >
                            {f}
                        </button>
                    ))}
                </div>
            </header>

            {/* ═══ Pipeline Cross-App ═══ */}
            <CrossAppKPIs />
            <ActivityTimeline />
            <WeeklyProgress />

            {/* ═══ Editor — Detalhes ═══ */}
            <h3 className="text-sm font-medium text-muted-foreground mb-3 mt-2">Editor — Detalhes</h3>

            {/* Summary Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-6">
                <SummaryCard
                    title="Total de Edições"
                    value={data?.resumo.total || 0}
                    icon={Clock}
                    color="blue"
                />
                <SummaryCard
                    title="Processando"
                    value={data?.resumo.em_andamento || 0}
                    subtitle={data?.resumo.worker_status}
                    icon={PlayCircle}
                    color="amber"
                    animate={(data?.resumo.em_andamento ?? 0) > 0}
                />
                <SummaryCard
                    title="Concluídos"
                    value={data?.resumo.concluidos || 0}
                    icon={CheckCircle2}
                    color="emerald"
                />
                <SummaryCard
                    title="Alertas / Erros"
                    value={data?.resumo.em_erro || 0}
                    icon={AlertCircle}
                    color="rose"
                    urgent={(data?.resumo.em_erro ?? 0) > 0}
                />
            </div>

            {/* Projects List */}
            <div className="grid grid-cols-1 gap-6">
                {filteredProjetos?.length === 0 ? (
                    <div className="text-center py-24 border-4 border-dashed rounded-[3rem] bg-muted/5 border-muted/20 flex flex-col items-center justify-center space-y-4">
                        <div className="w-20 h-20 bg-muted rounded-full flex items-center justify-center">
                            <Clock className="w-10 h-10 text-muted-foreground/30" />
                        </div>
                        <div className="space-y-1">
                            <p className="text-xl font-black text-primary/40 uppercase tracking-tight">Nenhum projeto encontrado</p>
                            <p className="text-sm text-muted-foreground font-medium">Tente ajustar seus filtros ou importe novos projetos.</p>
                        </div>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 gap-4">
                        {filteredProjetos?.map(projeto => (
                            <ProjectCard key={projeto.id} projeto={projeto} />
                        ))}
                    </div>
                )}
            </div>
        </div>
    )
}

function SummaryCard({ title, value, subtitle, icon: Icon, color, animate, urgent }: any) {
    const colors: any = {
        blue: "text-blue-600 bg-blue-50 border-blue-100",
        amber: "text-amber-600 bg-amber-50 border-amber-100",
        emerald: "text-emerald-600 bg-emerald-50 border-emerald-100",
        rose: "text-rose-600 bg-rose-50 border-rose-100",
    }

    return (
        <Card className={cn(
            "overflow-hidden border-none shadow-sm transition-all hover:shadow-xl hover:-translate-y-1 rounded-3xl group",
            urgent && "animate-pulse-subtle border-l-4 border-l-rose-500"
        )}>
            <CardContent className="p-6">
                <div className="flex items-center justify-between">
                    <div className={cn("p-3 rounded-2xl shadow-inner", colors[color])}>
                        <Icon className={cn("w-6 h-6 stroke-[2.5px]", animate && "animate-spin-[3s_linear_infinite]")} />
                    </div>
                    <span className="text-4xl font-black tracking-tighter text-primary">{value}</span>
                </div>
                <div className="mt-5">
                    <p className="text-[10px] font-black text-muted-foreground uppercase tracking-[0.2em]">{title}</p>
                    {subtitle && (
                        <p className="text-[10px] font-bold text-muted-foreground/60 truncate mt-1 italic">{subtitle}</p>
                    )}
                </div>
            </CardContent>
        </Card>
    )
}

function ProjectCard({ projeto }: { projeto: Edicao & { link_direto: string } }) {
    const isError = projeto.status === "erro"
    const isAguardando = projeto.status === "revisar" || projeto.status === "aguardando_acao"
    const isProcessando = projeto.status === "processando" || projeto.status === "renderizando"

    const flags: Record<string, string> = { pt: "🇧🇷", en: "🇬🇧", es: "🇪🇸", de: "🇩🇪", fr: "🇫🇷", it: "🇮🇹", pl: "🇵🇱" }

    return (
        <Card className={cn(
            "group transition-all hover:shadow-2xl border-none rounded-[2rem] overflow-hidden bg-card/60 backdrop-blur-sm",
            isError ? "bg-rose-50/30" : isAguardando ? "bg-amber-50/30" : ""
        )}>
            <CardContent className="p-6">
                <div className="flex flex-col lg:flex-row gap-6 items-start lg:items-center">
                    <div className="flex-1 min-w-0 space-y-2">
                        <div className="flex items-center gap-3">
                            <h3 className="font-black text-xl tracking-tight text-primary group-hover:text-secondary transition-colors duration-300 truncate">
                                {projeto.artista} — {projeto.musica}
                            </h3>
                            <StatusBadge status={projeto.status} />
                        </div>

                        <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-[11px] font-bold text-muted-foreground uppercase tracking-tight">
                            <span className="flex items-center gap-1.5">
                                <span className="w-2 h-2 rounded-full bg-primary/10" />
                                {projeto.opera || "Opera Experimental"}
                            </span>
                            <span className="flex items-center gap-1.5">
                                <span className="text-lg grayscale group-hover:grayscale-0 transition-all">{flags[projeto.idioma] || "❓"}</span>
                                {projeto.idioma}
                            </span>
                            <span className="flex items-center gap-1.5 px-2 py-0.5 bg-muted/40 rounded italic text-[9px] lowercase font-medium">
                                {projeto.progresso_detalhe ? JSON.stringify(projeto.progresso_detalhe).slice(0, 40) + "..." : "sem rastro"}
                            </span>
                        </div>
                    </div>

                    <div className="flex flex-col sm:flex-row items-center gap-4 w-full lg:w-auto">
                        {isProcessando && (
                            <div className="w-full sm:w-48 space-y-2">
                                <div className="flex justify-between text-[9px] font-black text-primary/40 uppercase tracking-widest">
                                    <span>Passo {projeto.passo_atual || 0} / 9</span>
                                    <span>{Math.round(((projeto.passo_atual || 0) / 9) * 100)}%</span>
                                </div>
                                <Progress value={Math.round(((projeto.passo_atual || 0) / 9) * 100)} className="h-2 bg-muted rounded-full overflow-hidden" />
                            </div>
                        )}

                        <div className="flex gap-3 w-full sm:w-auto">
                            <Link href={`/editor/edicao/${projeto.id}/overview`} className="flex-1 sm:flex-none">
                                <Button variant="outline" size="lg" className="h-12 w-full px-6 rounded-xl border-muted hover:bg-muted hover:text-primary transition-all font-bold gap-2 text-xs">
                                    <ExternalLink className="w-4 h-4" />
                                    Editor
                                </Button>
                            </Link>
                            <Link href={`/dashboard/projeto/${projeto.id}`} className="flex-1 sm:flex-none">
                                <Button size="lg" className="h-12 w-full px-6 rounded-xl bg-primary text-white hover:bg-secondary hover:shadow-lg shadow-primary/10 transition-all font-black uppercase tracking-widest text-[10px] gap-2">
                                    Detalhes
                                    <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
                                </Button>
                            </Link>
                        </div>
                    </div>
                </div>

                {isError && projeto.erro_msg && (
                    <div className="mt-6 p-4 rounded-2xl bg-rose-600/5 text-rose-600 text-xs flex items-start gap-3 border border-rose-600/10 animate-pulse-subtle">
                        <AlertCircle className="w-5 h-5 shrink-0 stroke-[2.5px]" />
                        <div className="space-y-1">
                            <p className="font-black uppercase tracking-widest text-[9px]">Erro do Worker</p>
                            <p className="font-medium italic leading-relaxed">"{projeto.erro_msg}"</p>
                        </div>
                    </div>
                )}
            </CardContent>
        </Card>
    )
}

function StatusBadge({ status }: { status: string }) {
    const styles: any = {
        erro: "bg-rose-600 shadow-rose-500/30",
        concluido: "bg-emerald-500 shadow-emerald-500/30",
        processando: "bg-amber-500 shadow-amber-500/30 animate-pulse",
        renderizando: "bg-secondary shadow-secondary/30 animate-pulse",
        revisar: "bg-primary shadow-primary/30",
        aguardando_acao: "bg-accent shadow-accent/30",
    }

    const labels: any = {
        erro: "Erro",
        concluido: "Concluído",
        processando: "Processando",
        renderizando: "Finalizando",
        revisar: "Revisar",
        aguardando_acao: "Pendente",
    }

    return (
        <Badge className={cn(
            "px-2.5 py-0.5 text-[9px] uppercase font-black tracking-widest rounded-full shadow-lg text-white border-none",
            styles[status] || "bg-muted text-primary"
        )}>
            {labels[status] || status}
        </Badge>
    )
}
