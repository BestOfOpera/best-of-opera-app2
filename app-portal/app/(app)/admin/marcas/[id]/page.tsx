"use client"

import { useState, useEffect } from "react"
import { useParams, useRouter } from "next/navigation"
import Link from "next/link"
import { editorApi, type Perfil } from "@/lib/api/editor"
import { useAuth } from "@/lib/auth-context"
import { toast } from "sonner"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { Loader2, ArrowLeft, Save, Globe, Eye, CopyPlus } from "lucide-react"

export default function MarcaConfigPage() {
    const { id } = useParams()
    const router = useRouter()
    const { isAdmin } = useAuth()
    const [loading, setLoading] = useState(true)
    const [saving, setSaving] = useState(false)

    const [formData, setFormData] = useState<Partial<Perfil>>({})

    useEffect(() => {
        if (id) loadPerfil()
    }, [id])

    const loadPerfil = async () => {
        try {
            const data = await editorApi.detalharPerfil(Number(id))
            setFormData(data)
        } catch (err: any) {
            toast.error("Erro ao carregar marca: " + err.message)
            router.push("/admin/marcas")
        } finally {
            setLoading(false)
        }
    }

    const handleChange = (field: keyof Perfil, value: any) => {
        setFormData(prev => ({ ...prev, [field]: value }))
    }

    const handleJSONChange = (field: "overlay_style" | "lyrics_style" | "traducao_style", text: string) => {
        try {
            if (!text.trim()) {
                handleChange(field, {})
                return
            }
            const parsed = JSON.parse(text)
            handleChange(field, parsed)
        } catch (err) {
            // Ignore err on fly
        }
    }

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault()
        setSaving(true)
        try {
            await editorApi.atualizarPerfil(Number(id), formData)
            toast.success("Configurações da marca salvas!")
            loadPerfil()
        } catch (err: any) {
            toast.error("Erro ao salvar marca: " + err.message)
        } finally {
            setSaving(false)
        }
    }

    const handleToggleAtivo = async () => {
        try {
            await editorApi.atualizarPerfilParcial(Number(id), { ativo: !formData.ativo })
            toast.success(`Marca ${!formData.ativo ? "ativada" : "desativada"}!`)
            loadPerfil()
        } catch (err: any) {
            toast.error("Erro ao alterar status: " + err.message)
        }
    }

    if (loading) {
        return <div className="flex h-[50vh] items-center justify-center"><Loader2 className="h-8 w-8 animate-spin text-muted-foreground" /></div>
    }

    return (
        <div className="mx-auto max-w-5xl space-y-6 pb-20">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div className="flex items-center gap-4">
                    <Button variant="ghost" size="icon" asChild className="shrink-0">
                        <Link href="/admin/marcas"><ArrowLeft className="h-4 w-4" /></Link>
                    </Button>
                    <div>
                        <div className="flex items-center gap-3">
                            <h1 className="text-2xl font-bold tracking-tight">Configurar {formData.nome}</h1>
                            <Badge variant={formData.ativo ? "default" : "secondary"} className="capitalize">
                                {formData.ativo ? "Ativa" : "Inativa"}
                            </Badge>
                        </div>
                        <p className="text-sm text-muted-foreground mt-1">ID: {formData.id} • Criada em: {formData.created_at ? new Date(formData.created_at).toLocaleDateString() : "—"}</p>
                    </div>
                </div>
                <div className="flex gap-2 shrink-0">
                    <Button variant="outline" size="sm" onClick={handleToggleAtivo}>
                        {formData.ativo ? "Desativar Marca" : "Reativar Marca"}
                    </Button>
                </div>
            </div>

            <form onSubmit={handleSave} className="space-y-6">
                <Card>
                    <CardHeader>
                        <CardTitle className="text-lg">Configurações Gerais</CardTitle>
                    </CardHeader>
                    <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label>Nome da Marca *</Label>
                            <Input required value={formData.nome || ""} onChange={e => handleChange("nome", e.target.value)} />
                        </div>
                        <div className="space-y-2">
                            <Label>Slug *</Label>
                            <Input required value={formData.slug || ""} onChange={e => handleChange("slug", e.target.value)} />
                        </div>
                        <div className="space-y-2">
                            <Label>Sigla *</Label>
                            <Input required value={formData.sigla || ""} onChange={e => handleChange("sigla", e.target.value)} maxLength={4} />
                        </div>
                        <div className="space-y-2">
                            <Label>Prefixo Cloudflare R2 *</Label>
                            <Input required value={formData.r2_prefix || ""} onChange={e => handleChange("r2_prefix", e.target.value)} />
                        </div>
                        <div className="space-y-2">
                            <Label>Cor Primária (Hex)</Label>
                            <div className="flex gap-2">
                                <Input type="color" className="w-12 h-10 p-1" value={formData.cor_primaria || "#3b82f6"} onChange={e => handleChange("cor_primaria", e.target.value)} />
                                <Input value={formData.cor_primaria || ""} onChange={e => handleChange("cor_primaria", e.target.value)} placeholder="#3b82f6" />
                            </div>
                        </div>
                        <div className="space-y-2">
                            <Label>Cor Secundária (Hex)</Label>
                            <div className="flex gap-2">
                                <Input type="color" className="w-12 h-10 p-1" value={formData.cor_secundaria || "#1e40af"} onChange={e => handleChange("cor_secundaria", e.target.value)} />
                                <Input value={formData.cor_secundaria || ""} onChange={e => handleChange("cor_secundaria", e.target.value)} placeholder="#1e40af" />
                            </div>
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle className="text-lg">Idiomas</CardTitle>
                    </CardHeader>
                    <CardContent className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        <div className="space-y-2">
                            <Label>Idiomas Alvo</Label>
                            <Input value={formData.idiomas_alvo || ""} onChange={e => handleChange("idiomas_alvo", e.target.value)} />
                        </div>
                        <div className="space-y-2">
                            <Label>Idioma Base (Postagem)</Label>
                            <Input value={formData.editorial_lang || ""} onChange={e => handleChange("editorial_lang", e.target.value)} />
                        </div>
                        <div className="space-y-2">
                            <Label>Idioma de Preview</Label>
                            <Input value={formData.idioma_preview || ""} onChange={e => handleChange("idioma_preview", e.target.value)} />
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle className="text-lg">Prompts & Editorial</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="space-y-2">
                            <Label>Identity Prompt (LLM)</Label>
                            <Textarea
                                value={formData.identity_prompt || ""}
                                onChange={e => handleChange("identity_prompt", e.target.value)}
                                className="min-h-[100px]"
                            />
                        </div>
                        <div className="space-y-2">
                            <Label>Tom de Voz</Label>
                            <Input value={formData.tom_voz || ""} onChange={e => handleChange("tom_voz", e.target.value)} />
                        </div>
                        <div className="space-y-2">
                            <Label>Escopo de Conteúdo</Label>
                            <Textarea
                                value={formData.escopo_conteudo || ""}
                                onChange={e => handleChange("escopo_conteudo", e.target.value)}
                                className="min-h-[80px]"
                            />
                        </div>
                        <div className="space-y-2">
                            <Label>Categorias/Ganchos Frequentes</Label>
                            <Input value={formData.categorias_hook || ""} onChange={e => handleChange("categorias_hook", e.target.value)} />
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle className="text-lg">Estilos JSON & Vídeo</CardTitle>
                    </CardHeader>
                    <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="grid grid-cols-2 gap-4 md:col-span-2">
                            <div className="space-y-2">
                                <Label>Largura Vídeo</Label>
                                <Input type="number" required value={formData.video_width || 1080} onChange={e => handleChange("video_width", parseInt(e.target.value))} />
                            </div>
                            <div className="space-y-2">
                                <Label>Altura Vídeo</Label>
                                <Input type="number" required value={formData.video_height || 1920} onChange={e => handleChange("video_height", parseInt(e.target.value))} />
                            </div>
                            <div className="space-y-2">
                                <Label>Duração Min (s)</Label>
                                <Input type="number" required value={formData.duracao_min_sec || 45} onChange={e => handleChange("duracao_min_sec", parseInt(e.target.value))} />
                            </div>
                            <div className="space-y-2">
                                <Label>Duração Máx (s)</Label>
                                <Input type="number" required value={formData.duracao_max_sec || 90} onChange={e => handleChange("duracao_max_sec", parseInt(e.target.value))} />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <Label>JSON - Overlay</Label>
                            <Textarea
                                defaultValue={JSON.stringify(formData.overlay_style || {}, null, 2)}
                                onChange={e => handleJSONChange("overlay_style", e.target.value)}
                                className="font-mono text-xs min-h-[150px]"
                            />
                        </div>
                        <div className="space-y-2">
                            <Label>JSON - Letra Principal</Label>
                            <Textarea
                                defaultValue={JSON.stringify(formData.lyrics_style || {}, null, 2)}
                                onChange={e => handleJSONChange("lyrics_style", e.target.value)}
                                className="font-mono text-xs min-h-[150px]"
                            />
                        </div>
                        <div className="space-y-2 md:col-span-2">
                            <Label>JSON - Tradução Lateral</Label>
                            <Textarea
                                defaultValue={JSON.stringify(formData.traducao_style || {}, null, 2)}
                                onChange={e => handleJSONChange("traducao_style", e.target.value)}
                                className="font-mono text-xs min-h-[150px]"
                            />
                        </div>
                    </CardContent>
                </Card>

                <div className="fixed bottom-0 left-0 lg:left-[240px] right-0 p-4 bg-background/80 backdrop-blur-sm border-t border-border flex justify-end gap-3 z-20">
                    <Button type="button" variant="outline" onClick={() => router.push("/admin/marcas")}>
                        Cancelar
                    </Button>
                    <Button type="submit" size="default" disabled={saving}>
                        {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
                        {saving ? "Salvando..." : "Salvar Configurações"}
                    </Button>
                </div>
            </form>
        </div>
    )
}
