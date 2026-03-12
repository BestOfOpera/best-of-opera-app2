"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/lib/auth-context"
import { editorApi } from "@/lib/api/editor"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Loader2, KeyRound } from "lucide-react"

export default function AlterarSenhaPage() {
  const { user, isLoading, logout } = useAuth()
  const router = useRouter()
  const [senhaNova, setSenhaNova] = useState("")
  const [senhaConfirm, setSenhaConfirm] = useState("")
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (!isLoading && !user) {
      router.push("/login")
    }
  }, [user, isLoading, router])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (senhaNova !== senhaConfirm) {
      toast.error("As senhas não coincidem")
      return
    }
    if (senhaNova.length < 6) {
      toast.error("A senha deve ter pelo menos 6 caracteres")
      return
    }
    setSubmitting(true)
    try {
      await editorApi.alterarSenha(senhaNova)
      toast.success("Senha alterada com sucesso!")
      // Força reload do usuário para limpar must_change_password
      logout()
    } catch (err: any) {
      toast.error(err.message || "Erro ao alterar senha")
    } finally {
      setSubmitting(false)
    }
  }

  if (isLoading || !user) return null

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-br from-[#1a1a2e] to-[#0f3460] p-4">
      <div className="w-full max-w-md space-y-8 rounded-2xl border border-border/50 bg-card p-8 shadow-2xl animate-in fade-in zoom-in-95 duration-500">
        <div className="flex flex-col items-center text-center space-y-2">
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 mb-2">
            <KeyRound className="h-7 w-7 text-primary" />
          </div>
          <h1 className="font-serif text-2xl font-semibold tracking-tight text-foreground">
            Crie sua senha de acesso
          </h1>
          <p className="text-sm text-muted-foreground max-w-xs">
            Olá, {user.nome.split(" ")[0]}! Por segurança, defina uma senha pessoal antes de continuar.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-2">
            <Label htmlFor="senha-nova">Nova senha</Label>
            <Input
              id="senha-nova"
              type="password"
              placeholder="Mínimo 6 caracteres"
              value={senhaNova}
              onChange={(e) => setSenhaNova(e.target.value)}
              required
              className="h-11"
              autoFocus
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="senha-confirm">Confirmar nova senha</Label>
            <Input
              id="senha-confirm"
              type="password"
              placeholder="Repita a senha"
              value={senhaConfirm}
              onChange={(e) => setSenhaConfirm(e.target.value)}
              required
              className="h-11"
            />
          </div>

          <Button type="submit" className="w-full h-11 text-base" disabled={submitting}>
            {submitting ? <Loader2 className="mr-2 h-5 w-5 animate-spin" /> : null}
            {submitting ? "Salvando..." : "Definir senha e entrar"}
          </Button>
        </form>
      </div>
    </div>
  )
}
