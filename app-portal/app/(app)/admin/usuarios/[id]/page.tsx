"use client"

import { useState, useEffect } from "react"
import { useParams, useRouter } from "next/navigation"
import { editorApi, AuthUser } from "@/lib/api/editor"
import { RequireAdmin } from "@/components/auth/require-admin"
import { ArrowLeft, Clock, Calendar, LogIn, BarChart3 } from "lucide-react"

function formatMinutes(min: number): string {
  if (min < 60) return `${min}min`
  const h = Math.floor(min / 60)
  const m = min % 60
  return m > 0 ? `${h}h ${m}min` : `${h}h`
}

function UserDetailContent() {
  const params = useParams()
  const router = useRouter()
  const userId = Number(params.id)

  const [user, setUser] = useState<AuthUser | null>(null)
  const [logins, setLogins] = useState<any>(null)
  const [sessions, setSessions] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!userId) return

    const fetchAll = async () => {
      try {
        const [users, loginsRes, sessionsRes] = await Promise.all([
          editorApi.listarUsuarios(),
          editorApi.getUserLoginHistory(userId, 30),
          editorApi.getUserSessions(userId, 30),
        ])

        const foundUser = users.find((u) => u.id === userId) || null
        setUser(foundUser)
        setLogins(loginsRes)
        setSessions(sessionsRes)
      } catch (err) {
        console.error("Erro ao carregar dados do usuário:", err)
      } finally {
        setLoading(false)
      }
    }

    fetchAll()
  }, [userId])

  if (loading) {
    return (
      <div className="p-6 space-y-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-muted rounded w-48" />
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map(i => <div key={i} className="h-24 bg-muted rounded-lg" />)}
          </div>
        </div>
      </div>
    )
  }

  if (!user) {
    return (
      <div className="p-6">
        <button onClick={() => router.back()} className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-4">
          <ArrowLeft className="h-4 w-4" /> Voltar
        </button>
        <p className="text-muted-foreground">Usuário não encontrado.</p>
      </div>
    )
  }

  const summaryCards = [
    { label: "Hoje", value: formatMinutes(sessions?.today_minutes || 0), icon: Clock, sub: "ativo" },
    { label: "Semana", value: formatMinutes(sessions?.week_minutes || 0), icon: Calendar, sub: "ativo" },
    { label: "Mês", value: formatMinutes(sessions?.month_minutes || 0), icon: BarChart3, sub: "ativo" },
    { label: "Total", value: logins?.total || 0, icon: LogIn, sub: "logins" },
  ]

  const last14Days = (sessions?.by_day || []).slice(0, 14).reverse()
  const maxMinutes = Math.max(...last14Days.map((d: any) => d.minutes), 1)

  return (
    <div className="p-6 space-y-6 max-w-4xl">
      {/* Header */}
      <div>
        <button onClick={() => router.back()} className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-4">
          <ArrowLeft className="h-4 w-4" /> Voltar
        </button>
        <div className="flex items-center gap-4">
          <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center text-lg font-bold text-primary">
            {(user.nome || "?")[0].toUpperCase()}
          </div>
          <div>
            <h1 className="text-xl font-bold">{user.nome}</h1>
            <div className="flex items-center gap-3 text-sm text-muted-foreground">
              <span>{user.email}</span>
              <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${user.role === "admin" ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"}`}>
                {user.role}
              </span>
              <span className={`flex items-center gap-1 ${user.ativo ? "text-green-500" : "text-red-500"}`}>
                <span className="h-1.5 w-1.5 rounded-full bg-current" />
                {user.ativo ? "Ativo" : "Inativo"}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {summaryCards.map(card => (
          <div key={card.label} className="rounded-lg border bg-card p-4">
            <div className="flex items-center gap-2 mb-2">
              <card.icon className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">{card.label}</span>
            </div>
            <div className="text-2xl font-bold">{card.value}</div>
            <div className="text-xs text-muted-foreground">{card.sub}</div>
          </div>
        ))}
      </div>

      {/* Atividade Diária */}
      {last14Days.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-muted-foreground mb-3">Atividade diária (últimos 14 dias)</h3>
          <div className="rounded-lg border bg-card p-4">
            <div className="flex items-end gap-1 h-32">
              {last14Days.map((day: any, i: number) => {
                const height = Math.max(4, (day.minutes / maxMinutes) * 100)
                const dayLabel = new Date(day.date + "T00:00:00").toLocaleDateString("pt-BR", { weekday: "short" }).slice(0, 3)
                return (
                  <div key={i} className="flex-1 flex flex-col items-center gap-1">
                    <div className="w-full flex items-end justify-center" style={{ height: "100px" }}>
                      <div
                        className="w-full max-w-[24px] bg-primary/80 rounded-t"
                        style={{ height: `${height}%` }}
                        title={`${day.date}: ${formatMinutes(day.minutes)}`}
                      />
                    </div>
                    <span className="text-[10px] text-muted-foreground">{dayLabel}</span>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      )}

      {/* Histórico de Logins */}
      <div>
        <h3 className="text-sm font-medium text-muted-foreground mb-3">Histórico de logins</h3>
        <div className="rounded-lg border bg-card divide-y">
          {(logins?.logins || []).length === 0 ? (
            <div className="p-4 text-sm text-muted-foreground">Nenhum login registrado.</div>
          ) : (
            (logins.logins || []).slice(0, 20).map((login: any, i: number) => (
              <div key={i} className="flex items-center gap-4 px-4 py-3 text-sm">
                <span className="text-muted-foreground w-36">
                  {login.timestamp ? new Date(login.timestamp).toLocaleString("pt-BR") : "—"}
                </span>
                <span className="text-muted-foreground w-28 font-mono text-xs">{login.ip || "—"}</span>
                <span className="text-muted-foreground">{login.device || "—"}</span>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Sessões Recentes */}
      {(sessions?.sessions || []).length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-muted-foreground mb-3">Sessões recentes</h3>
          <div className="rounded-lg border bg-card divide-y">
            {(sessions.sessions || []).slice(0, 10).map((s: any, i: number) => (
              <div key={i} className="flex items-center gap-4 px-4 py-3 text-sm">
                <span className="text-muted-foreground w-36">
                  {new Date(s.started).toLocaleString("pt-BR", { hour: "2-digit", minute: "2-digit" })}
                  {" \u2192 "}
                  {new Date(s.ended).toLocaleString("pt-BR", { hour: "2-digit", minute: "2-digit" })}
                </span>
                <span className="font-medium w-20">{formatMinutes(s.duration_min)}</span>
                <div className="flex-1">
                  <div className="w-full bg-muted rounded-full h-1.5">
                    <div
                      className="bg-primary h-1.5 rounded-full"
                      style={{ width: `${Math.min(100, (s.duration_min / 480) * 100)}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default function UserDetailPage() {
  return (
    <RequireAdmin>
      <UserDetailContent />
    </RequireAdmin>
  )
}
