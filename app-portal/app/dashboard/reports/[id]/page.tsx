"use client"

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { editorApi, Report } from "@/lib/api/editor"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { ArrowLeft, Clock, User, Tag, ShieldCheck, CheckCircle2, AlertCircle } from "lucide-react"
import { toast } from "sonner"
import { cn } from "@/lib/utils"

export default function ReportDetalhePage() {
    const { id } = useParams()
    const router = useRouter()
    const [report, setReport] = useState<Report | null>(null)
    const [loading, setLoading] = useState(true)
    const [editing, setEditing] = useState(false)
    const [editData, setEditData] = useState<{ status: "novo" | "analise" | "resolvido"; resolucao: string; codigo_err: string }>({ status: "novo", resolucao: "", codigo_err: "" })

    const fetchReport = async () => {
        try {
            const res = await editorApi.detalheReport(parseInt(id as string))
            setReport(res)
            setEditData({ status: res.status, resolucao: res.resolucao || "", codigo_err: res.codigo_err || "" })
        } catch (err) {
            console.error(err)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchReport()
    }, [id])

    const handleUpdate = async () => {
        try {
            await editorApi.atualizarReport(report!.id, editData)
            toast.success("Report atualizado!")
            setEditing(false)
            fetchReport()
        } catch (err) {
            toast.error("Erro ao atualizar report.")
        }
    }

    if (loading) return <div className="p-8 animate-pulse space-y-4"><div className="h-10 w-48 bg-muted rounded" /><div className="h-64 bg-muted rounded" /></div>
    if (!report) return <div className="p-8 text-center"><p>Report não encontrado.</p></div>

    const statusColors: any = {
        novo: "bg-blue-500 text-white",
        analise: "bg-amber-500 text-white",
        resolvido: "bg-emerald-500 text-white",
    }

    return (
        <div className="p-4 md:p-8 max-w-4xl mx-auto space-y-8">
            <div className="flex items-center gap-4">
                <Button variant="ghost" size="icon" onClick={() => router.back()}><ArrowLeft className="w-5 h-5" /></Button>
                <div className="flex-1">
                    <div className="flex items-center gap-3">
                        <h1 className="text-2xl font-bold">{report.titulo}</h1>
                        <Badge className={cn("uppercase", statusColors[report.status])}>{report.status}</Badge>
                    </div>
                    <div className="flex flex-wrap gap-4 text-xs text-muted-foreground mt-2">
                        <span className="flex items-center gap-1"><User className="w-3 h-3" /> {report.colaborador}</span>
                        <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {new Date(report.created_at).toLocaleString()}</span>
                        <span className="flex items-center gap-1"><Tag className="w-3 h-3" /> {report.tipo.toUpperCase()} • {report.prioridade.toUpperCase()}</span>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                <div className="md:col-span-2 space-y-6">
                    <Card>
                        <CardHeader><CardTitle className="text-sm uppercase tracking-wider text-muted-foreground font-semibold">Descrição</CardTitle></CardHeader>
                        <CardContent>
                            <p className="whitespace-pre-wrap leading-relaxed">{report.descricao}</p>
                        </CardContent>
                    </Card>

                    {report.screenshots.length > 0 && (
                        <Card>
                            <CardHeader><CardTitle className="text-sm uppercase tracking-wider text-muted-foreground font-semibold">Galeria de Evidências</CardTitle></CardHeader>
                            <CardContent>
                                <div className="grid grid-cols-2 gap-4">
                                    {report.screenshots.map((src, i) => (
                                        <div key={i} className="aspect-video rounded-xl overflow-hidden border-2 bg-muted hover:scale-[1.02] transition-transform cursor-pointer shadow-sm">
                                            <img src={src} className="w-full h-full object-cover" alt={`Screenshot ${i + 1}`} onClick={() => window.open(src, "_blank")} />
                                        </div>
                                    ))}
                                </div>
                            </CardContent>
                        </Card>
                    )}
                </div>

                <div className="space-y-6">
                    <Card className={cn("border-2 shadow-lg", report.status === "resolvido" ? "border-emerald-500" : "border-primary/20")}>
                        <CardHeader className="flex flex-row items-center justify-between pb-2">
                            <CardTitle className="text-base font-bold">Resolução</CardTitle>
                            {report.status === "resolvido" ? <CheckCircle2 className="w-5 h-5 text-emerald-500" /> : <ShieldCheck className="w-5 h-5 text-primary" />}
                        </CardHeader>
                        <CardContent className="space-y-4">
                            {editing ? (
                                <>
                                    <div className="space-y-2">
                                        <label className="text-xs font-bold">Status</label>
                                        <Select value={editData.status} onValueChange={v => setEditData({ ...editData, status: v as "novo" | "analise" | "resolvido" })}>
                                            <SelectTrigger><SelectValue /></SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="novo">Novo</SelectItem>
                                                <SelectItem value="analise">Em Análise</SelectItem>
                                                <SelectItem value="resolvido">Resolvido</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                    <div className="space-y-2">
                                        <label className="text-xs font-bold">Resolução/Resposta</label>
                                        <Textarea
                                            placeholder="Explique como foi resolvido..."
                                            rows={4}
                                            value={editData.resolucao}
                                            onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setEditData({ ...editData, resolucao: e.target.value })}
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <label className="text-xs font-bold">Código ERR (Backend)</label>
                                        <Input
                                            placeholder="Ex: ERR_501"
                                            value={editData.codigo_err}
                                            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEditData({ ...editData, codigo_err: e.target.value })}
                                        />
                                    </div>
                                    <div className="flex gap-2 pt-2">
                                        <Button variant="ghost" className="flex-1" onClick={() => setEditing(false)}>Cancelar</Button>
                                        <Button className="flex-1" onClick={handleUpdate}>Salvar</Button>
                                    </div>
                                </>
                            ) : (
                                <div className="space-y-4">
                                    {report.resolucao ? (
                                        <div className="bg-muted/50 p-4 rounded-xl text-sm italic">
                                            {report.resolucao}
                                            <p className="not-italic text-[10px] text-muted-foreground mt-2">Resolvido por: {report.resolvido_por || "Sistema"}</p>
                                        </div>
                                    ) : (
                                        <div className="text-center py-6">
                                            <p className="text-xs text-muted-foreground">Este reporte ainda não possui uma resolução documentada.</p>
                                        </div>
                                    )}
                                    {report.codigo_err && (
                                        <div className="flex items-center gap-2 text-xs font-mono bg-rose-50 border border-rose-100 p-2 rounded-lg text-rose-600">
                                            <AlertCircle className="w-3 h-3" /> {report.codigo_err}
                                        </div>
                                    )}
                                    <Button variant="outline" className="w-full" onClick={() => setEditing(true)}>Editar Resolução</Button>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    )
}
