"use client"

import { Report } from "@/lib/api/editor"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { AlertCircle, Lightbulb, MessageSquare, Clock, ArrowRight } from "lucide-react"
import Link from "next/link"
import { cn } from "@/lib/utils"

export function ReportCard({ report }: { report: Report }) {
    const typeConfig: any = {
        bug: { icon: AlertCircle, color: "text-rose-600 bg-rose-50", label: "Bug" },
        melhoria: { icon: Lightbulb, color: "text-amber-600 bg-amber-50", label: "Melhoria" },
        sugestao: { icon: MessageSquare, color: "text-blue-600 bg-blue-50", label: "Sugestão" },
    }

    const priorityConfig: any = {
        alta: "bg-rose-600 text-white border-none",
        media: "bg-amber-500 text-white border-none",
        baixa: "bg-emerald-500 text-white border-none",
    }

    const statusConfig: any = {
        novo: "bg-primary shadow-[0_0_8px_rgba(26,26,46,0.5)]",
        analise: "bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.5)]",
        resolvido: "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]",
    }

    const { icon: Icon, color, label } = typeConfig[report.tipo] || typeConfig.bug

    return (
        <Card className="hover:shadow-2xl hover:-translate-y-1 transition-all duration-300 group border-none bg-card/60 backdrop-blur-sm rounded-[2rem] overflow-hidden">
            <CardContent className="p-6">
                <div className="flex flex-col sm:flex-row items-start justify-between gap-6">
                    <div className="flex-1 min-w-0 space-y-4">
                        <div className="flex flex-wrap items-center gap-2">
                            <div className={cn("flex items-center gap-1.5 px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-wider shadow-sm", color)}>
                                <Icon className="w-3 h-3 stroke-[3px]" />
                                {label}
                            </div>
                            <Badge className={cn("text-[9px] font-black uppercase tracking-widest px-2.5 py-0.5 rounded-full", priorityConfig[report.prioridade])}>
                                {report.prioridade}
                            </Badge>
                            <div className="flex items-center gap-2 px-2.5 py-0.5 bg-muted/40 rounded-full border border-muted-foreground/10">
                                <div className={cn("w-2 h-2 rounded-full animate-pulse", statusConfig[report.status])} />
                                <span className="text-[9px] font-black text-primary/60 uppercase tracking-widest">{report.status}</span>
                            </div>
                        </div>

                        <div className="space-y-1">
                            <h3 className="font-black text-xl tracking-tight text-primary group-hover:text-secondary transition-colors duration-300">
                                {report.titulo}
                            </h3>
                            <p className="text-sm text-muted-foreground font-medium leading-relaxed line-clamp-2 italic">
                                "{report.descricao}"
                            </p>
                        </div>

                        <div className="flex flex-wrap items-center gap-4 pt-2">
                            <div className="flex items-center gap-2">
                                <div className="w-6 h-6 rounded-full bg-accent/20 flex items-center justify-center text-[10px] font-black text-accent uppercase">
                                    {report.colaborador.charAt(0)}
                                </div>
                                <span className="text-[11px] font-black text-primary uppercase tracking-tight">{report.colaborador}</span>
                            </div>
                            <span className="flex items-center gap-1.5 text-[11px] font-bold text-muted-foreground/60 uppercase tracking-tighter">
                                <Clock className="w-3.5 h-3.5" />
                                {new Date(report.created_at).toLocaleDateString()}
                            </span>
                            {report.projeto_id && (
                                <Badge variant="secondary" className="text-[9px] font-black bg-primary/5 text-primary/40 border-none px-2 rounded">
                                    #PROJ-{report.projeto_id}
                                </Badge>
                            )}
                        </div>
                    </div>

                    <div className="flex flex-row sm:flex-col items-center justify-between sm:justify-center gap-4 w-full sm:w-auto mt-4 sm:mt-0 pt-4 sm:pt-0 border-t sm:border-0 border-muted">
                        {report.screenshots.length > 0 && (
                            <div className="relative w-20 h-20 rounded-2xl overflow-hidden border-2 border-muted group-hover:border-secondary transition-colors shadow-lg">
                                <img src={report.screenshots[0]} alt="Screenshot" className="object-cover w-full h-full transform group-hover:scale-110 transition-transform duration-500" />
                                {report.screenshots.length > 1 && (
                                    <div className="absolute inset-0 bg-primary/60 backdrop-blur-[2px] flex items-center justify-center text-[10px] text-white font-black tracking-tighter">
                                        +{report.screenshots.length - 1} ARQUIVOS
                                    </div>
                                )}
                            </div>
                        )}
                        <Link href={`/dashboard/reports/${report.id}`} className="sm:mt-auto">
                            <Button className="h-12 w-12 rounded-2xl bg-muted text-primary hover:bg-secondary hover:text-white transition-all shadow-sm group-hover:scale-110 duration-500">
                                <ArrowRight className="w-5 h-5 stroke-[3px]" />
                            </Button>
                        </Link>
                    </div>
                </div>
            </CardContent>
        </Card>
    )
}

export function ReportSkeleton() {
    return (
        <div className="space-y-4">
            {[1, 2, 3].map(i => (
                <Card key={i} className="animate-pulse">
                    <CardContent className="p-4 flex gap-4">
                        <div className="flex-1 space-y-3">
                            <div className="h-4 w-1/4 bg-muted rounded" />
                            <div className="h-6 w-3/4 bg-muted rounded" />
                            <div className="h-12 w-full bg-muted rounded" />
                        </div>
                        <div className="w-16 h-16 bg-muted rounded" />
                    </CardContent>
                </Card>
            ))}
        </div>
    )
}
