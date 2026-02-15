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

const CATEGORIES = ["", "Aria", "Duet", "Chorus", "Overture", "Recitative", "Ensemble", "Ballet", "Intermezzo", "Other"]

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

export function RedatorNewProject() {
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

  const [screenshotFile, setScreenshotFile] = useState<File | null>(null)
  const [screenshotPreview, setScreenshotPreview] = useState("")
  const [detecting, setDetecting] = useState(false)
  const [detected, setDetected] = useState(false)
  const [confidence, setConfidence] = useState("")

  const [shared, setShared] = useState({ work: "", composer: "", composition_year: "", album_opera: "" })
  const [interpreters, setInterpreters] = useState<Interpreter[]>([emptyInterpreter()])

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
      const result: DetectedMetadata = await redatorApi.detectMetadata(screenshotFile, youtubeUrl)
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
      setDetected(true)
    } catch (err: any) {
      setError(`Falha na deteccao automatica: ${err.message}. Preencha os campos manualmente.`)
      setDetected(true)
      setConfidence("low")
    } finally {
      setDetecting(false)
    }
  }

  const hookValid = hookCategory === "prefiro_escrever" ? hook.trim().length > 0 : hookCategory.length > 0
  const stepAComplete = hookValid && !!category && !!cutStart && !!cutEnd
  const canSubmit = stepAComplete && detected && !!interpreters[0]?.artist && !!shared.work && !!shared.composer

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!canSubmit) return
    setError("")
    setLoading(true)
    try {
      const joinField = (key: keyof Interpreter) =>
        interpreters.map(i => i[key]).filter(Boolean).join(key === "artist" ? " & " : " / ")
      const project = await redatorApi.createProject({
        youtube_url: youtubeUrl, hook, hook_category: hookCategory,
        category, cut_start: cutStart, cut_end: cutEnd,
        artist: joinField("artist"), work: shared.work, composer: shared.composer,
        composition_year: shared.composition_year, nationality: joinField("nationality"),
        nationality_flag: joinField("nationality_flag"), voice_type: joinField("voice_type"),
        birth_date: joinField("birth_date"), death_date: joinField("death_date"),
        album_opera: shared.album_opera,
      })
      await redatorApi.generate(project.id)
      router.push(`/redator/projeto/${project.id}/overlay`)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-foreground">Novo Projeto</h1>
        <p className="text-sm text-muted-foreground">Preencha os dados para gerar conteudo</p>
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

            <div className="space-y-2">
              <Label>Link do YouTube (opcional)</Label>
              <Input value={youtubeUrl} onChange={(e) => setYoutubeUrl(e.target.value)} placeholder="https://www.youtube.com/watch?v=..." />
            </div>

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

            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label>Categoria *</Label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs transition-colors"
                >
                  {CATEGORIES.map((c) => (
                    <option key={c} value={c}>{c || "— Selecionar —"}</option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <Label>Inicio do Corte *</Label>
                <Input value={cutStart} onChange={(e) => setCutStart(e.target.value)} placeholder="1:15" className="font-mono" />
              </div>
              <div className="space-y-2">
                <Label>Fim do Corte *</Label>
                <Input value={cutEnd} onChange={(e) => setCutEnd(e.target.value)} placeholder="2:45" className="font-mono" />
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
                    confidence === "high" ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"
                  )}>
                    {confidence === "high" ? "Detectado" : "Baixa confianca — revise"}
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
                          <Label className="text-xs">Artista *</Label>
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
                        <div className="space-y-1">
                          <Label className="text-xs">Tipo de Voz</Label>
                          <Input value={interp.voice_type} onChange={(e) => setInterpreterField(index, "voice_type", e.target.value)} />
                        </div>
                        <div className="space-y-1">
                          <Label className="text-xs">Nascimento</Label>
                          <Input value={interp.birth_date} onChange={(e) => setInterpreterField(index, "birth_date", e.target.value)} placeholder="dd/mm/yyyy" />
                        </div>
                        <div className="space-y-1">
                          <Label className="text-xs">Falecimento</Label>
                          <Input value={interp.death_date} onChange={(e) => setInterpreterField(index, "death_date", e.target.value)} placeholder="Vazio se vivo" />
                        </div>
                      </div>
                    </div>
                  ))}
                  {isMulti && (
                    <Button type="button" variant="outline" size="sm" onClick={addInterpreter}>+ Adicionar Interprete</Button>
                  )}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <Label className="text-xs">Obra *</Label>
                      <Input value={shared.work} onChange={(e) => setSharedField("work", e.target.value)} />
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
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        )}

        {detected && (
          <>
            <Button type="submit" className="w-full" size="lg" disabled={loading || !canSubmit}>
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {loading ? "Criando & Gerando Conteudo..." : "Criar Projeto e Gerar Conteudo"}
            </Button>
            {!canSubmit && !loading && (
              <p className="mt-2 text-center text-xs text-muted-foreground">
                Preencha todos os campos obrigatorios (*) para continuar
              </p>
            )}
          </>
        )}
      </form>
    </div>
  )
}
