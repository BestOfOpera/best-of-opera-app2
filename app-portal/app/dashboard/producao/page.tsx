"use client"

import { useEffect, useState } from "react"
import { editorApi, DashboardProducao } from "@/lib/api/editor"
import { useBrand } from "@/lib/brand-context"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { TrendingUp, CheckCircle, Clock, Zap, AlertCircle } from "lucide-react"
import { cn } from "@/lib/utils"

export default function ProducaoPage() {
    const { selectedBrand } = useBrand()
    const [data, setData] = useState<DashboardProducao | null>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        setLoading(true)
        editorApi.dashboardProducao(selectedBrand?.id)
            .then(setData)
            .catch(console.error)
            .finally(() => setLoading(false))
    }, [selectedBrand])

    if (loading) return <div className="p-8 animate-pulse space-y-6"><div className="h-64 bg-muted rounded-xl" /><div className="grid grid-cols-3 gap-4"><div className="h-32 bg-muted rounded" /></div></div>

    return (
        <div className="p-4 md:p-8 max-w-6xl mx-auto space-y-8">
            <header>
                <h1 className="text-3xl font-bold tracking-tight">Relatório de Produção</h1>
                <p className="text-muted-foreground">Eficiência e desempenho dos últimos 30 dias.</p>
            </header>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <MetricCard title="Taxa de Sucesso" value={data?.metricas.taxa_sucesso || "0%"} icon={CheckCircle} color="emerald" />
                <MetricCard title="Tempo Médio" value={data?.metricas.tempo_medio || "0m"} icon={Clock} color="blue" />
                <MetricCard title="Gargalo Atual" value={data?.metricas.gargalo || "Nenhum"} icon={Zap} color="amber" />
            </div>

            <Card>
                <CardHeader>
                    <CardTitle className="text-lg">Projetos por Dia</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="h-[250px] w-full flex items-end gap-1 px-2 pt-4">
                        {data?.grafico.map((item, i) => {
                            const max = Math.max(...data!.grafico.map(g => g.sucesso + g.erro), 1)
                            const successHeight = (item.sucesso / max) * 100
                            const errorHeight = (item.erro / max) * 100

                            return (
                                <div key={i} className="flex-1 flex flex-col justify-end gap-0.5 group relative">
                                    <div
                                        className="bg-rose-500 rounded-sm w-full transition-all group-hover:opacity-80"
                                        style={{ height: `${errorHeight}%` }}
                                    />
                                    <div
                                        className="bg-emerald-500 rounded-sm w-full transition-all group-hover:opacity-80"
                                        style={{ height: `${successHeight}%` }}
                                    />
                                    <div className="absolute -top-12 left-1/2 -translate-x-1/2 bg-popover text-popover-foreground text-[10px] p-1.5 rounded shadow-lg opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-10">
                                        <p className="font-bold">{item.data}</p>
                                        <p className="text-emerald-500">✅ {item.sucesso}</p>
                                        <p className="text-rose-500">❌ {item.erro}</p>
                                    </div>
                                </div>
                            )
                        })}
                    </div>
                    <div className="flex justify-between mt-4 text-[10px] text-muted-foreground font-medium px-2">
                        <span>30 dias atrás</span>
                        <div className="flex gap-4">
                            <span className="flex items-center gap-1.5"><div className="w-2 h-2 rounded bg-emerald-500" /> Sucesso</span>
                            <span className="flex items-center gap-1.5"><div className="w-2 h-2 rounded bg-rose-500" /> Erro</span>
                        </div>
                        <span>Hoje</span>
                    </div>
                </CardContent>
            </Card>

            <Card>
                <CardHeader>
                    <CardTitle className="text-lg">Eficiência por Etapa</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="space-y-4">
                        {data?.etapas.map((etapa, i) => (
                            <div key={i} className="flex items-center justify-between group">
                                <div className="flex-1">
                                    <div className="flex items-center justify-between mb-1.5 text-sm">
                                        <span className="font-medium">{etapa.etapa}</span>
                                        <span className="text-muted-foreground">{etapa.tempo_medio}</span>
                                    </div>
                                    <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden">
                                        <div className="h-full bg-primary/40 rounded-full transition-all group-hover:bg-primary" style={{ width: "50%" }} />
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>
        </div>
    )
}

function MetricCard({ title, value, icon: Icon, color }: any) {
    const colors: any = {
        emerald: "text-emerald-500 bg-emerald-500/10",
        blue: "text-blue-500 bg-blue-500/10",
        amber: "text-amber-500 bg-amber-500/10",
    }
    return (
        <Card>
            <CardContent className="p-6 flex items-center gap-4">
                <div className={cn("p-3 rounded-xl", colors[color])}>
                    <Icon className="w-6 h-6" />
                </div>
                <div>
                    <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{title}</p>
                    <p className="text-2xl font-bold">{value}</p>
                </div>
            </CardContent>
        </Card>
    )
}
