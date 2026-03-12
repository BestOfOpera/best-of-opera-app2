"use client"

import { useState, useEffect } from "react"
import { useParams, useRouter } from "next/navigation"
import Link from "next/link"
import { editorApi, type Perfil } from "@/lib/api/editor"
import { useAuth } from "@/lib/auth-context"
import { toast } from "sonner"
import { Card, CardContent } from "@/components/ui/card"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { Loader2, ArrowLeft, Save, Globe, Eye, MonitorPlay, Type, Settings2, Palette, ChevronDown, Video, Check, Cpu, Copy } from "lucide-react"
import { StyleTrackConfig } from "@/components/admin/style-track-config"
import { BrandPreview } from "@/components/admin/brand-preview"

const HOOK_CATEGORIES = [
    { key: "curiosidade_musica",        label: "Curiosidade Sobre a Música",    emoji: "🎵" },
    { key: "curiosidade_interprete",    label: "Curiosidade Sobre o Intérprete", emoji: "🎤" },
    { key: "curiosidade_compositor",    label: "Curiosidade Sobre o Compositor", emoji: "✍️" },
    { key: "valor_historico",           label: "Valor Histórico",               emoji: "📜" },
    { key: "climax_vocal",              label: "Clímax Vocal",                  emoji: "🔥" },
    { key: "peso_emocional",            label: "Peso Emocional",                emoji: "💔" },
    { key: "transformacao_progressiva", label: "Transformação Progressiva",     emoji: "🌅" },
    { key: "dueto_encontro",            label: "Dueto / Encontro",              emoji: "🤝" },
    { key: "reacao_impacto_visual",     label: "Reação / Impacto Visual",       emoji: "😱" },
    { key: "conexao_cultural",          label: "Conexão Cultural",              emoji: "🌍" },
    { key: "prefiro_escrever",          label: "Prefiro Escrever",              emoji: "✏️" },
]

function toHookArray(v: unknown): string[] {
    if (Array.isArray(v)) return v
    if (typeof v === "string" && v) return v.split(",").map(s => s.trim()).filter(Boolean)
    return []
}

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

export default function MarcaConfigPage() {
    const { id } = useParams()
    const router = useRouter()
    const { isAdmin } = useAuth()
    const [loading, setLoading] = useState(true)
    const [saving, setSaving] = useState(false)
    const [previewOpen, setPreviewOpen] = useState(false)

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

    const handleDuplicate = async () => {
        if (!confirm("Deseja criar uma cópia desta marca?")) return
        setLoading(true)
        try {
            const data = await editorApi.duplicarPerfil(Number(id))
            toast.success("Marca duplicada com sucesso!")
            router.push(`/admin/marcas/${data.id}`)
        } catch (err: any) {
            toast.error("Erro ao duplicar: " + err.message)
            setLoading(false)
        }
    }

    if (loading) {
        return <div className="flex h-[50vh] items-center justify-center"><Loader2 className="h-8 w-8 animate-spin text-muted-foreground" /></div>
    }

    return (
        <div className="mx-auto max-w-4xl space-y-6 pb-28">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-card p-6 rounded-2xl border border-border/50 shadow-sm">
                <div className="flex items-center gap-4">
                    <Button variant="ghost" size="icon" asChild className="shrink-0 h-10 w-10 bg-muted/50 hover:bg-muted rounded-full">
                        <Link href="/admin/marcas"><ArrowLeft className="h-4 w-4" /></Link>
                    </Button>
                    <div>
                        <div className="flex items-center gap-3">
                            <h1 className="text-2xl font-bold tracking-tight">Configurar {formData.nome}</h1>
                            <Badge 
                                variant={formData.ativo ? "default" : "secondary"} 
                                className={cn("uppercase text-[10px] tracking-wider font-bold", formData.ativo ? "bg-emerald-500/15 text-emerald-700 hover:bg-emerald-500/25 border-emerald-500/20" : "")}
                            >
                                {formData.ativo ? "Ativa" : "Inativa"}
                            </Badge>
                        </div>
                        <p className="text-sm text-muted-foreground mt-1">ID: {formData.id} • Criada em: {formData.created_at ? new Date(formData.created_at).toLocaleDateString() : "—"}</p>
                    </div>
                </div>
                <div className="flex gap-2 shrink-0">
                    <Button variant="outline" size="sm" onClick={handleDuplicate} className="gap-2">
                        <Copy className="h-4 w-4" /> Duplicar
                    </Button>
                    <Button variant="outline" size="sm" onClick={handleToggleAtivo} className={!formData.ativo ? "border-emerald-200 text-emerald-700 hover:bg-emerald-50" : ""}>
                        {formData.ativo ? "Desativar Marca" : "Reativar Marca"}
                    </Button>
                </div>
            </div>

            <form onSubmit={handleSave} className="space-y-4">
                <CollapsibleSection title="Configurações Gerais" description="Dados básicos, identificadores e cores fundamentais da identidade visual." icon={Settings2} defaultOpen={true}>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                        <div className="space-y-2">
                            <Label htmlFor="perfil-nome" className="font-semibold text-muted-foreground">Nome da Marca *</Label>
                            <p className="text-[11px] text-muted-foreground -mt-1">Nome de exibição público no portal e nos metadados. Ex: Best of Opera.</p>
                            <Input id="perfil-nome" required value={formData.nome || ""} onChange={e => handleChange("nome", e.target.value)} className="bg-background" />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="perfil-slug" className="font-semibold text-muted-foreground">Slug (URL) *</Label>
                            <p className="text-[11px] text-muted-foreground -mt-1">Identificador amigável para URLs e nomes de pastas (use apenas letras minusculas e hífens). Ex: best-of-opera.</p>
                            <Input id="perfil-slug" required value={formData.slug || ""} onChange={e => handleChange("slug", e.target.value)} className="bg-background font-mono text-sm" />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="perfil-sigla" className="font-semibold text-muted-foreground">Sigla (ID Curadoria) *</Label>
                            <p className="text-[11px] text-muted-foreground -mt-1">Abreviação única de 2 a 4 letras usada pelo motor de busca. Ex: BO.</p>
                            <Input id="perfil-sigla" required value={formData.sigla || ""} onChange={e => handleChange("sigla", e.target.value)} maxLength={4} className="bg-background uppercase font-bold" />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="perfil-r2-prefix" className="font-semibold text-muted-foreground">Prefixo Cloudflare R2 *</Label>
                            <p className="text-[11px] text-muted-foreground -mt-1">Caminho base no storage R2 para todos os assets desta marca. Ex: editor/brand-x/</p>
                            <Input id="perfil-r2-prefix" required value={formData.r2_prefix || ""} onChange={e => handleChange("r2_prefix", e.target.value)} className="bg-background font-mono text-sm" placeholder="exemplo/" />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="perfil-cor-primaria" className="font-semibold text-muted-foreground">Cor Primária (Hex)</Label>
                            <p className="text-[11px] text-muted-foreground -mt-1">Cor principal usada em botões, links e destaques no app.</p>
                            <div className="flex gap-2 p-1 bg-background border border-input rounded-md focus-within:ring-1 focus-within:ring-ring h-10 overflow-hidden">
                                <input 
                                    id="perfil-cor-primaria-picker"
                                    type="color" 
                                    className="w-10 h-full p-0 border-0 cursor-pointer bg-transparent" 
                                    value={formData.cor_primaria || "#3b82f6"} 
                                    onChange={e => handleChange("cor_primaria", e.target.value)} 
                                />
                                <Input 
                                    id="perfil-cor-primaria"
                                    value={formData.cor_primaria || ""} 
                                    onChange={e => handleChange("cor_primaria", e.target.value)} 
                                    placeholder="#3b82f6" 
                                    maxLength={7}
                                    className="flex-1 border-0 h-full uppercase font-mono focus-visible:ring-0 shadow-none px-2" 
                                />
                            </div>
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="perfil-cor-secundaria" className="font-semibold text-muted-foreground">Cor Secundária (Hex)</Label>
                            <p className="text-[11px] text-muted-foreground -mt-1">Cor de suporte usada em badges e estados secundários.</p>
                            <div className="flex gap-2 p-1 bg-background border border-input rounded-md focus-within:ring-1 focus-within:ring-ring h-10 overflow-hidden">
                                <input 
                                    id="perfil-cor-secundaria-picker"
                                    type="color" 
                                    className="w-10 h-full p-0 border-0 cursor-pointer bg-transparent" 
                                    value={formData.cor_secundaria || "#1e40af"} 
                                    onChange={e => handleChange("cor_secundaria", e.target.value)} 
                                />
                                <Input 
                                    id="perfil-cor-secundaria"
                                    value={formData.cor_secundaria || ""} 
                                    onChange={e => handleChange("cor_secundaria", e.target.value)} 
                                    placeholder="#1e40af" 
                                    maxLength={7}
                                    className="flex-1 border-0 h-full uppercase font-mono focus-visible:ring-0 shadow-none px-2" 
                                />
                            </div>
                        </div>
                        <div className="space-y-2 md:col-span-2">
                            <Label htmlFor="perfil-font-upload" className="font-semibold text-muted-foreground">Fonte da Marca (.ttf, .otf)</Label>
                            <p className="text-[11px] text-muted-foreground -mt-1">Font atual: <span className="font-mono text-primary">{formData.font_name || "Padrão (Inter)"}</span>. O upload será enviado para o R2.</p>
                            <div className="flex gap-2">
                                <Input 
                                    id="perfil-font-upload"
                                    type="file" 
                                    accept=".ttf,.otf"
                                    onChange={async (e) => {
                                        const file = e.target.files?.[0]
                                        if (!file) return
                                        
                                        const tId = toast.loading(`Enviando fonte ${file.name}...`)
                                        try {
                                            const updated = await editorApi.uploadFonte(Number(id), file)
                                            setFormData(updated)
                                            toast.success("Fonte enviada e configurada!", { id: tId })
                                        } catch (err: any) {
                                            toast.error("Erro no upload: " + err.message, { id: tId })
                                        }
                                    }}
                                    className="bg-background cursor-pointer" 
                                />
                                {formData.font_file_r2_key && (
                                    <Badge variant="outline" className="h-10 px-3 bg-emerald-50 text-emerald-600 border-emerald-200">R2 OK</Badge>
                                )}
                            </div>
                        </div>
                    </div>
                </CollapsibleSection>

                <CollapsibleSection title="Motor da Marca (Curadoria)" description="Configurações avançadas para o robô de busca e curadoria automática de vídeos." icon={Cpu}>
                    <div className="space-y-6">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                            <div className="space-y-2">
                                <Label htmlFor="perfil-playlist-id" className="font-semibold text-muted-foreground">ID da Playlist YouTube</Label>
                                <p className="text-[11px] text-muted-foreground -mt-1">Playlist oficial para coleta de vídeos. Ex: PL...</p>
                                <Input id="perfil-playlist-id" value={formData.playlist_id || ""} onChange={e => handleChange("playlist_id", e.target.value)} className="bg-background font-mono text-sm" placeholder="PL..." />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="perfil-anti-spam" className="font-semibold text-muted-foreground">Termos Anti-Spam</Label>
                                <p className="text-[11px] text-muted-foreground -mt-1">Palavras ou prefixos que o robô deve ignorar na busca.</p>
                                <Input id="perfil-anti-spam" value={formData.anti_spam_terms || ""} onChange={e => handleChange("anti_spam_terms", e.target.value)} className="bg-background text-sm" />
                            </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-5 border-t border-border/50 pt-4">
                            <div className="space-y-2">
                                <Label className="font-semibold text-muted-foreground">Canais Institucionais (JSON Array)</Label>
                                <p className="text-[11px] text-muted-foreground -mt-1">Lista de slugs de canais que têm prioridade ou são oficiais.</p>
                                <Textarea
                                    value={JSON.stringify(formData.institutional_channels || [], null, 2)}
                                    onChange={e => {
                                        try {
                                            const parsed = JSON.parse(e.target.value)
                                            handleChange("institutional_channels", parsed)
                                        } catch (err) {}
                                    }}
                                    className="font-mono text-[12px] min-h-[80px] bg-zinc-950 text-blue-400 border-zinc-800"
                                    spellCheck={false}
                                />
                            </div>
                            <div className="space-y-2">
                                <Label className="font-semibold text-muted-foreground">Elite Hits (JSON Array)</Label>
                                <p className="text-[11px] text-muted-foreground -mt-1">Obras de altíssimo desempenho para esta marca.</p>
                                <Textarea
                                    value={JSON.stringify(formData.elite_hits || [], null, 2)}
                                    onChange={e => {
                                        try {
                                            const parsed = JSON.parse(e.target.value)
                                            handleChange("elite_hits", parsed)
                                        } catch (err) {}
                                    }}
                                    className="font-mono text-[12px] min-h-[80px] bg-zinc-950 text-blue-400 border-zinc-800"
                                    spellCheck={false}
                                />
                            </div>
                        </div>

                        <div className="space-y-2 border-t border-border/50 pt-4">
                            <Label className="font-semibold text-muted-foreground">Categorias e Seeds (Exploração)</Label>
                            <p className="text-xs text-muted-foreground -mt-1 mb-2">Estrutura de busca profunda: "categoria": ["seed1", "seed2", ...].</p>
                            <Textarea
                                value={JSON.stringify(formData.curadoria_categories || {}, null, 2)}
                                onChange={e => {
                                    try {
                                        const parsed = JSON.parse(e.target.value)
                                        handleChange("curadoria_categories", parsed)
                                    } catch (err) {}
                                }}
                                className="font-mono text-[12px] min-h-[150px] bg-zinc-950 text-blue-400 border-zinc-800"
                                spellCheck={false}
                            />
                        </div>
                    </div>
                </CollapsibleSection>

                <CollapsibleSection title="Idiomas e Internacionalização" description="Quais idiomas essa marca suporta por padrão." icon={Globe}>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
                        <div className="space-y-4 sm:col-span-3 pb-2">
                            <div className="flex items-center justify-between">
                                <Label className="font-semibold text-muted-foreground">Idiomas Alvo</Label>
                                <Badge variant="outline" className="text-[10px] uppercase font-bold">{formData.idiomas_alvo?.length || 0} SELECIONADOS</Badge>
                            </div>
                            <div className="flex flex-wrap gap-2 p-4 bg-muted/30 rounded-xl border border-border/50">
                                {["en", "pt", "es", "de", "fr", "it", "pl", "ru", "ja", "zh"].map(lang => {
                                    const isSelected = formData.idiomas_alvo?.includes(lang)
                                    return (
                                        <button
                                            key={lang}
                                            type="button"
                                            onClick={() => {
                                                const current = formData.idiomas_alvo || []
                                                handleChange("idiomas_alvo", isSelected 
                                                    ? current.filter(l => l !== lang)
                                                    : [...current, lang]
                                                )
                                            }}
                                            className={cn(
                                                "px-3 py-1.5 rounded-lg text-sm font-medium transition-all border",
                                                isSelected
                                                    ? "bg-primary text-primary-foreground border-primary shadow-sm"
                                                    : "bg-background text-muted-foreground border-border hover:border-primary/50 hover:text-foreground"
                                            )}
                                        >
                                            {lang.toUpperCase()}
                                        </button>
                                    )
                                })}
                            </div>
                        </div>
                        <div className="space-y-2">
                            <Label className="font-semibold text-muted-foreground">Idioma Base</Label>
                            <Input value={formData.editorial_lang || ""} onChange={e => handleChange("editorial_lang", e.target.value)} className="bg-background font-mono text-sm" placeholder="pt" />
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
                            <Label className="font-semibold text-muted-foreground">Persona do Redator (Prompt Base)</Label>
                            <p className="text-[11px] text-muted-foreground -mt-1">Define como a IA deve se comportar e escrever para esta marca.</p>
                            <Textarea
                                value={formData.identity_prompt || ""}
                                onChange={e => handleChange("identity_prompt", e.target.value)}
                                className="min-h-[140px] bg-background resize-y text-sm leading-relaxed"
                                placeholder="Ex: Você é um curador de ópera sofisticado que escreve para jovens entusiastas..."
                            />
                        </div>
                        <div className="space-y-2">
                            <Label className="font-semibold text-muted-foreground">Tom de Voz & Estilo</Label>
                            <div className="flex flex-wrap gap-2 mb-2">
                                {["Informativo", "Entusiasta", "Acadêmico", "Provocador", "Minimalista"].map(tone => (
                                    <Badge 
                                        key={tone} 
                                        variant="secondary" 
                                        className="cursor-pointer hover:bg-primary hover:text-primary-foreground transition-colors"
                                        onClick={() => handleChange("tom_de_voz", tone)}
                                    >
                                        {tone}
                                    </Badge>
                                ))}
                            </div>
                            <Input value={formData.tom_de_voz || ""} onChange={e => handleChange("tom_de_voz", e.target.value)} className="bg-background" placeholder="Sinta-se livre para customizar o tom aqui..." />
                        </div>
                        <div className="space-y-2">
                            <Label className="font-semibold text-muted-foreground">Nota de Escopo de Conteúdo</Label>
                            <p className="text-[11px] text-muted-foreground -mt-1">Instruções extras sobre o que o conteúdo deve focar.</p>
                            <Textarea
                                value={formData.escopo_conteudo || ""}
                                onChange={e => handleChange("escopo_conteudo", e.target.value)}
                                className="min-h-[80px] bg-background resize-y text-sm"
                                placeholder="Focar em curiosidades históricas e técnica vocal..."
                            />
                        </div>
                        <div className="space-y-4">
                            <div className="flex items-center justify-between">
                                <Label className="font-semibold text-muted-foreground">Hashtags Fixas</Label>
                                <Badge variant="secondary" className="text-[10px] uppercase font-bold">{formData.hashtags_fixas?.length || 0} ATIVAS</Badge>
                            </div>
                            <p className="text-[11px] text-muted-foreground -mt-3">Hashtags que serão incluídas em todos os posts (separe por vírgula).</p>
                            <Input 
                                value={Array.isArray(formData.hashtags_fixas) ? formData.hashtags_fixas.join(", ") : ""} 
                                onChange={e => handleChange("hashtags_fixas", e.target.value.split(",").map(s => s.trim()).filter(Boolean))} 
                                className="bg-background font-mono text-sm" 
                                placeholder="opera, classicalmusic, bestofopera"
                            />
                        </div>
                        <div className="space-y-3">
                            <div className="flex items-center justify-between">
                                <Label className="font-semibold text-muted-foreground">Categorias/Ganchos</Label>
                                <span className="text-xs text-muted-foreground">
                                    {toHookArray(formData.categorias_hook).length === 0
                                        ? "Nenhuma selecionada — todas ativas"
                                        : `${toHookArray(formData.categorias_hook).length} selecionada(s)`}
                                </span>
                            </div>
                            <p className="text-xs text-muted-foreground -mt-1">Marque as categorias que esta marca usa. Se nenhuma for marcada, todas ficam disponíveis.</p>
                            <div className="flex flex-wrap gap-2">
                                {HOOK_CATEGORIES.map(cat => {
                                    const selected = toHookArray(formData.categorias_hook).includes(cat.key)
                                    return (
                                        <button
                                            key={cat.key}
                                            type="button"
                                            onClick={() => {
                                                const current = toHookArray(formData.categorias_hook)
                                                handleChange("categorias_hook", selected
                                                    ? current.filter(k => k !== cat.key)
                                                    : [...current, cat.key]
                                                )
                                            }}
                                            className={cn(
                                                "flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm border transition-all",
                                                selected
                                                    ? "bg-primary/10 border-primary/40 text-primary font-medium"
                                                    : "bg-background border-border text-muted-foreground hover:border-primary/30 hover:text-foreground"
                                            )}
                                        >
                                            <span>{cat.emoji}</span>
                                            <span>{cat.label}</span>
                                            {selected && <Check className="h-3 w-3 ml-0.5" />}
                                        </button>
                                    )
                                })}
                            </div>
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
                        <div className="grid grid-cols-2 lg:grid-cols-4 gap-5 md:col-span-2 p-5 bg-muted/20 rounded-xl border border-border/30">
                            <div className="space-y-2">
                                <Label className="font-semibold text-muted-foreground text-[10px] uppercase tracking-wider">Overlay Max</Label>
                                <Input type="number" value={formData.overlay_max_chars || 50} onChange={e => handleChange("overlay_max_chars", parseInt(e.target.value))} className="bg-background h-8 text-xs" />
                            </div>
                            <div className="space-y-2">
                                <Label className="font-semibold text-muted-foreground text-[10px] uppercase tracking-wider">Overlay/Linha</Label>
                                <Input type="number" value={formData.overlay_max_chars_linha || 25} onChange={e => handleChange("overlay_max_chars_linha", parseInt(e.target.value))} className="bg-background h-8 text-xs" />
                            </div>
                            <div className="space-y-2">
                                <Label className="font-semibold text-muted-foreground text-[10px] uppercase tracking-wider">Lyrics Max</Label>
                                <Input type="number" value={formData.lyrics_max_chars || 40} onChange={e => handleChange("lyrics_max_chars", parseInt(e.target.value))} className="bg-background h-8 text-xs" />
                            </div>
                            <div className="space-y-2">
                                <Label className="font-semibold text-muted-foreground text-[10px] uppercase tracking-wider">Trad Max</Label>
                                <Input type="number" value={formData.traducao_max_chars || 60} onChange={e => handleChange("traducao_max_chars", parseInt(e.target.value))} className="bg-background h-8 text-xs" />
                            </div>
                        </div>

                        <div className="grid grid-cols-2 gap-5 md:col-span-2 p-5 bg-muted/40 rounded-xl border border-border/50">
                            <div className="space-y-2">
                                <Label className="font-semibold text-muted-foreground text-xs uppercase tracking-wider">Largura (px)</Label>
                                <Input type="number" required value={formData.video_width || 1080} onChange={e => handleChange("video_width", parseInt(e.target.value))} className="bg-background font-mono" />
                            </div>
                            <div className="space-y-2">
                                <Label className="font-semibold text-muted-foreground text-xs uppercase tracking-wider">Altura (px)</Label>
                                <Input type="number" required value={formData.video_height || 1920} onChange={e => handleChange("video_height", parseInt(e.target.value))} className="bg-background font-mono" />
                            </div>
                        </div>

                        <div className="md:col-span-2 grid grid-cols-1 xl:grid-cols-2 gap-6 pt-2">
                            <StyleTrackConfig 
                                title="Overlay (Header)" 
                                description="Legendas de contexto exibidas no topo do vídeo"
                                value={formData.overlay_style || {}} 
                                onChange={v => handleChange("overlay_style", v)} 
                            />
                            <StyleTrackConfig 
                                title="Letra Principal (Lyrics)" 
                                description="Letras cantadas em destaque no meio/inferior"
                                value={formData.lyrics_style || {}} 
                                onChange={v => handleChange("lyrics_style", v)} 
                            />
                            <div className="xl:col-span-2">
                                <StyleTrackConfig 
                                    title="Tradução (Translation)" 
                                    description="Tradução de acompanhamento"
                                    value={formData.traducao_style || {}} 
                                    onChange={v => handleChange("traducao_style", v)} 
                                />
                            </div>
                        </div>
                    </div>
                </CollapsibleSection>

                <div className="fixed bottom-0 left-0 lg:left-[224px] right-0 p-5 bg-background/80 backdrop-blur-md border-t border-border flex justify-end gap-3 z-30 shadow-[0_-4px_16px_rgba(0,0,0,0.05)]">
                    <Button type="button" variant="outline" onClick={() => router.push("/admin/marcas")} className="bg-card hover:bg-muted text-foreground px-6 h-11">
                        Cancelar
                    </Button>
                    <Button type="submit" size="default" disabled={saving} className="bg-primary hover:bg-primary/90 text-primary-foreground shadow-sm px-6 h-11">
                        {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
                        {saving ? "Salvando..." : "Salvar Configurações"}
                    </Button>
                </div>
            </form>

            <Dialog open={previewOpen} onOpenChange={setPreviewOpen}>
                <DialogContent className="sm:max-w-4xl bg-zinc-900 border-zinc-800 text-zinc-100 p-0 overflow-hidden">
                    <DialogHeader className="p-6 pb-2 border-b border-zinc-800">
                        <DialogTitle className="text-zinc-100 flex items-center gap-2 text-xl">
                            <MonitorPlay className="h-5 w-5 text-emerald-400" />
                            Simulador Realista (Preview)
                        </DialogTitle>
                        <DialogDescription className="text-zinc-400 text-sm mt-1">
                            Visualização baseada nos StyleTrackConfigs e assets da marca. Altas fidelidade ao render final.
                        </DialogDescription>
                    </DialogHeader>
                    
                    <div className="flex flex-col md:flex-row gap-0">
                        {/* Preview Area */}
                        <div className="flex-1 flex justify-center bg-[#0d0d0d] p-8 min-h-[500px] border-r border-zinc-800/50">
                            <BrandPreview perfil={formData} />
                        </div>
                        
                        {/* Quick Adjustments or Info Area */}
                        <div className="w-full md:w-80 bg-zinc-950/50 p-6 space-y-6 overflow-y-auto max-h-[600px]">
                            <div className="space-y-4">
                                <h4 className="text-xs font-bold uppercase tracking-widest text-emerald-500/80">Contexto do Preview</h4>
                                <div className="space-y-3">
                                    <div className="rounded-lg bg-zinc-900/80 p-3 border border-zinc-800">
                                        <Label className="text-[10px] text-zinc-500 uppercase tracking-tight">Fonte Ativa</Label>
                                        <p className="text-sm font-medium text-zinc-300 mt-0.5 truncate">{formData.font_name || "Padrão (Inter)"}</p>
                                    </div>
                                    <div className="rounded-lg bg-zinc-900/80 p-3 border border-zinc-800">
                                        <Label className="text-[10px] text-zinc-500 uppercase tracking-tight">Resolução</Label>
                                        <p className="text-sm font-medium text-zinc-300 mt-0.5">{formData.video_width}x{formData.video_height}</p>
                                    </div>
                                </div>
                            </div>

                            <div className="space-y-3 pt-6 border-t border-zinc-800">
                                <h4 className="text-xs font-bold uppercase tracking-widest text-zinc-500">Dica de Live Sync</h4>
                                <p className="text-[11px] leading-relaxed text-zinc-400">
                                    As alterações feitas nos formulários de estilo atrás desta janela são refletidas instantaneamente aqui.
                                </p>
                            </div>
                        </div>
                    </div>

                    <div className="p-4 bg-zinc-900 border-t border-zinc-800 flex justify-end">
                        <Button variant="outline" size="default" onClick={() => setPreviewOpen(false)} className="border-zinc-700 text-zinc-300 hover:bg-zinc-800 hover:text-white px-8">
                            Continuar Editando
                        </Button>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    )
}
