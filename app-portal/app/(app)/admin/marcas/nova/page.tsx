"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { editorApi, type Perfil } from "@/lib/api/editor"
import { useAuth } from "@/lib/auth-context"
import { toast } from "sonner"
import { Card, CardContent } from "@/components/ui/card"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"
import { Loader2, ArrowLeft, Save, Globe, MonitorPlay, Type, Settings2, Palette, ChevronDown } from "lucide-react"

function CollapsibleSection({ title, description, icon: Icon, defaultOpen = false, children }: any) {
    const [open, setOpen] = useState(defaultOpen)
    return (
        <Card className="overflow-hidden border-border/50 shadow-sm transition-all bg-card/50">
            <div 
                className="flex items-center justify-between p-5 cursor-pointer hover:bg-muted/40 select-none group" 
                onClick={() => setOpen(!open)}
            >
                <div className="flex items-center gap-4">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary transition-colors group-hover:bg-primary/20">
                        <Icon className="h-5 w-5" />
                    </div>
                    <div>
                        <h3 className="text-base font-semibold leading-none tracking-tight text-foreground">{title}</h3>
                        {description && <p className="text-sm text-muted-foreground mt-1.5 leading-snug">{description}</p>}
                    </div>
                </div>
                <div className="flex h-8 w-8 items-center justify-center rounded-full hover:bg-muted transition-colors">
                    <ChevronDown className={cn("h-5 w-5 text-muted-foreground transition-transform duration-300", open ? "rotate-180" : "")} />
                </div>
            </div>
            {open && (
                <div className="p-5 pt-0 border-t border-border/50 bg-background/50">
                    <div className="mt-5">{children}</div>
                </div>
            )}
        </Card>
    )
}

export default function NovaMarcaPage() {
    const router = useRouter()
    const { isAdmin } = useAuth()
    const [loading, setLoading] = useState(false)
    const [previewOpen, setPreviewOpen] = useState(false)

    const [formData, setFormData] = useState<Partial<Perfil>>({
        nome: "",
        sigla: "",
        slug: "",
        ativo: true,
        cor_primaria: "#1a1a2e",
        cor_secundaria: "#e94560",
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
            // Ignorar parsing errors no change
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
        <div className="mx-auto max-w-4xl space-y-6 pb-28">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-card p-6 rounded-2xl border border-border/50 shadow-sm">
                <div className="flex items-center gap-4">
                    <Button variant="ghost" size="icon" asChild className="shrink-0 h-10 w-10 bg-muted/50 hover:bg-muted rounded-full">
                        <Link href="/admin/marcas"><ArrowLeft className="h-4 w-4" /></Link>
                    </Button>
                    <div>
                        <h1 className="text-2xl font-bold tracking-tight">Nova Marca (Perfil)</h1>
                        <p className="text-sm text-muted-foreground mt-1">Configure o esqueleto visual e os prompts base para IA.</p>
                    </div>
                </div>
            </div>

            <form onSubmit={handleSave} className="space-y-4">
                <CollapsibleSection title="Configurações Gerais" description="Dados básicos, identificadores e cores." icon={Settings2} defaultOpen={true}>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                        <div className="space-y-2">
                            <Label className="font-semibold text-muted-foreground">Nome da Marca *</Label>
                            <Input required value={formData.nome || ""} onChange={e => handleChange("nome", e.target.value)} className="bg-background" placeholder="Ex: Aria de Bolso" />
                        </div>
                        <div className="space-y-2">
                            <Label className="font-semibold text-muted-foreground">Slug (Nome p/ URLs/Folders) *</Label>
                            <Input required value={formData.slug || ""} onChange={e => handleChange("slug", e.target.value)} className="bg-background font-mono text-sm" placeholder="aria-de-bolso" />
                        </div>
                        <div className="space-y-2">
                            <Label className="font-semibold text-muted-foreground">Sigla *</Label>
                            <Input required value={formData.sigla || ""} onChange={e => handleChange("sigla", e.target.value)} maxLength={4} className="bg-background uppercase font-bold" placeholder="AB" />
                        </div>
                        <div className="space-y-2">
                            <Label className="font-semibold text-muted-foreground">Prefixo Cloudflare R2 *</Label>
                            <Input required value={formData.r2_prefix || ""} onChange={e => handleChange("r2_prefix", e.target.value)} className="bg-background font-mono text-sm" placeholder="AriaDeBolso/projetos_" />
                        </div>
                        <div className="space-y-2">
                            <Label className="font-semibold text-muted-foreground">Cor Primária (Hex)</Label>
                            <div className="flex gap-2 p-1 bg-background border border-input rounded-md focus-within:ring-1 focus-within:ring-ring h-10 overflow-hidden">
                                <input 
                                    type="color" 
                                    className="w-10 h-full p-0 border-0 cursor-pointer bg-transparent" 
                                    value={formData.cor_primaria || "#1a1a2e"} 
                                    onChange={e => handleChange("cor_primaria", e.target.value)} 
                                />
                                <Input 
                                    value={formData.cor_primaria || ""} 
                                    onChange={e => handleChange("cor_primaria", e.target.value)} 
                                    placeholder="#1a1a2e" 
                                    className="flex-1 border-0 h-full uppercase font-mono focus-visible:ring-0 shadow-none px-2" 
                                />
                            </div>
                        </div>
                        <div className="space-y-2">
                            <Label className="font-semibold text-muted-foreground">Cor Secundária (Hex)</Label>
                            <div className="flex gap-2 p-1 bg-background border border-input rounded-md focus-within:ring-1 focus-within:ring-ring h-10 overflow-hidden">
                                <input 
                                    type="color" 
                                    className="w-10 h-full p-0 border-0 cursor-pointer bg-transparent" 
                                    value={formData.cor_secundaria || "#e94560"} 
                                    onChange={e => handleChange("cor_secundaria", e.target.value)} 
                                />
                                <Input 
                                    value={formData.cor_secundaria || ""} 
                                    onChange={e => handleChange("cor_secundaria", e.target.value)} 
                                    placeholder="#e94560" 
                                    className="flex-1 border-0 h-full uppercase font-mono focus-visible:ring-0 shadow-none px-2" 
                                />
                            </div>
                        </div>
                    </div>
                </CollapsibleSection>

                <CollapsibleSection title="Idiomas e Internacionalização" description="Quais idiomas essa marca suporta por padrão." icon={Globe}>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
                        <div className="space-y-2">
                            <Label className="font-semibold text-muted-foreground">Idiomas Alvo</Label>
                            <Input value={formData.idiomas_alvo || ""} onChange={e => handleChange("idiomas_alvo", e.target.value)} className="bg-background font-mono text-sm" placeholder="pt,en,es" />
                        </div>
                        <div className="space-y-2">
                            <Label className="font-semibold text-muted-foreground">Idioma Base</Label>
                            <Input value={formData.editorial_lang || ""} onChange={e => handleChange("editorial_lang", e.target.value)} className="bg-background font-mono text-sm" placeholder="pt-br" />
                        </div>
                        <div className="space-y-2">
                            <Label className="font-semibold text-muted-foreground">Idioma de Preview</Label>
                            <Input value={formData.idioma_preview || ""} onChange={e => handleChange("idioma_preview", e.target.value)} className="bg-background font-mono text-sm" placeholder="pt" />
                        </div>
                    </div>
                </CollapsibleSection>

                <CollapsibleSection title="Prompts & Editorial" description="Personalidade da marca para a inteligência artificial." icon={Type}>
                    <div className="space-y-5">
                        <div className="space-y-2">
                            <Label className="font-semibold text-muted-foreground">Identity Prompt (LLM Redator)</Label>
                            <Textarea
                                value={formData.identity_prompt || ""}
                                onChange={e => handleChange("identity_prompt", e.target.value)}
                                className="min-h-[100px] bg-background resize-y"
                                placeholder="Você atua como um editor especializado em ópera..."
                            />
                        </div>
                        <div className="space-y-2">
                            <Label className="font-semibold text-muted-foreground">Tom de Voz</Label>
                            <Input value={formData.tom_voz || ""} onChange={e => handleChange("tom_voz", e.target.value)} className="bg-background" />
                        </div>
                        <div className="space-y-2">
                            <Label className="font-semibold text-muted-foreground">Escopo de Conteúdo</Label>
                            <Textarea
                                value={formData.escopo_conteudo || ""}
                                onChange={e => handleChange("escopo_conteudo", e.target.value)}
                                className="min-h-[80px] bg-background resize-y"
                            />
                        </div>
                        <div className="space-y-2">
                            <Label className="font-semibold text-muted-foreground">Categorias/Ganchos Frequentes</Label>
                            <Input value={formData.categorias_hook || ""} onChange={e => handleChange("categorias_hook", e.target.value)} className="bg-background font-mono text-sm" placeholder="historia,curiosidade,nota_alta" />
                        </div>
                    </div>
                </CollapsibleSection>

                <CollapsibleSection title="Estilos Visuais (JSON) & Vídeo" description="Aparência das legendas e overlays no render final." icon={Palette} defaultOpen={true}>
                    <div className="flex justify-end mb-4">
                        <Button 
                            type="button" 
                            variant="secondary" 
                            size="sm" 
                            className="gap-2 shrink-0 bg-[#0f3460] hover:bg-[#1a1a2e] text-white shadow-sm"
                            onClick={() => setPreviewOpen(true)}
                        >
                            <MonitorPlay className="h-4 w-4" /> Visualizar Apperance
                        </Button>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="grid grid-cols-2 gap-5 md:col-span-2 p-5 bg-muted/40 rounded-xl border border-border/50">
                            <div className="space-y-2">
                                <Label className="font-semibold text-muted-foreground text-xs uppercase tracking-wider">Largura (px)</Label>
                                <Input type="number" required value={formData.video_width || 1080} onChange={e => handleChange("video_width", parseInt(e.target.value))} className="bg-background font-mono" />
                            </div>
                            <div className="space-y-2">
                                <Label className="font-semibold text-muted-foreground text-xs uppercase tracking-wider">Altura (px)</Label>
                                <Input type="number" required value={formData.video_height || 1920} onChange={e => handleChange("video_height", parseInt(e.target.value))} className="bg-background font-mono" />
                            </div>
                            <div className="space-y-2">
                                <Label className="font-semibold text-muted-foreground text-xs uppercase tracking-wider">Duração Min (s)</Label>
                                <Input type="number" required value={formData.duracao_min_sec || 45} onChange={e => handleChange("duracao_min_sec", parseInt(e.target.value))} className="bg-background font-mono" />
                            </div>
                            <div className="space-y-2">
                                <Label className="font-semibold text-muted-foreground text-xs uppercase tracking-wider">Duração Máx (s)</Label>
                                <Input type="number" required value={formData.duracao_max_sec || 90} onChange={e => handleChange("duracao_max_sec", parseInt(e.target.value))} className="bg-background font-mono" />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <Label className="font-semibold text-muted-foreground">JSON - Overlay (Header)</Label>
                            <Textarea
                                defaultValue={JSON.stringify(formData.overlay_style || {}, null, 2)}
                                onChange={e => handleJSONChange("overlay_style", e.target.value)}
                                className="font-mono text-[13px] min-h-[180px] bg-zinc-950 text-emerald-400 border-zinc-800 shadow-inner focus-visible:ring-emerald-500/50"
                                spellCheck={false}
                            />
                        </div>
                        <div className="space-y-2">
                            <Label className="font-semibold text-muted-foreground">JSON - Letra Principal (Lyrics)</Label>
                            <Textarea
                                defaultValue={JSON.stringify(formData.lyrics_style || {}, null, 2)}
                                onChange={e => handleJSONChange("lyrics_style", e.target.value)}
                                className="font-mono text-[13px] min-h-[180px] bg-zinc-950 text-emerald-400 border-zinc-800 shadow-inner focus-visible:ring-emerald-500/50"
                                spellCheck={false}
                            />
                        </div>
                        <div className="space-y-2 md:col-span-2">
                            <Label className="font-semibold text-muted-foreground">JSON - Tradução (Translation)</Label>
                            <Textarea
                                defaultValue={JSON.stringify(formData.traducao_style || {}, null, 2)}
                                onChange={e => handleJSONChange("traducao_style", e.target.value)}
                                className="font-mono text-[13px] min-h-[180px] bg-zinc-950 text-emerald-400 border-zinc-800 shadow-inner focus-visible:ring-emerald-500/50"
                                spellCheck={false}
                            />
                        </div>
                    </div>
                </CollapsibleSection>

                <div className="fixed bottom-0 left-0 lg:left-[224px] right-0 p-5 bg-background/80 backdrop-blur-md border-t border-border flex justify-end gap-3 z-30 shadow-[0_-4px_16px_rgba(0,0,0,0.05)]">
                    <Button type="button" variant="outline" onClick={() => router.push("/admin/marcas")} className="bg-card hover:bg-muted text-foreground px-6 h-11">
                        Cancelar
                    </Button>
                    <Button type="submit" size="default" disabled={loading} className="bg-primary hover:bg-primary/90 text-primary-foreground shadow-sm px-6 h-11">
                        {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
                        {loading ? "Salvando..." : "Criar Marca"}
                    </Button>
                </div>
            </form>

            <Dialog open={previewOpen} onOpenChange={setPreviewOpen}>
                <DialogContent className="sm:max-w-md bg-zinc-900 border-zinc-800 text-zinc-100 p-0 overflow-hidden">
                    <DialogHeader className="p-4 pb-2 border-b border-zinc-800">
                        <DialogTitle className="text-zinc-100 flex items-center gap-2">
                            <MonitorPlay className="h-4 w-4 text-emerald-400" />
                            Preview Visual (Wireframe)
                        </DialogTitle>
                        <DialogDescription className="text-zinc-400 text-xs">Aproximação baseada nos JSONs de estilo.</DialogDescription>
                    </DialogHeader>
                    <div className="flex justify-center bg-[#0d0d0d] p-6">
                        <div className="relative aspect-[9/16] w-full max-w-[260px] bg-zinc-800 rounded-md overflow-hidden shadow-2xl border border-zinc-700/50 flex flex-col items-center">
                            {/* Background placeholder */}
                            <div className="absolute inset-0 block bg-gradient-to-t from-black/90 via-black/20 to-black/40" />
                            
                            {/* Overlay mock (top/middle) */}
                            <div className="absolute top-16 left-0 right-0 text-center z-10 px-4">
                                <span className="inline-block px-3 py-1 bg-white/10 backdrop-blur-sm rounded border border-white/20 text-white font-serif uppercase tracking-[0.2em] text-xs">
                                    {(formData.overlay_style as any)?.text || "MOCK OVERLAY"}
                                </span>
                            </div>

                            {/* Tracks mock (bottom) */}
                            <div className="absolute bottom-16 left-0 right-0 flex flex-col items-center gap-3 px-6 z-10 w-full">
                                {/* Translation mock */}
                                <div className="text-center text-sm font-medium italic text-emerald-300 drop-shadow-md">
                                    Tradução na lateral ou topo
                                </div>
                                {/* Lyrics mock */}
                                <div className="text-center font-serif text-2xl font-bold text-white drop-shadow-[0_4px_4px_rgba(0,0,0,0.8)] leading-tight">
                                    Líricas Principais
                                </div>
                            </div>
                        </div>
                    </div>
                    <div className="p-4 bg-zinc-950 flex justify-end">
                        <Button variant="outline" size="sm" onClick={() => setPreviewOpen(false)} className="border-zinc-700 text-zinc-300 hover:bg-zinc-800 hover:text-white">
                            Fechar
                        </Button>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    )
}
