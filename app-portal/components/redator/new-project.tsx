"use client"

import { useState, useRef, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"
import { Upload, Loader2 } from "lucide-react"
import { redatorApi, type DetectedMetadata } from "@/lib/api/redator"
import { curadoriaApi } from "@/lib/api/curadoria"
import { BrandSelector } from "@/components/brand-selector"
import { useBrand } from "@/lib/brand-context"

const CATEGORIES = ["", "Aria", "Duet", "Chorus", "Sacred Music", "Art Song", "Ensemble", "Crossover", "Vocal", "Overture", "Recitative", "Ballet", "Intermezzo", "Other"]
const RC_CATEGORIES = ["", "Orchestral", "Chamber", "Piano Solo", "Strings", "Winds", "Choral/Sacred", "Ballet", "Contemporary", "Crossover", "Opera", "Other"]

const HOOK_CATEGORIES = [
  { key: "curiosidade_musica", label: "Curiosidade Sobre a Musica", emoji: "🎵", desc: "Origem, contexto ou fato surpreendente sobre a musica" },
  { key: "curiosidade_interprete", label: "Curiosidade Sobre o Interprete", emoji: "🎤", desc: "Momento marcante, historia de bastidor ou peculiaridade" },
  { key: "curiosidade_compositor", label: "Curiosidade Sobre o Compositor", emoji: "✍️", desc: "Circunstancias da criacao, rivalidades ou inspiracoes" },
  { key: "valor_historico", label: "Valor Historico", emoji: "📜", desc: "Por que esta gravacao e um marco na opera" },
  { key: "climax_vocal", label: "Climax Vocal", emoji: "🔥", desc: "A nota impossivel ou passagem tecnicamente extraordinaria" },
  { key: "peso_emocional", label: "Peso Emocional", emoji: "💔", desc: "Drama do enredo ou emocao visivel do interprete" },
  { key: "transformacao_progressiva", label: "Transformacao Progressiva", emoji: "🌅", desc: "Como a interpretacao evolui do inicio ao climax" },
  { key: "dueto_encontro", label: "Dueto / Encontro", emoji: "🤝", desc: "Quimica e dialogo entre vozes" },
  { key: "reacao_impacto_visual", label: "Reacao / Impacto Visual", emoji: "😱", desc: "Plateia em extase, aplausos ou momento viral" },
  { key: "conexao_cultural", label: "Conexao Cultural", emoji: "🌍", desc: "Referencias em cinema, TV ou cultura popular" },
  { key: "prefiro_escrever", label: "Prefiro Escrever", emoji: "✏️", desc: "Escreva seu proprio angulo criativo" },
]

interface Interpreter {
  artist: string
  nationality: string
  nationality_flag: string
  voice_type: string
  birth_date: string
  death_date: string
}

const emptyInterpreter = (): Interpreter => ({
  artist: "", nationality: "", nationality_flag: "",
  voice_type: "", birth_date: "", death_date: "",
})

export function RedatorNewProject({ r2Folder, scheduledDate, projectId }: { r2Folder?: string; scheduledDate?: string; projectId?: string }) {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [youtubeUrl, setYoutubeUrl] = useState("")
  const [hook, setHook] = useState("")
  const [hookCategory, setHookCategory] = useState("")
  const [category, setCategory] = useState("")
  const [cutStart, setCutStart] = useState("")
  const [cutEnd, setCutEnd] = useState("")
  const { selectedBrand } = useBrand()
  const isRC = selectedBrand?.slug === "reels-classics"

  const [instrumentFormation, setInstrumentFormation] = useState("")
  const [orchestra, setOrchestra] = useState("")
  const [conductor, setConductor] = useState("")

  const [screenshotFile, setScreenshotFile] = useState<File | null>(null)
  const [screenshotPreview, setScreenshotPreview] = useState("")
  const [thumbnailUrl, setThumbnailUrl] = useState("")
  const [ytTitle, setYtTitle] = useState("")
  const [ytDescription, setYtDescription] = useState("")
  const [r2Loading, setR2Loading] = useState(false)
  const [r2Error, setR2Error] = useState("")
  const [detecting, setDetecting] = useState(false)
  const [detected, setDetected] = useState(false)
  const [confidence, setConfidence] = useState("")

  const [shared, setShared] = useState({ work: "", composer: "", composition_year: "", album_opera: "" })
  const [interpreters, setInterpreters] = useState<Interpreter[]>([emptyInterpreter()])

  // Helper: aplica metadados detectados via detectMetadataFromText
  async function applyR2Info(folder: string, fallbackArtist: string, fallbackWork: string) {
    setR2Loading(true)
    setR2Error("")
    try {
      const info = await curadoriaApi.r2Info(folder, selectedBrand?.slug)
      setYoutubeUrl(info.youtube_url)
      setThumbnailUrl(info.thumbnail_url)
      setYtTitle(info.title || "")
      setYtDescription(info.description || "")
      if (info.category) setCategory(info.category)
      if (info.title) {
        setDetecting(true)
        try {
          const meta = await redatorApi.detectMetadataFromText(info.youtube_url, info.title, info.description || "", selectedBrand?.slug)
          const artistStr = meta.artist || fallbackArtist
          const artists = artistStr.includes(" & ") ? artistStr.split(" & ").map((a: string) => a.trim()) : [artistStr]
          const nationalities = (meta.nationality || "").split(" / ").map((s: string) => s.trim())
          const flags = (meta.nationality_flag || "").trim().replace(/\s*\/\s*/g, " ").split(" ").map((s: string) => s.trim()).filter(Boolean)
          const voiceTypes = (meta.voice_type || "").split(" / ").map((s: string) => s.trim())
          const birthDates = (meta.birth_date || "").split(" / ").map((s: string) => s.trim())
          const deathDates = (meta.death_date || "").split(" / ").map((s: string) => s.trim())
          setInterpreters(artists.map((a: string, i: number) => ({
            artist: a,
            nationality: nationalities[i] || nationalities[0] || "",
            nationality_flag: flags[i] || flags[0] || "",
            voice_type: voiceTypes[i] || voiceTypes[0] || "",
            birth_date: birthDates[i] || birthDates[0] || "",
            death_date: deathDates[i] || deathDates[0] || "",
          })))
          setShared({
            work: meta.work || fallbackWork,
            composer: meta.composer || "",
            composition_year: meta.composition_year || "",
            album_opera: meta.album_opera || "",
          })
          setConfidence(meta.confidence || "high")
          if (meta.instrument_formation) setInstrumentFormation(meta.instrument_formation)
          if (meta.orchestra) setOrchestra(meta.orchestra)
          if (meta.conductor) setConductor(meta.conductor)
          if (meta.category) setCategory(meta.category)
        } catch {
          // Keep pre-fill if detection fails
        } finally {
          setDetecting(false)
        }
      }
    } catch (err: any) {
      setR2Error(`Não foi possível carregar YouTube info: ${err?.message || err}`)
    } finally {
      setR2Loading(false)
    }
  }

  useEffect(() => {
    if (!r2Folder) return
    // Strip r2_prefix da marca (ex: "ReelsClassics/projetos_/") para extrair artist/work
    const prefix = selectedBrand?.r2_prefix || ""
    let folderClean = r2Folder
    if (prefix && folderClean.startsWith(prefix)) {
      folderClean = folderClean.slice(prefix.length)
      if (folderClean.startsWith("/")) folderClean = folderClean.slice(1)
    }
    const sep = " - "
    const idx = folderClean.indexOf(sep)
    const artist = idx >= 0 ? folderClean.slice(0, idx).trim() : folderClean.trim()
    const work = idx >= 0 ? folderClean.slice(idx + sep.length).trim() : ""
    setInterpreters([{ ...emptyInterpreter(), artist }])
    setShared(prev => ({ ...prev, work }))
    setDetected(true)
    setConfidence("r2")
    applyR2Info(r2Folder, artist, work)
  }, [r2Folder])

  // Modo edição: carregar dados do projeto existente
  useEffect(() => {
    if (!projectId) return
    setLoading(true)
    redatorApi.getProject(Number(projectId)).then((p) => {
      setYoutubeUrl(p.youtube_url || "")
      setHook(p.hook || "")
      setHookCategory(p.hook_category || "")
      setCategory(p.category || "")
      setCutStart(p.cut_start || "")
      setCutEnd(p.cut_end || "")
      // Interpreters: split multi-artist fields
      const artists = (p.artist || "").split(" & ").map((a: string) => a.trim()).filter(Boolean)
      const nationalities = (p.nationality || "").split(" / ").map((s: string) => s.trim())
      const flags = (p.nationality_flag || "").split(" / ").map((s: string) => s.trim())
      const voiceTypes = (p.voice_type || "").split(" / ").map((s: string) => s.trim())
      const birthDates = (p.birth_date || "").split(" / ").map((s: string) => s.trim())
      const deathDates = (p.death_date || "").split(" / ").map((s: string) => s.trim())
      setInterpreters(artists.length > 0
        ? artists.map((a: string, i: number) => ({
            artist: a,
            nationality: nationalities[i] || nationalities[0] || "",
            nationality_flag: flags[i] || flags[0] || "",
            voice_type: voiceTypes[i] || voiceTypes[0] || "",
            birth_date: birthDates[i] || birthDates[0] || "",
            death_date: deathDates[i] || deathDates[0] || "",
          }))
        : [emptyInterpreter()]
      )
      setShared({
        work: p.work || "",
        composer: p.composer || "",
        composition_year: p.composition_year || "",
        album_opera: p.album_opera || "",
      })
      if (p.instrument_formation) setInstrumentFormation(p.instrument_formation)
      if (p.orchestra) setOrchestra(p.orchestra)
      if (p.conductor) setConductor(p.conductor)
      setDetected(true)
      setConfidence("edit")
      // Se tem r2_folder mas não youtube_url, buscar info do R2 para preencher metadados
      if (p.r2_folder && !p.youtube_url) {
        applyR2Info(p.r2_folder, p.artist || "", p.work || "")
      }
    }).catch((err) => {
      setError(`Erro ao carregar projeto: ${err?.message || err}`)
    }).finally(() => setLoading(false))
  }, [projectId])

  const isEditMode = !!projectId

  const isMulti = category === "Duet" || category === "Ensemble"

  const setSharedField = (key: string, value: string) =>
    setShared(prev => ({ ...prev, [key]: value }))

  const setInterpreterField = (index: number, key: keyof Interpreter, value: string) =>
    setInterpreters(prev => prev.map((interp, i) => i === index ? { ...interp, [key]: value } : interp))

  const addInterpreter = () => setInterpreters(prev => [...prev, emptyInterpreter()])
  const removeInterpreter = (index: number) => setInterpreters(prev => prev.filter((_, i) => i !== index))

  useEffect(() => {
    if (isMulti && interpreters.length < 2) {
      setInterpreters(prev => [...prev, emptyInterpreter()])
    }
  }, [category])

  const handleScreenshot = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setScreenshotFile(file)
    if (screenshotPreview) URL.revokeObjectURL(screenshotPreview)
    setScreenshotPreview(URL.createObjectURL(file))
    setDetected(false)
  }

  const handleDetect = async () => {
    if (!screenshotFile) return
    setDetecting(true)
    setError("")
    try {
      const result: DetectedMetadata = await redatorApi.detectMetadata(screenshotFile, youtubeUrl, selectedBrand?.slug)
      setShared({
        work: result.work || "",
        composer: result.composer || "",
        composition_year: result.composition_year || "",
        album_opera: result.album_opera || "",
      })
      const artistStr = result.artist || ""
      const artists = artistStr.includes(" & ") ? artistStr.split(" & ").map(a => a.trim()) : [artistStr]
      const nationalities = (result.nationality || "").split(" / ").map(s => s.trim())
      const flags = (result.nationality_flag || "").split(" / ").map(s => s.trim())
      const flagsSplit = flags.length === 1 && artists.length > 1
        ? (result.nationality_flag || "").trim().split(/\s+/)
        : flags
      const voiceTypes = (result.voice_type || "").split(" / ").map(s => s.trim())
      const birthDates = (result.birth_date || "").split(" / ").map(s => s.trim())
      const deathDates = (result.death_date || "").split(" / ").map(s => s.trim())
      setInterpreters(artists.map((a, i) => ({
        artist: a,
        nationality: nationalities[i] || nationalities[0] || "",
        nationality_flag: flagsSplit[i] || flagsSplit[0] || "",
        voice_type: voiceTypes[i] || voiceTypes[0] || "",
        birth_date: birthDates[i] || birthDates[0] || "",
        death_date: deathDates[i] || deathDates[0] || "",
      })))
      setConfidence(result.confidence || "high")
      // Preencher campos RC se detectados
      if (result.instrument_formation) setInstrumentFormation(result.instrument_formation)
      if (result.orchestra) setOrchestra(result.orchestra)
      if (result.conductor) setConductor(result.conductor)
      if (result.category) setCategory(result.category)
      setDetected(true)
    } catch (err: any) {
      setError(`Falha na deteccao automatica: ${err.message}. Preencha os campos manualmente.`)
      setDetected(true)
      setConfidence("low")
    } finally {
      setDetecting(false)
    }
  }

  const isValidMMSS = (v: string) => /^\d{2}:\d{2}$/.test(v)
  const hookValid = hookCategory === "prefiro_escrever" ? hook.trim().length > 0 : hookCategory.length > 0
  const stepAComplete = isRC
    ? (!!category && isValidMMSS(cutStart) && isValidMMSS(cutEnd))
    : (hookValid && !!category && isValidMMSS(cutStart) && isValidMMSS(cutEnd))
  const canSubmit = stepAComplete && detected && !!interpreters[0]?.artist && !!shared.work && !!shared.composer && !!selectedBrand

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!canSubmit) return
    if (!selectedBrand) {
      setError("Selecione uma marca antes de criar o projeto.")
      return
    }
    setError("")
    setLoading(true)
    try {
      const joinField = (key: keyof Interpreter) =>
        interpreters.map(i => i[key]).filter(Boolean).join(key === "artist" ? " & " : " / ")
      const projectData: Record<string, string> = {
        youtube_url: youtubeUrl, hook, hook_category: hookCategory,
        category, cut_start: cutStart, cut_end: cutEnd,
        artist: joinField("artist"), work: shared.work, composer: shared.composer,
        composition_year: shared.composition_year, nationality: joinField("nationality"),
        nationality_flag: joinField("nationality_flag"), voice_type: joinField("voice_type"),
        birth_date: joinField("birth_date"), death_date: joinField("death_date"),
        album_opera: shared.album_opera,
      }
      if (isRC) {
        if (instrumentFormation) projectData.instrument_formation = instrumentFormation
        if (orchestra) projectData.orchestra = orchestra
        if (conductor) projectData.conductor = conductor
      }
      if (r2Folder) projectData.r2_folder = r2Folder
      let finalProjectId: number

      if (isEditMode) {
        const updated = await redatorApi.updateProject(Number(projectId), projectData)
        finalProjectId = updated.id
      } else {
        const created = await redatorApi.createProject(projectData, selectedBrand?.slug)
        finalProjectId = created.id

        // Agendar se veio do calendário
        if (scheduledDate && finalProjectId) {
          try {
            await redatorApi.scheduleProject(finalProjectId, scheduledDate)
          } catch (e) {
            console.error("Erro ao agendar:", e)
          }
        }
      }

      if (isRC) {
        // Research + hooks são chamados na página /hooks (Opção A)
        // Submit apenas cria o projeto e redireciona
        router.push(`/redator/projeto/${finalProjectId}/hooks`)
      } else {
        if (!isEditMode) {
          await redatorApi.generate(finalProjectId)
        } else {
          // Edit mode (ex: projeto criado via calendário): gerar se overlay ainda não existe
          const existing = await redatorApi.getProject(finalProjectId)
          if (!existing.overlay_json || existing.overlay_json.length === 0) {
            await redatorApi.generate(finalProjectId)
          }
        }
        router.push(`/redator/projeto/${finalProjectId}/overlay`)
      }
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-8 gap-4">
        <div>
          <h1 className="text-xl font-semibold text-foreground">{isEditMode ? "Editar Projeto" : "Novo Projeto"}</h1>
          <p className="text-sm text-muted-foreground">{isEditMode ? "Revise os dados antes de prosseguir" : "Preencha os dados para gerar conteudo"}</p>
        </div>
        <div className="shrink-0 flex items-center gap-3 bg-muted/40 p-2 rounded-lg border border-border">
          <span className="text-xs font-medium text-muted-foreground hidden sm:inline-block">Marca Destino:</span>
          <BrandSelector />
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-base">Etapa A — Seus Dados</CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            {!r2Folder && !isEditMode && (
              <div className="space-y-2">
                <Label>Screenshot do YouTube *</Label>
                <p className="text-xs text-muted-foreground">Tire um screenshot da pagina do video no YouTube</p>
                <input ref={fileInputRef} type="file" accept="image/*" onChange={handleScreenshot} className="hidden" />
                <div className="flex gap-3">
                  <Button type="button" variant="outline" size="sm" onClick={() => fileInputRef.current?.click()}>
                    <Upload className="mr-2 h-3.5 w-3.5" />
                    {screenshotFile ? "Trocar Screenshot" : "Enviar Screenshot"}
                  </Button>
                  {screenshotFile && (
                    <Button type="button" size="sm" onClick={handleDetect} disabled={detecting}>
                      {detecting && <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />}
                      {detecting ? "Detectando..." : detected ? "Re-detectar" : "Detectar Metadados"}
                    </Button>
                  )}
                </div>
                {screenshotPreview && (
                  <img src={screenshotPreview} alt="YouTube screenshot" className="mt-3 max-w-full max-h-60 rounded-lg border" />
                )}
              </div>
            )}

            <div className="space-y-2">
              <Label>Link do YouTube (opcional)</Label>
              {r2Loading ? (
                <div className="flex items-center gap-2 text-xs text-muted-foreground py-1">
                  <Loader2 className="h-3 w-3 animate-spin" /> Carregando dados do YouTube...
                </div>
              ) : r2Error ? (
                <p className="text-xs text-destructive">{r2Error}</p>
              ) : null}
              <Input value={youtubeUrl} onChange={(e) => setYoutubeUrl(e.target.value)} placeholder="https://www.youtube.com/watch?v=..." />
              {r2Folder && ytTitle && (
                <div className="mt-2 rounded-lg border bg-muted/40 p-3 space-y-1">
                  <p className="text-xs font-semibold text-foreground leading-snug">{ytTitle}</p>
                  {ytDescription && (
                    <p className="text-[11px] text-muted-foreground leading-relaxed line-clamp-4 whitespace-pre-line">{ytDescription}</p>
                  )}
                </div>
              )}
            </div>

            {!isRC && (
              <div className="space-y-2">
                <Label>Categoria do Gancho *</Label>
                <div className="grid grid-cols-2 gap-2">
                  {HOOK_CATEGORIES.map((hc) => (
                    <button
                      key={hc.key}
                      type="button"
                      onClick={() => {
                        setHookCategory(hc.key)
                        if (hc.key !== "prefiro_escrever" && hookCategory === "prefiro_escrever") setHook("")
                      }}
                      className={cn(
                        "flex items-start gap-2.5 rounded-lg border p-3 text-left transition-all",
                        hookCategory === hc.key
                          ? "border-primary bg-primary/5 ring-1 ring-primary/20"
                          : "border-border bg-card hover:bg-muted/30"
                      )}
                    >
                      <span className="text-lg leading-none">{hc.emoji}</span>
                      <div className="min-w-0">
                        <p className="text-xs font-medium text-foreground">{hc.label}</p>
                        <p className="mt-0.5 text-[11px] leading-tight text-muted-foreground">{hc.desc}</p>
                      </div>
                    </button>
                  ))}
                </div>

                {hookCategory && hookCategory !== "prefiro_escrever" && (
                  <div className="mt-3 space-y-1.5">
                    <Label className="text-xs">Complemento (opcional)</Label>
                    <Textarea value={hook} onChange={(e) => setHook(e.target.value)} placeholder="Quer acrescentar algo ao prompt?" className="min-h-[60px]" />
                  </div>
                )}
                {hookCategory === "prefiro_escrever" && (
                  <div className="mt-3 space-y-1.5">
                    <Label className="text-xs">Seu gancho *</Label>
                    <Textarea value={hook} onChange={(e) => setHook(e.target.value)} placeholder="Escreva seu angulo criativo..." className="min-h-[80px]" />
                  </div>
                )}
              </div>
            )}

            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label>Categoria *</Label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs transition-colors"
                >
                  {(isRC ? RC_CATEGORIES : CATEGORIES).map((c) => (
                    <option key={c} value={c}>{c || "— Selecionar —"}</option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <Label>Inicio do Corte *</Label>
                <Input value={cutStart} onChange={(e) => setCutStart(e.target.value)} placeholder="01:15" className={cn("font-mono", cutStart && !isValidMMSS(cutStart) && "border-destructive")} maxLength={5} />
                {cutStart && !isValidMMSS(cutStart) && <p className="text-[11px] text-destructive">Formato: MM:SS (ex: 01:15)</p>}
              </div>
              <div className="space-y-2">
                <Label>Fim do Corte *</Label>
                <Input value={cutEnd} onChange={(e) => setCutEnd(e.target.value)} placeholder="02:45" className={cn("font-mono", cutEnd && !isValidMMSS(cutEnd) && "border-destructive")} maxLength={5} />
                {cutEnd && !isValidMMSS(cutEnd) && <p className="text-[11px] text-destructive">Formato: MM:SS (ex: 02:45)</p>}
              </div>
            </div>
          </CardContent>
        </Card>

        {(detected || detecting) && (
          <Card className={cn("mb-6", detecting && "opacity-60")}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">Etapa B — Metadados Detectados</CardTitle>
                {detected && !detecting && (
                  <span className={cn(
                    "rounded-full px-3 py-1 text-xs font-medium",
                    confidence === "edit"
                      ? "bg-blue-100 text-blue-800"
                      : confidence === "r2"
                        ? "bg-primary/10 text-primary"
                        : confidence === "high"
                          ? "bg-emerald-100 text-emerald-800"
                          : "bg-amber-100 text-amber-800"
                  )}>
                    {confidence === "edit" ? "Dados do projeto" : confidence === "r2" ? "Pre-carregado do R2" : confidence === "high" ? "Detectado" : "Baixa confianca — revise"}
                  </span>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {detecting && (
                <div className="flex items-center justify-center py-8 text-sm text-muted-foreground">
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Analisando screenshot...
                </div>
              )}
              {detected && !detecting && (
                <>
                  {interpreters.map((interp, index) => (
                    <div key={index} className={cn("space-y-3", isMulti && "rounded-lg border p-4")}>
                      {isMulti && (
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-semibold text-primary">Interprete {index + 1}</span>
                          {interpreters.length > 1 && (
                            <Button type="button" variant="ghost" size="sm" onClick={() => removeInterpreter(index)}>Remover</Button>
                          )}
                        </div>
                      )}
                      <div className="grid grid-cols-2 gap-3">
                        <div className="space-y-1">
                          <Label className="text-xs">{isRC ? "Interprete(s) *" : "Artista *"}</Label>
                          <Input value={interp.artist} onChange={(e) => setInterpreterField(index, "artist", e.target.value)} />
                        </div>
                        <div className="space-y-1">
                          <Label className="text-xs">Nacionalidade</Label>
                          <Input value={interp.nationality} onChange={(e) => setInterpreterField(index, "nationality", e.target.value)} />
                        </div>
                        <div className="space-y-1">
                          <Label className="text-xs">Bandeira</Label>
                          <Input value={interp.nationality_flag} onChange={(e) => setInterpreterField(index, "nationality_flag", e.target.value)} className="text-xl" />
                        </div>
                        {!isRC && (
                          <div className="space-y-1">
                            <Label className="text-xs">Tipo de Voz</Label>
                            <Input value={interp.voice_type} onChange={(e) => setInterpreterField(index, "voice_type", e.target.value)} />
                          </div>
                        )}
                        {!isRC && (
                          <div className="space-y-1">
                            <Label className="text-xs">Nascimento</Label>
                            <Input value={interp.birth_date} onChange={(e) => setInterpreterField(index, "birth_date", e.target.value)} placeholder="dd/mm/yyyy" />
                          </div>
                        )}
                        {!isRC && (
                          <div className="space-y-1">
                            <Label className="text-xs">Falecimento</Label>
                            <Input value={interp.death_date} onChange={(e) => setInterpreterField(index, "death_date", e.target.value)} placeholder="Vazio se vivo" />
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                  {isMulti && (
                    <Button type="button" variant="outline" size="sm" onClick={addInterpreter}>+ Adicionar Interprete</Button>
                  )}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <Label className={`text-xs ${!shared.work ? "text-red-600 font-bold" : ""}`}>
                        Obra * {!shared.work && "— preencha manualmente"}
                      </Label>
                      <Input
                        value={shared.work}
                        onChange={(e) => setSharedField("work", e.target.value)}
                        placeholder={!shared.work ? "Nome da ária/peça não detectado — digite aqui" : ""}
                        className={!shared.work ? "border-red-500 border-2 bg-red-50" : ""}
                      />
                      {!shared.work && (
                        <p className="text-xs text-red-600 mt-1">
                          O nome da música não foi encontrado no título/descrição do vídeo.
                        </p>
                      )}
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Compositor *</Label>
                      <Input value={shared.composer} onChange={(e) => setSharedField("composer", e.target.value)} />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Ano de Composicao</Label>
                      <Input value={shared.composition_year} onChange={(e) => setSharedField("composition_year", e.target.value)} />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Album / Opera</Label>
                      <Input value={shared.album_opera} onChange={(e) => setSharedField("album_opera", e.target.value)} />
                    </div>
                    {isRC && (
                      <div className="space-y-1">
                        <Label className="text-xs">Instrumento / Formacao *</Label>
                        <Input value={instrumentFormation} onChange={(e) => setInstrumentFormation(e.target.value)} placeholder="Piano solo, Quarteto de cordas, Orquestra sinfonica..." />
                      </div>
                    )}
                    {isRC && (
                      <div className="space-y-1">
                        <Label className="text-xs">Orquestra / Ensemble</Label>
                        <Input value={orchestra} onChange={(e) => setOrchestra(e.target.value)} placeholder="Opcional" />
                      </div>
                    )}
                    {isRC && (
                      <div className="space-y-1">
                        <Label className="text-xs">Regente</Label>
                        <Input value={conductor} onChange={(e) => setConductor(e.target.value)} placeholder="Opcional" />
                      </div>
                    )}
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        )}

        <div className="pt-4 border-t">
          <Button type="submit" className="w-full" size="lg" disabled={loading || !canSubmit}>
            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {loading
              ? (isEditMode ? "Salvando..." : isRC ? "Criando projeto..." : "Criando & Gerando Conteúdo...")
              : (isEditMode
                ? (isRC ? "Salvar e Selecionar Ganchos" : "Salvar e Gerar Conteúdo")
                : (isRC ? "Próximo: Selecionar Ganchos" : "Próximo: Gerar Conteúdo"))}
          </Button>
          {!detected && !loading && !r2Folder && !isEditMode && (
            <p className="mt-3 text-center text-sm font-medium text-amber-600 bg-amber-50 p-2 rounded-lg border border-amber-200">
              Faça upload do screenshot do YouTube para continuar
            </p>
          )}
          {detected && !canSubmit && !loading && (() => {
            const missing: string[] = []
            if (!isRC && !hookValid) missing.push("Categoria do Gancho")
            if (!category) missing.push("Categoria")
            if (!isValidMMSS(cutStart)) missing.push("Inicio do Corte (MM:SS)")
            if (!isValidMMSS(cutEnd)) missing.push("Fim do Corte (MM:SS)")
            if (!interpreters[0]?.artist) missing.push("Artista")
            if (!shared.work) missing.push("Obra")
            if (!shared.composer) missing.push("Compositor")
            if (!selectedBrand) missing.push("Marca")
            return (
              <p className="mt-2 text-center text-xs text-muted-foreground">
                {missing.length > 0
                  ? `Falta preencher: ${missing.join(", ")}`
                  : "Preencha todos os campos obrigatórios (*) para continuar"}
              </p>
            )
          })()}
        </div>
      </form>
    </div>
  )
}
