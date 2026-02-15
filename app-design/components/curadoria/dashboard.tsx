"use client"

import { useState, useEffect, useCallback } from "react"
import { curadoriaApi, type Video, type Quota, type Category, type SearchResult } from "@/lib/api/curadoria"
import { VideoCard } from "./video-card"
import { VideoDetailModal } from "./video-detail-modal"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"
import { Search, RefreshCw, Trophy, ListMusic, Loader2 } from "lucide-react"

interface SeedInfo {
  index: number
  total: number
  query?: string
}

export function CuradoriaDashboard() {
  const [query, setQuery] = useState("")
  const [results, setResults] = useState<Video[]>([])
  const [loading, setLoading] = useState(false)
  const [msg, setMsg] = useState("")
  const [msgType, setMsgType] = useState<"ok" | "loading" | "error" | "">("")
  const [detailIdx, setDetailIdx] = useState<number | null>(null)
  const [hidePosted, setHidePosted] = useState(true)
  const [activeCat, setActiveCat] = useState<string | null>(null)
  const [apiOk, setApiOk] = useState<boolean | null>(null)
  const [quota, setQuota] = useState<Quota>({ total_points: 0, remaining: 0, limit: 0 })
  const [categories, setCategories] = useState<Category[]>([])
  const [seedInfo, setSeedInfo] = useState<Record<string, SeedInfo>>({})
  const [playlistCount, setPlaylistCount] = useState(0)
  const [postedHidden, setPostedHidden] = useState(0)

  const loadQuota = useCallback(async () => {
    try {
      const q = await curadoriaApi.quota()
      setQuota(q)
    } catch {}
  }, [])

  const loadCategories = useCallback(async () => {
    try {
      const data = await curadoriaApi.categories()
      setCategories(data.categories || [])
    } catch {}
  }, [])

  const checkHealth = useCallback(async () => {
    try {
      const h = await curadoriaApi.health()
      setApiOk(h.youtube_api)
    } catch {
      setApiOk(false)
    }
  }, [])

  const updatePlaylistStatus = useCallback(async () => {
    try {
      const s = await curadoriaApi.cacheStatus()
      setPlaylistCount(s.playlist?.count || 0)
    } catch {}
  }, [])

  useEffect(() => {
    checkHealth()
    loadQuota()
    loadCategories()
    updatePlaylistStatus()
  }, [checkHealth, loadQuota, loadCategories, updatePlaylistStatus])

  const doSearch = async (q?: string, catKey?: string, forceRefresh = false) => {
    const isFresh = !catKey || forceRefresh || activeCat !== catKey
    if (isFresh && !forceRefresh) {
      if (!confirm("Esta busca custa ~100 pontos de cota. Continuar?")) return
    }
    if (forceRefresh) {
      if (!confirm("Nova seed custa ~100 pontos de cota. Continuar?")) return
    }

    setLoading(true)
    setResults([])
    setMsg(catKey ? `Buscando ${catKey}...` : q ? `Buscando "${q}"...` : "Carregando ranking...")
    setMsgType("loading")
    if (catKey) setActiveCat(catKey)

    try {
      let data: SearchResult
      if (catKey) {
        data = await curadoriaApi.searchCategory(catKey, hidePosted, forceRefresh)
        if (data.seed_index !== undefined) {
          setSeedInfo(prev => ({ ...prev, [catKey]: { index: data.seed_index!, total: data.total_seeds!, query: data.seed_query } }))
        }
        setQuery(catKey)
      } else if (q) {
        data = await curadoriaApi.search(q, hidePosted)
        setActiveCat(null)
      } else {
        data = await curadoriaApi.ranking(hidePosted)
        setQuery("Ranking")
        setActiveCat(null)
      }

      setResults(data.videos || [])
      setPostedHidden(data.posted_hidden || 0)
      const count = data.videos?.length || 0
      setMsg(`${count} vídeos encontrados`)
      setMsgType("ok")

      loadQuota()
      if (forceRefresh) loadCategories()
    } catch (err) {
      setMsg("Erro: " + (err instanceof Error ? err.message : "Erro"))
      setMsgType("error")
    } finally {
      setLoading(false)
    }
  }

  const loadPlaylist = async () => {
    setLoading(true)
    setResults([])
    setQuery("Playlist")
    setActiveCat("Playlist")
    setMsg("Carregando playlist...")
    setMsgType("loading")
    try {
      const data = await curadoriaApi.playlistVideos(hidePosted)
      setResults(data.videos || [])
      setMsg(`${data.videos?.length || 0} vídeos da playlist`)
      setMsgType("ok")
    } catch (err) {
      setMsg("Erro: " + (err instanceof Error ? err.message : "Erro"))
      setMsgType("error")
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (query.trim()) doSearch(query.trim())
  }

  const visibleResults = hidePosted ? results.filter(r => !r.posted) : results
  const detailVideo = detailIdx !== null ? visibleResults[detailIdx] : null

  const quotaPercent = quota.limit > 0 ? (quota.total_points / quota.limit) * 100 : 0
  const quotaColor = quotaPercent > 80 ? "text-red-600" : quotaPercent > 50 ? "text-amber-600" : "text-green-600"

  return (
    <div>
      {/* Header with quota */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold">Curadoria</h2>
          <p className="text-sm text-muted-foreground">Motor V7 — Seed rotation · Scoring V7 · Anti-spam</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <div className="text-xs text-muted-foreground">Cota YouTube API</div>
            <div className="flex items-center gap-2">
              <Progress value={quotaPercent} className="w-24 h-2" />
              <span className={`text-xs font-semibold ${quotaColor}`}>
                {quota.remaining} restantes
              </span>
            </div>
          </div>
          <Badge variant={apiOk === true ? "default" : apiOk === false ? "destructive" : "secondary"}>
            {apiOk === true ? "API OK" : apiOk === false ? "Offline" : "..."}
          </Badge>
        </div>
      </div>

      {/* Search bar */}
      <form onSubmit={handleSearch} className="flex gap-2 mb-6">
        <Input
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Buscar artista, música ou estilo..."
          disabled={loading}
          className="flex-1"
        />
        <Button type="submit" disabled={loading || !query.trim()} className="gap-2">
          <Search className="h-4 w-4" /> Buscar
        </Button>
        {(activeCat || results.length > 0) && (
          <Button type="button" variant="outline" onClick={() => doSearch()} disabled={loading} className="gap-2">
            <Trophy className="h-4 w-4" /> Ranking
          </Button>
        )}
      </form>

      {/* Categories grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-6">
        {categories.map(cat => {
          const si = seedInfo[cat.key]
          const isActive = activeCat === cat.key
          return (
            <Card
              key={cat.key}
              className={`cursor-pointer hover:shadow-md transition ${isActive ? "ring-2 ring-primary" : ""}`}
              onClick={() => doSearch(undefined, cat.key)}
            >
              <CardContent className="p-4">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xl">{cat.emoji}</span>
                  <span className="font-semibold text-sm">{cat.name}</span>
                </div>
                <p className="text-xs text-muted-foreground mb-2">{cat.desc}</p>
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-muted-foreground">
                    Seed {(si?.index ?? cat.last_seed) + 1}/{si?.total ?? cat.total_seeds}
                  </span>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-6 text-[10px] px-2"
                    onClick={(e) => { e.stopPropagation(); doSearch(undefined, cat.key, true) }}
                    disabled={loading}
                  >
                    <RefreshCw className="h-3 w-3 mr-1" /> Nova Seed
                  </Button>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Playlist button */}
      <div className="mb-6">
        <Button variant="outline" size="sm" onClick={loadPlaylist} disabled={loading} className="gap-2">
          <ListMusic className="h-4 w-4" />
          Playlist {playlistCount > 0 ? `(${playlistCount} vídeos em cache)` : "(Carregar)"}
        </Button>
      </div>

      {/* Message */}
      {msg && (
        <div className={`text-sm px-3 py-2 rounded-lg mb-4 ${
          msgType === "ok" ? "bg-green-50 text-green-700" :
          msgType === "loading" ? "bg-amber-50 text-amber-700" :
          msgType === "error" ? "bg-red-50 text-red-700" :
          "bg-muted text-muted-foreground"
        }`}>
          {msgType === "loading" && <Loader2 className="h-3.5 w-3.5 inline animate-spin mr-2" />}
          {msg}
          {postedHidden > 0 && msgType === "ok" && (
            <span className="ml-2 text-xs text-muted-foreground">({postedHidden} posted ocultos)</span>
          )}
        </div>
      )}

      {/* Results */}
      {results.length > 0 && (
        <>
          <div className="flex items-center justify-between mb-4">
            <div className="text-sm font-semibold">{visibleResults.length} vídeos · Score V7</div>
            <div className="flex items-center gap-2">
              <Checkbox
                id="hidePosted"
                checked={hidePosted}
                onCheckedChange={(c) => setHidePosted(!!c)}
              />
              <Label htmlFor="hidePosted" className="text-xs">Ocultar posted</Label>
            </div>
          </div>
          <div className="grid gap-3" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(230px, 1fr))" }}>
            {visibleResults.map((v, i) => (
              <VideoCard key={v.video_id} video={v} onClick={() => setDetailIdx(i)} />
            ))}
          </div>
        </>
      )}

      {/* Empty state */}
      {!loading && results.length === 0 && !msg && (
        <div className="text-center py-16 text-muted-foreground">
          <span className="text-5xl block mb-4">🎭</span>
          <p>Clique numa categoria ou busque um termo</p>
          <Button variant="link" onClick={() => doSearch()} className="mt-2">
            Ver ranking
          </Button>
        </div>
      )}

      {/* Detail modal */}
      <VideoDetailModal
        video={detailVideo}
        open={detailIdx !== null}
        onClose={() => setDetailIdx(null)}
        onDownloaded={loadQuota}
      />
    </div>
  )
}
