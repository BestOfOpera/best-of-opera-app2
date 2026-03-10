"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { editorApi, type Perfil } from "@/lib/api/editor"
import { useAuth } from "@/lib/auth-context"
import { toast } from "sonner"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Loader2, ArrowLeft, Save, Globe, Eye } from "lucide-react"

export default function NovaMarcaPage() {
    const router = useRouter()
    const { isAdmin } = useAuth()
    const [loading, setLoading] = useState(false)
    const [previewing, setPreviewing] = useState(false)
    const [previewUrl, setPreviewUrl] = useState<string | null>(null)

    const [formData, setFormData] = useState<Partial<Perfil>>({
        nome: "",
        sigla: "",
        slug: "",
        ativo: true,
        cor_primaria: "#3b82f6",
        cor_secundaria: "#1e40af",
        video_width: 1080,
        video_height: 1920,
        duracao_min_sec: 45,
        duracao_max_sec: 90,
        r2_prefix: "",
        idiomas_alvo: "pt,en,es",
        idioma_preview: "pt",
        editorial_lang: "pt-br",
        identity_prompt: "",
        tom_voz: "",
        categorias_hook: "",
        escopo_conteudo: "",
        overlay_style: {},
        lyrics_style: {},
        traducao_style: {}
    })

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
            // Ignorar parsing errors no change pra não travar o campo de texto
        }
    }

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault()
        setLoading(true)
        try {
            const response = await editorApi.criarPerfil(formData)
            toast.success("Marca criada com sucesso!")
            router.push(`/admin/marcas/${response.id}`)
        } catch (err: any) {
            toast.error("Erro ao salvar marca: " + err.message)
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="mx-auto max-w-5xl space-y-6 pb-20">
            <div className="flex items-center gap-4">
                <Button variant="ghost" size="icon" asChild className="shrink-0">
                    <Link href="/admin/marcas"><ArrowLeft className="h-4 w-4" /></Link>
                </Button>
                <div>
                    <h1 className="text-2xl font-bold tracking-tight">Nova Marca (Perfil)</h1>
                    <p className="text-sm text-muted-foreground mt-1">Configure o esqueleto visual e prompts de base.</p>
                </div>
            </div>

            <form onSubmit={handleSave} className="space-y-6">
                <Card>
                    <CardHeader>
                        <CardTitle className="text-lg">Configurações Gerais</CardTitle>
                        <CardDescription>Nome, slug e identificadores curtos do projeto</CardDescription>
                    </CardHeader>
                    <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label>Nome da Marca *</Label>
                            <Input required value={formData.nome || ""} onChange={e => handleChange("nome", e.target.value)} placeholder="Ex: Aria de Bolso" />
                        </div>
                        <div className="space-y-2">
                            <Label>Slug (Nome p/ URLs/Folders) *</Label>
                            <Input required value={formData.slug || ""} onChange={e => handleChange("slug", e.target.value)} placeholder="aria-de-bolso" />
                        </div>
                        <div className="space-y-2">
                            <Label>Sigla *</Label>
                            <Input required value={formData.sigla || ""} onChange={e => handleChange("sigla", e.target.value)} placeholder="AB" maxLength={4} />
                        </div>
                        <div className="space-y-2">
                            <Label>Prefixo Bucket Cloudflare R2 *</Label>
                            <Input required value={formData.r2_prefix || ""} onChange={e => handleChange("r2_prefix", e.target.value)} placeholder="AriaDeBolso/projetos_" />
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
                            <Label>Idiomas Alvo (vírgula)</Label>
                            <Input value={formData.idiomas_alvo || ""} onChange={e => handleChange("idiomas_alvo", e.target.value)} placeholder="pt,en,es" />
                            <p className="text-xs text-muted-foreground">Vídeos vão renderizar track pra esses idiomas</p>
                        </div>
                        <div className="space-y-2">
                            <Label>Idioma Base (Postagem)</Label>
                            <Input value={formData.editorial_lang || ""} onChange={e => handleChange("editorial_lang", e.target.value)} placeholder="pt-br" />
                        </div>
                        <div className="space-y-2">
                            <Label>Idioma de Preview Visual</Label>
                            <Input value={formData.idioma_preview || ""} onChange={e => handleChange("idioma_preview", e.target.value)} placeholder="pt" />
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle className="text-lg">Tons de Voz & Prompts da Marca</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="space-y-2">
                            <Label>Identity Prompt (LLM Redator)</Label>
                            <Textarea
                                value={formData.identity_prompt || ""}
                                onChange={e => handleChange("identity_prompt", e.target.value)}
                                placeholder="Você é o redator do perfil X, responda como Y..."
                                className="min-h-[100px]"
                            />
                        </div>
                        <div className="space-y-2">
                            <Label>Tom de Voz</Label>
                            <Input value={formData.tom_voz || ""} onChange={e => handleChange("tom_voz", e.target.value)} placeholder="Inspirador, educativo, bem-humorado" />
                        </div>
                        <div className="space-y-2">
                            <Label>Escopo de Conteúdo (Instruções p/ copy)</Label>
                            <Textarea
                                value={formData.escopo_conteudo || ""}
                                onChange={e => handleChange("escopo_conteudo", e.target.value)}
                                placeholder="Evitar jargão técnico excessivo. Priorizar..."
                                className="min-h-[80px]"
                            />
                        </div>
                        <div className="space-y-2">
                            <Label>Categorias/Ganchos Frequentes</Label>
                            <Input value={formData.categorias_hook || ""} onChange={e => handleChange("categorias_hook", e.target.value)} placeholder="curiosidade,historia,climax_vocal" />
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle className="text-lg">Formato e Estilos Visuais (JSON)</CardTitle>
                    </CardHeader>
                    <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="grid grid-cols-2 gap-4 md:col-span-2">
                            <div className="space-y-2">
                                <Label>Largura Vídeo (px)</Label>
                                <Input type="number" required value={formData.video_width || 1080} onChange={e => handleChange("video_width", parseInt(e.target.value))} />
                            </div>
                            <div className="space-y-2">
                                <Label>Altura Vídeo (px)</Label>
                                <Input type="number" required value={formData.video_height || 1920} onChange={e => handleChange("video_height", parseInt(e.target.value))} />
                            </div>
                            <div className="space-y-2">
                                <Label>Duração Min. Sec</Label>
                                <Input type="number" required value={formData.duracao_min_sec || 45} onChange={e => handleChange("duracao_min_sec", parseInt(e.target.value))} />
                            </div>
                            <div className="space-y-2">
                                <Label>Duração Máx. Sec</Label>
                                <Input type="number" required value={formData.duracao_max_sec || 90} onChange={e => handleChange("duracao_max_sec", parseInt(e.target.value))} />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <Label>Estilo do Texto do Overlay</Label>
                            <Textarea
                                defaultValue={JSON.stringify(formData.overlay_style || {}, null, 2)}
                                onChange={e => handleJSONChange("overlay_style", e.target.value)}
                                className="font-mono text-xs min-h-[150px]"
                                placeholder='{ "font_size": 48 }'
                            />
                        </div>
                        <div className="space-y-2">
                            <Label>Estilo das Líricas Originais (Letra principal)</Label>
                            <Textarea
                                defaultValue={JSON.stringify(formData.lyrics_style || {}, null, 2)}
                                onChange={e => handleJSONChange("lyrics_style", e.target.value)}
                                className="font-mono text-xs min-h-[150px]"
                            />
                        </div>
                        <div className="space-y-2 md:col-span-2">
                            <Label>Estilo das Traduções (Subtexto)</Label>
                            <Textarea
                                defaultValue={JSON.stringify(formData.traducao_style || {}, null, 2)}
                                onChange={e => handleJSONChange("traducao_style", e.target.value)}
                                className="font-mono text-xs min-h-[150px]"
                            />
                        </div>
                    </CardContent>
                </Card>

                <div className="fixed bottom-0 left-0 lg:left-[240px] right-0 p-4 bg-background/80 backdrop-blur-sm border-t border-border flex justify-end gap-3 z-20">
                    <Button type="submit" size="default" disabled={loading}>
                        {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
                        {loading ? "Salvando..." : "Salvar Marca"}
                    </Button>
                </div>
            </form>
        </div>
    )
}
