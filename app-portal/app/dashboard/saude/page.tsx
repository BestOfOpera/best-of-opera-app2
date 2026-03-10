"use client"

import { useEffect, useState } from "react"
import { editorApi, DashboardSaude } from "@/lib/api/editor"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Activity, Server, AlertTriangle, ShieldCheck, ArrowRight, ExternalLink } from "lucide-react"
import Link from "next/link"
import { cn } from "@/lib/utils"

export default function SaudePage() {
    const [data, setData] = useState<DashboardSaude | null>(null)
    const [loading, setLoading] = useState(true)

    const fetchSaude = async () => {
        try {
            const res = await editorApi.dashboardSaude()
            setData(res)
        } catch (err) {
            console.error(err)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchSaude()
        const int = setInterval(fetchSaude, 30000)
        return () => clearInterval(int)
    }, [])

    if (loading) return <div className="p-8 animate-pulse grid grid-cols-1 md:grid-cols-2 gap-6"><div className="h-64 bg-muted rounded-xl" /><div className="h-64 bg-muted rounded-xl" /></div>

    return (
        <div className="p-4 md:p-8 max-w-6xl mx-auto space-y-8">
            <header className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Saúde do Sistema</h1>
                    <p className="text-muted-foreground">Monitoramento em tempo real da infraestrutura.</p>
                </div>
                <div className={cn(
                    "flex items-center gap-3 px-4 py-2 rounded-full border-2",
                    data?.semaforo === "verde" ? "bg-emerald-50 border-emerald-500 text-emerald-600" :
                        data?.semaforo === "amarelo" ? "bg-amber-50 border-amber-500 text-amber-600" :
                            "bg-rose-50 border-rose-500 text-rose-600 animate-pulse"
                )}>
                    <div className={cn("w-3 h-3 rounded-full shrink-0",
                        data?.semaforo === "verde" ? "bg-emerald-500" :
                            data?.semaforo === "amarelo" ? "bg-amber-500" : "bg-rose-500"
                    )} />
                    <span className="font-bold uppercase tracking-wider text-sm">
                        {data?.semaforo === "verde" ? "Operacional" : data?.semaforo === "amarelo" ? "Atenção" : "Parado"}
                    </span>
                </div>
            </header>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {/* Worker Card */}
                <Card className="md:col-span-2 lg:col-span-1">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Status do Worker</CardTitle>
                        <Activity className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent className="pt-4">
                        <div className="flex items-end justify-between mb-4">
                            <div>
                                <p className="text-2xl font-bold">{data?.worker.status || "Inativo"}</p>
                                <p className="text-xs text-muted-foreground">Uptime: {data?.worker.uptime || "0h"}</p>
                            </div>
                            <div className="text-right">
                                <span className="text-sm font-medium">{data?.worker.progresso || 0}%</span>
                            </div>
                        </div>
                        <Progress value={data?.worker.progresso || 0} className="h-2" />
                    </CardContent>
                </Card>

                {/* Queue Card */}
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Fila de Processamento</CardTitle>
                        <Server className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent className="pt-4">
                        <div className="text-3xl font-bold">{data?.fila.quantidade || 0}</div>
                        <p className="text-xs text-muted-foreground mt-1">Tarefas aguardando worker</p>
                        <div className="mt-6 border-t pt-4">
                            <p className="text-[10px] uppercase font-bold text-muted-foreground">Próxima Task</p>
                            <p className="text-sm truncate mt-1">{data?.fila.proxima_task || "Fila vazia"}</p>
                        </div>
                    </CardContent>
                </Card>

                {/* System & Sentry */}
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Links do Sistema</CardTitle>
                        <ShieldCheck className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent className="pt-4 space-y-3">
                        <Button variant="outline" className="w-full justify-between" asChild>
                            <a href={data?.sentry_url || "#"} target="_blank" rel="noreferrer">
                                Monitoramento Sentry
                                <ExternalLink className="w-4 h-4" />
                            </a>
                        </Button>
                        <Button variant="outline" className="w-full justify-between">
                            Uptime Dashboard
                            <ExternalLink className="w-4 h-4" />
                        </Button>
                    </CardContent>
                </Card>

                {/* Last Error Card */}
                {data?.ultimo_erro && (
                    <Card className="md:col-span-2 lg:col-span-3 border-rose-200 bg-rose-50/20">
                        <CardHeader className="flex flex-row items-center gap-2">
                            <AlertTriangle className="h-5 w-5 text-rose-500" />
                            <CardTitle className="text-lg text-rose-700">Último Erro Detectado</CardTitle>
                            <Badge variant="outline" className="ml-auto border-rose-300 text-rose-600">
                                Há {data.ultimo_erro.timestamp}
                            </Badge>
                        </CardHeader>
                        <CardContent className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                            <div className="flex-1">
                                <p className="font-mono text-sm bg-background border p-3 rounded-lg text-rose-600 overflow-x-auto">
                                    {data.ultimo_erro.msg}
                                </p>
                            </div>
                            <Link href={`/dashboard/projeto/${data.ultimo_erro.edicao_id}`}>
                                <Button variant="destructive" className="gap-2">
                                    Ver Projeto <ArrowRight className="w-4 h-4" />
                                </Button>
                            </Link>
                        </CardContent>
                    </Card>
                )}
            </div>
        </div>
    )
}
