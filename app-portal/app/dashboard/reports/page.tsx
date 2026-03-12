"use client"

import { useEffect, useState, useRef } from "react"
import { editorApi, Report, ReportResumo } from "@/lib/api/editor"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { ReportCard, ReportSkeleton } from "@/components/dashboard/reports/report-card"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog"
import { Plus, X, Upload, CheckCircle2, AlertCircle, Camera, Trash2, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"
import { toast } from "sonner"
import * as Sentry from "@sentry/nextjs"

export default function ReportsPage() {
    const [reports, setReports] = useState<Report[]>([])
    const [resumo, setResumo] = useState<ReportResumo | null>(null)
    const [loading, setLoading] = useState(true)
    const [filter, setFilter] = useState("Todos")
    const [isModalOpen, setIsModalOpen] = useState(false)
    const [confirmLimpar, setConfirmLimpar] = useState(false)
    const [limpando, setLimpando] = useState(false)

    const fetchReports = async () => {
        try {
            const [list, res] = await Promise.all([
                editorApi.listarReports(),
                editorApi.resumoReports()
            ])
            setReports(list)
            setResumo(res)
        } catch (err) {
            console.error(err)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchReports()
    }, [])

    const handleLimparResolvidos = async () => {
        setLimpando(true)
        try {
            const res = await editorApi.deletarReportsResolvidos()
            toast.success(`${res.deleted} report(s) resolvido(s) removido(s).`)
            setConfirmLimpar(false)
            fetchReports()
        } catch (err: any) {
            toast.error("Erro ao limpar resolvidos: " + (err?.message || "desconhecido"))
        } finally {
            setLimpando(false)
        }
    }

    const filtered = reports.filter(r => {
        if (filter === "Todos") return true
        if (filter === "Novos") return r.status === "novo"
        if (filter === "Em análise") return r.status === "analise"
        if (filter === "Resolvidos") return r.status === "resolvido"
        return true
    })

    return (
        <div className="p-4 md:p-8 max-w-6xl mx-auto space-y-10 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <header className="flex flex-col md:flex-row md:items-end justify-between gap-6 border-b pb-8">
                <div className="space-y-1">
                    <h1 className="text-4xl font-black tracking-tighter text-primary">Sistema de Reports</h1>
                    <p className="text-muted-foreground font-medium flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-secondary animate-pulse" />
                        Colabore reportando bugs e sugerindo melhorias para a plataforma.
                    </p>
                </div>
                <Button size="lg" className="px-8 rounded-full shadow-xl shadow-primary/10 hover:shadow-primary/20 transition-all font-black gap-2 h-14" onClick={() => setIsModalOpen(true)}>
                    <Plus className="w-5 h-5 stroke-[3px]" />
                    Reportar Problema
                </Button>
            </header>

            {/* Summary Stats */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
                <ResumoCard label="Novos" value={resumo?.novos || 0} color="rose" active={(resumo?.novos ?? 0) > 0} />
                <ResumoCard label="Em análise" value={resumo?.em_analise || 0} color="amber" />
                <ResumoCard label="Resolvidos" value={resumo?.resolvidos || 0} color="emerald" />
            </div>

            {/* Filters */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 py-2">
                <div className="flex gap-1.5 p-1.5 bg-muted/40 backdrop-blur-sm rounded-2xl w-fit border border-muted-foreground/5 shadow-inner">
                    {["Todos", "Novos", "Em análise", "Resolvidos"].map(f => (
                        <button
                            key={f}
                            onClick={() => setFilter(f)}
                            className={cn(
                                "px-6 py-2 text-xs font-black uppercase tracking-widest rounded-xl transition-all duration-300",
                                filter === f
                                    ? "bg-primary text-white shadow-lg shadow-primary/20 scale-105"
                                    : "text-muted-foreground hover:bg-muted/60 hover:text-primary"
                            )}
                        >
                            {f}
                        </button>
                    ))}
                </div>
                <div className="flex items-center gap-4">
                    {(resumo?.resolvidos ?? 0) > 0 && (
                        <Button
                            variant="outline"
                            size="sm"
                            className="rounded-full text-rose-600 border-rose-200 hover:bg-rose-50 hover:border-rose-300 font-black text-[10px] uppercase tracking-widest gap-1.5"
                            onClick={() => setConfirmLimpar(true)}
                        >
                            <Trash2 className="w-3.5 h-3.5" />
                            Limpar Resolvidos ({resumo?.resolvidos})
                        </Button>
                    )}
                    <div className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/60">
                        Total: {filtered.length} reports encontrados
                    </div>
                </div>
            </div>

            {/* List */}
            <div className="grid grid-cols-1 gap-6">
                {loading ? <ReportSkeleton /> : (
                    filtered.length === 0 ? (
                        <div className="text-center py-24 border-4 border-dashed rounded-[3rem] bg-muted/5 border-muted/20 flex flex-col items-center justify-center space-y-4">
                            <div className="w-20 h-20 bg-muted rounded-full flex items-center justify-center">
                                <AlertCircle className="w-10 h-10 text-muted-foreground/30" />
                            </div>
                            <div className="space-y-1">
                                <p className="text-xl font-black text-primary/40 uppercase tracking-tight">Nenhum report encontrado</p>
                                <p className="text-sm text-muted-foreground font-medium">Tente ajustar seus filtros para ver mais resultados.</p>
                            </div>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-1 gap-4">
                            {filtered.map(report => <ReportCard key={report.id} report={report} onDelete={fetchReports} />)}
                        </div>
                    )
                )}
            </div>

            {isModalOpen && <CreateReportModal onClose={() => {
                setIsModalOpen(false)
                fetchReports()
            }} />}

            <Dialog open={confirmLimpar} onOpenChange={setConfirmLimpar}>
                <DialogContent className="sm:max-w-md">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <Trash2 className="h-5 w-5 text-rose-500" />
                            Limpar reports resolvidos
                        </DialogTitle>
                        <DialogDescription>
                            Isso vai deletar permanentemente {resumo?.resolvidos || 0} report(s) com status &quot;resolvido&quot; e seus screenshots. Esta a&ccedil;&atilde;o &eacute; irrevers&iacute;vel.
                        </DialogDescription>
                    </DialogHeader>
                    <DialogFooter className="gap-2">
                        <Button variant="outline" onClick={() => setConfirmLimpar(false)} disabled={limpando}>Cancelar</Button>
                        <Button variant="destructive" onClick={handleLimparResolvidos} disabled={limpando}>
                            {limpando ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                            Deletar Resolvidos
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    )
}

function ResumoCard({ label, value, color, active }: any) {
    const colors: any = {
        rose: "text-rose-600 bg-rose-50 border-rose-100 shadow-rose-500/5",
        amber: "text-amber-600 bg-amber-50 border-amber-100 shadow-amber-500/5",
        emerald: "text-emerald-600 bg-emerald-50 border-emerald-100 shadow-emerald-500/5",
    }
    return (
        <div className={cn(
            "p-6 rounded-3xl border transition-all hover:scale-105 hover:shadow-2xl flex flex-col items-center justify-center gap-1 group",
            colors[color]
        )}>
            <span className="text-[10px] font-black uppercase tracking-[0.2em] opacity-60 group-hover:opacity-100 transition-opacity">{label}</span>
            <div className="flex items-center gap-3">
                <span className="text-4xl font-black tracking-tighter">{value}</span>
                {active && (
                    <div className="relative flex h-3 w-3">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-current opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-3 w-3 bg-current"></span>
                    </div>
                )}
            </div>
        </div>
    )
}

function CreateReportModal({ onClose }: { onClose: () => void }) {
    const [formData, setFormData] = useState({
        colaborador: "",
        titulo: "",
        descricao: "",
        tipo: "bug" as any,
        prioridade: "media" as any,
        projeto_id: undefined as number | undefined
    })
    const [screenshots, setScreenshots] = useState<File[]>([])
    const [previews, setPreviews] = useState<string[]>([])
    const [submitting, setSubmitting] = useState(false)
    const fileInputRef = useRef<HTMLInputElement>(null)

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = Array.from(e.target.files || [])
        if (files.length + screenshots.length > 5) {
            toast.error("Máximo de 5 screenshots.")
            return
        }

        setScreenshots(prev => [...prev, ...files])
        const newPreviews = files.map(f => URL.createObjectURL(f))
        setPreviews(prev => [...prev, ...newPreviews])
    }

    const removeFile = (index: number) => {
        setScreenshots(prev => prev.filter((_, i) => i !== index))
        setPreviews(prev => prev.filter((_, i) => i !== index))
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!formData.titulo || !formData.descricao || !formData.colaborador) {
            toast.error("Preencha todos os campos obrigatórios.")
            return
        }

        setSubmitting(true)
        try {
            const report = await editorApi.criarReport(formData)

            // Upload screenshots
            if (screenshots.length > 0) {
                await Promise.all(screenshots.map(file => editorApi.uploadScreenshot(report.id, file)))
            }

            Sentry.captureMessage(`[Report] ${formData.titulo}`, {
                level: formData.prioridade === "alta" ? "error" : "warning",
                extra: {
                    report_id: report.id,
                    descricao: formData.descricao,
                    tipo: formData.tipo,
                    prioridade: formData.prioridade,
                    colaborador: formData.colaborador,
                    projeto_id: formData.projeto_id,
                },
            })

            toast.success("Report enviado com sucesso!")
            onClose()
        } catch (err) {
            toast.error("Erro ao enviar report.")
            console.error(err)
        } finally {
            setSubmitting(false)
        }
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-in fade-in duration-300">
            <div className="absolute inset-0 bg-primary/40 backdrop-blur-md" onClick={onClose} />
            <div className="relative bg-card border-none shadow-[0_32px_128px_rgba(0,0,0,0.5)] rounded-[2.5rem] w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
                <div className="p-8 border-b border-muted flex items-center justify-between bg-muted/20">
                    <div className="flex items-center gap-4">
                        <div className="w-12 h-12 bg-primary rounded-2xl flex items-center justify-center shadow-lg">
                            <AlertCircle className="w-6 h-6 text-white" />
                        </div>
                        <div>
                            <h2 className="text-2xl font-black text-primary tracking-tight">Reportar Problema</h2>
                            <p className="text-xs font-bold text-muted-foreground uppercase tracking-widest mt-0.5">Centro de Colaboração</p>
                        </div>
                    </div>
                    <Button variant="ghost" size="icon" onClick={onClose} className="rounded-full hover:bg-muted h-10 w-10">
                        <X className="w-5 h-5" />
                    </Button>
                </div>

                <form className="p-8 space-y-8 overflow-y-auto" onSubmit={handleSubmit}>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="space-y-2">
                            <Label htmlFor="colaborador" className="text-[10px] font-black uppercase tracking-widest text-primary/60 ml-1">Seu Nome *</Label>
                            <Input id="colaborador" required value={formData.colaborador} onChange={e => setFormData({ ...formData, colaborador: e.target.value })} placeholder="Ex: João Silva" className="rounded-xl border-muted bg-muted/10 h-12 focus:ring-secondary/20 focus:border-secondary transition-all" />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="projeto" className="text-[10px] font-black uppercase tracking-widest text-primary/60 ml-1">ID do Projeto (opcional)</Label>
                            <Input id="projeto" type="number" value={formData.projeto_id || ""} onChange={e => setFormData({ ...formData, projeto_id: e.target.value ? parseInt(e.target.value) : undefined })} placeholder="Ex: 48" className="rounded-xl border-muted bg-muted/10 h-12 focus:ring-secondary/20 focus:border-secondary transition-all" />
                        </div>
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="titulo" className="text-[10px] font-black uppercase tracking-widest text-primary/60 ml-1">Título do Problema *</Label>
                        <Input id="titulo" required value={formData.titulo} onChange={e => setFormData({ ...formData, titulo: e.target.value })} placeholder="Resumo curto e claro" className="rounded-xl border-muted bg-muted/10 h-12 focus:ring-secondary/20 focus:border-secondary transition-all" />
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="descricao" className="text-[10px] font-black uppercase tracking-widest text-primary/60 ml-1">Descrição Detalhada *</Label>
                        <Textarea id="descricao" required value={formData.descricao} onChange={e => setFormData({ ...formData, descricao: e.target.value })} placeholder="O que aconteceu? Como podemos reproduzir este erro?" rows={4} className="rounded-2xl border-muted bg-muted/10 min-h-[120px] focus:ring-secondary/20 focus:border-secondary transition-all resize-none" />
                    </div>

                    <div className="grid grid-cols-2 gap-6">
                        <div className="space-y-2">
                            <Label className="text-[10px] font-black uppercase tracking-widest text-primary/60 ml-1">Tipo</Label>
                            <Select value={formData.tipo} onValueChange={v => setFormData({ ...formData, tipo: v as any })}>
                                <SelectTrigger className="rounded-xl h-12 bg-muted/10 border-muted focus:ring-secondary/20 focus:border-secondary transition-all"><SelectValue /></SelectTrigger>
                                <SelectContent className="rounded-xl">
                                    <SelectItem value="bug">🐛 Erro / Bug</SelectItem>
                                    <SelectItem value="melhoria">💡 Melhoria</SelectItem>
                                    <SelectItem value="sugestao">💭 Sugestão</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="space-y-2">
                            <Label className="text-[10px] font-black uppercase tracking-widest text-primary/60 ml-1">Prioridade</Label>
                            <Select value={formData.prioridade} onValueChange={v => setFormData({ ...formData, prioridade: v as any })}>
                                <SelectTrigger className="rounded-xl h-12 bg-muted/10 border-muted focus:ring-secondary/20 focus:border-secondary transition-all"><SelectValue /></SelectTrigger>
                                <SelectContent className="rounded-xl">
                                    <SelectItem value="alta" className="text-rose-600 font-bold">🔴 Alta</SelectItem>
                                    <SelectItem value="media" className="text-amber-500 font-bold">🟡 Média</SelectItem>
                                    <SelectItem value="baixa" className="text-emerald-500 font-bold">🟢 Baixa</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    <div className="space-y-4">
                        <Label className="text-[10px] font-black uppercase tracking-widest text-primary/60 ml-1">Screenshots (Máximo 5)</Label>
                        <div
                            className="border-4 border-dashed rounded-3xl p-8 flex flex-col items-center justify-center gap-3 hover:bg-muted/30 border-muted/50 hover:border-secondary/30 cursor-pointer transition-all group"
                            onClick={() => fileInputRef.current?.click()}
                        >
                            <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center group-hover:scale-110 transition-transform duration-500 shadow-inner">
                                <Upload className="w-8 h-8 text-muted-foreground group-hover:text-secondary transition-colors" />
                            </div>
                            <div className="text-center">
                                <p className="text-sm font-black text-primary uppercase tracking-tight">Clique para escanear ou carregar</p>
                                <p className="text-[10px] text-muted-foreground font-bold uppercase tracking-widest mt-1">Formatos suportados: PNG, JPG, WEBP</p>
                            </div>
                            <input type="file" ref={fileInputRef} className="hidden" multiple accept="image/*" onChange={handleFileChange} />
                        </div>

                        {previews.length > 0 && (
                            <div className="grid grid-cols-5 gap-3 pt-2">
                                {previews.map((src, i) => (
                                    <div key={i} className="relative aspect-square rounded-xl overflow-hidden border-2 border-muted hover:border-secondary transition-all group/item shadow-lg">
                                        <img src={src} className="object-cover w-full h-full transform group-hover/item:scale-110 transition-transform duration-500" alt="Preview" />
                                        <button
                                            type="button"
                                            className="absolute top-1 right-1 bg-black/50 text-white rounded-full p-1 opacity-0 group-hover/item:opacity-100 transition-opacity"
                                            onClick={(e) => { e.stopPropagation(); removeFile(i); }}
                                        >
                                            <X className="w-3 h-3" />
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    <div className="flex justify-end gap-3 pt-6 border-t border-muted">
                        <Button variant="ghost" type="button" onClick={onClose} disabled={submitting} className="rounded-full px-6 font-bold">Cancelar</Button>
                        <Button type="submit" disabled={submitting} className="rounded-full px-12 h-12 bg-primary text-white font-black uppercase tracking-widest shadow-xl shadow-primary/20 hover:shadow-primary/40 hover:-translate-y-1 transition-all">
                            {submitting ? "Sincronizando..." : "Enviar Report Final"}
                        </Button>
                    </div>
                </form>
            </div>
        </div>
    )
}
