"use client"

import { useState, useEffect } from "react"
import { useAuth } from "@/lib/auth-context"
import { editorApi, type AuthUser } from "@/lib/api/editor"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { UserPlus, Search, PencilLine, CheckCircle2, XCircle, Power, UserIcon, Eye } from "lucide-react"
import { useRouter } from "next/navigation"
import { RequireAdmin } from "@/components/auth/require-admin"

export default function AdminUsuariosPage() {
  return (
    <RequireAdmin>
      <AdminUsuariosContent />
    </RequireAdmin>
  )
}

function AdminUsuariosContent() {
    const router = useRouter()
    const { user: currentUser } = useAuth()
    const [users, setUsers] = useState<AuthUser[]>([])
    const [loading, setLoading] = useState(true)
    const [searchTerm, setSearchTerm] = useState("")

    // Modal states
    const [isModalOpen, setIsModalOpen] = useState(false)
    const [modalMode, setModalMode] = useState<"create" | "edit">("create")
    const [editingId, setEditingId] = useState<number | null>(null)

    // Form states
    const [formData, setFormData] = useState({
        nome: "",
        email: "",
        senha: "",
        role: "operador",
        ativo: true
    })
    const [submitting, setSubmitting] = useState(false)

    const loadUsers = async () => {
        try {
            const data = await editorApi.listarUsuarios()
            setUsers(data)
        } catch (err: any) {
            toast.error("Erro ao carregar usuários: " + (err.message || "Desconhecido"))
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        loadUsers()
    }, [])

    const handleOpenCreate = () => {
        setModalMode("create")
        setFormData({ nome: "", email: "", senha: "", role: "operador", ativo: true })
        setEditingId(null)
        setIsModalOpen(true)
    }

    const handleOpenEdit = (user: AuthUser) => {
        setModalMode("edit")
        setFormData({ nome: user.nome, email: user.email, senha: "", role: user.role, ativo: user.ativo })
        setEditingId(user.id)
        setIsModalOpen(true)
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setSubmitting(true)
        try {
            if (modalMode === "create") {
                await editorApi.registrarUsuario(formData)
                toast.success("Usuário criado com sucesso")
            } else if (editingId) {
                // Envia senha apenas se tiver sido preenchida
                const payload: any = { nome: formData.nome, email: formData.email, role: formData.role, ativo: formData.ativo }
                if (formData.senha) payload.senha = formData.senha
                await editorApi.atualizarUsuario(editingId, payload)
                toast.success("Usuário atualizado com sucesso")
            }
            setIsModalOpen(false)
            loadUsers()
        } catch (err: any) {
            toast.error("Erro ao salvar: " + (err.message || "Erro desconhecido"))
        } finally {
            setSubmitting(false)
        }
    }

    const handleToggleActive = async (user: AuthUser) => {
        if (user.id === currentUser?.id) {
            toast.error("Você não pode desativar o seu próprio usuário")
            return
        }

        try {
            await editorApi.atualizarUsuario(user.id, { ativo: !user.ativo })
            toast.success(`Usuário ${!user.ativo ? "ativado" : "desativado"} com sucesso.`)
            loadUsers()
        } catch (err: any) {
            toast.error("Erro ao alterar status: " + err.message)
        }
    }

    const filteredUsers = users.filter(u =>
        u.nome.toLowerCase().includes(searchTerm.toLowerCase()) ||
        u.email.toLowerCase().includes(searchTerm.toLowerCase())
    )

    return (
        <div className="mx-auto max-w-5xl space-y-6">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight">Gerenciar Usuários</h1>
                    <p className="text-sm text-muted-foreground mt-1">Controle de acessos, administradores e redatores da plataforma.</p>
                </div>
                <Button onClick={handleOpenCreate} className="gap-2 shrink-0">
                    <UserPlus className="h-4 w-4" />
                    Convidar Colaborador
                </Button>
            </div>

            <Card>
                <CardHeader className="pb-3 border-b">
                    <div className="flex items-center gap-2">
                        <div className="relative flex-1 max-w-md">
                            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                            <input
                                type="text"
                                placeholder="Buscar por nome ou email..."
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                                className="w-full flex h-9 rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 pl-9"
                            />
                        </div>
                    </div>
                </CardHeader>
                <CardContent className="p-0">
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b bg-muted/30">
                                    <th className="h-10 px-4 text-left font-medium text-muted-foreground">Usuário</th>
                                    <th className="h-10 px-4 text-left font-medium text-muted-foreground">Role</th>
                                    <th className="h-10 px-4 text-left font-medium text-muted-foreground">Status</th>
                                    <th className="h-10 px-4 text-left font-medium text-muted-foreground hidden sm:table-cell">Último Login</th>
                                    <th className="h-10 px-4 text-right font-medium text-muted-foreground">Ações</th>
                                </tr>
                            </thead>
                            <tbody>
                                {loading ? (
                                    <tr>
                                        <td colSpan={5} className="p-6">
                                            <div className="flex flex-col gap-4">
                                                {[1,2,3].map(i => (
                                                    <div key={i} className="flex items-center gap-4 animate-pulse px-4 py-2">
                                                        <div className="h-9 w-9 rounded-full bg-muted shrink-0" />
                                                        <div className="space-y-2 flex-1">
                                                            <div className="h-4 bg-muted rounded w-1/4" />
                                                            <div className="h-3 bg-muted rounded w-1/3" />
                                                        </div>
                                                        <div className="h-6 w-16 bg-muted rounded hidden sm:block" />
                                                        <div className="h-6 w-16 bg-muted rounded" />
                                                    </div>
                                                ))}
                                            </div>
                                        </td>
                                    </tr>
                                ) : filteredUsers.length === 0 ? (
                                    <tr>
                                        <td colSpan={5} className="py-16">
                                            <div className="flex flex-col items-center justify-center text-center">
                                                <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted mb-3">
                                                    <Search className="h-8 w-8 text-muted-foreground/50" />
                                                </div>
                                                <h3 className="text-lg font-semibold text-foreground">Nenhum usuário</h3>
                                                <p className="text-muted-foreground text-sm max-w-sm mt-1 mb-4">
                                                    Não foi possível encontrar nenhum usuário com o termo especificado.
                                                </p>
                                                {!users.length && (
                                                    <Button onClick={handleOpenCreate} size="sm">
                                                        <UserPlus className="mr-2 h-4 w-4" />
                                                        Convidar Colaborador
                                                    </Button>
                                                )}
                                            </div>
                                        </td>
                                    </tr>
                                ) : (
                                    filteredUsers.map((user) => (
                                        <tr key={user.id} className="border-b transition-colors hover:bg-muted/30 last:border-0">
                                            <td className="p-4">
                                                <div className="flex items-center gap-3">
                                                    <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/10 text-primary shrink-0">
                                                        {user.nome.charAt(0).toUpperCase()}
                                                    </div>
                                                    <div>
                                                        <div className="font-medium flex items-center gap-2">
                                                            {user.nome} {user.id === currentUser?.id && <span className="text-[10px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded ml-1">(Você)</span>}
                                                        </div>
                                                        <div className="text-xs text-muted-foreground">{user.email}</div>
                                                    </div>
                                                </div>
                                            </td>
                                            <td className="p-4">
                                                <Badge variant={user.role === "admin" ? "default" : "secondary"} className="capitalize">
                                                    {user.role}
                                                </Badge>
                                            </td>
                                            <td className="p-4">
                                                <div className="flex items-center gap-1.5">
                                                    {user.ativo ? <CheckCircle2 className="h-4 w-4 text-green-500" /> : <XCircle className="h-4 w-4 text-muted-foreground" />}
                                                    <span className={user.ativo ? "text-green-600 font-medium" : "text-muted-foreground"}>
                                                        {user.ativo ? "Ativo" : "Inativo"}
                                                    </span>
                                                </div>
                                            </td>
                                            <td className="p-4 hidden sm:table-cell text-muted-foreground text-xs">
                                                {user.ultimo_login ? new Date(user.ultimo_login).toLocaleString("pt-BR") : "Nunca acessou"}
                                            </td>
                                            <td className="p-4 text-right">
                                                <div className="flex justify-end gap-2 text-muted-foreground">
                                                    <button
                                                        className="p-1.5 rounded hover:bg-muted hover:text-foreground transition-colors"
                                                        title="Ver detalhes"
                                                        onClick={() => router.push(`/admin/usuarios/${user.id}`)}
                                                    >
                                                        <Eye className="h-4 w-4" />
                                                    </button>
                                                    <button
                                                        className="p-1.5 rounded hover:bg-muted hover:text-foreground transition-colors"
                                                        title="Editar usuário"
                                                        onClick={() => handleOpenEdit(user)}
                                                    >
                                                        <PencilLine className="h-4 w-4" />
                                                    </button>
                                                    <button
                                                        className={`p-1.5 rounded hover:bg-muted transition-colors ${user.id === currentUser?.id ? "opacity-30 cursor-not-allowed" : "hover:text-amber-600"}`}
                                                        title={user.ativo ? "Desativar acesso" : "Reativar acesso"}
                                                        onClick={() => handleToggleActive(user)}
                                                        disabled={user.id === currentUser?.id}
                                                    >
                                                        <Power className="h-4 w-4" />
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </CardContent>
            </Card>

            <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
                <DialogContent className="sm:max-w-[425px]">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <UserIcon className="h-5 w-5" />
                            {modalMode === "create" ? "Convidar Novo Colaborador" : "Editar Colaborador"}
                        </DialogTitle>
                        <DialogDescription>
                            {modalMode === "create"
                                ? "Preencha os dados do novo integrante. A senha inicial será arias2026 e ele precisará trocá-la no primeiro acesso."
                                : "Atualize os dados e as permissões de acesso deste colaborador."}
                        </DialogDescription>
                    </DialogHeader>
                    <form onSubmit={handleSubmit} className="space-y-4 pt-2">
                        <div className="space-y-2">
                            <Label htmlFor="nome">Nome Completo</Label>
                            <Input id="nome" required value={formData.nome} onChange={e => setFormData({ ...formData, nome: e.target.value })} />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="email">Email</Label>
                            <Input id="email" type="email" required value={formData.email} onChange={e => setFormData({ ...formData, email: e.target.value })} />
                        </div>
                        {modalMode === "edit" && (
                            <div className="space-y-2">
                                <Label htmlFor="senha">Nova senha <span className="text-muted-foreground font-normal">(deixe em branco para não alterar)</span></Label>
                                <Input
                                    id="senha"
                                    type="password"
                                    value={formData.senha}
                                    onChange={e => setFormData({ ...formData, senha: e.target.value })}
                                    placeholder="••••••••"
                                />
                            </div>
                        )}
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label>Nível de Acesso</Label>
                                <Select value={formData.role} onValueChange={(val) => setFormData({ ...formData, role: val })}>
                                    <SelectTrigger><SelectValue /></SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="operador">Operador</SelectItem>
                                        <SelectItem value="admin">Admin</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                            <div className="space-y-2">
                                <Label>Status de Acesso</Label>
                                <Select
                                    disabled={editingId === currentUser?.id}
                                    value={formData.ativo ? "ativo" : "inativo"}
                                    onValueChange={(val) => setFormData({ ...formData, ativo: val === "ativo" })}
                                >
                                    <SelectTrigger><SelectValue /></SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="ativo">Ativo</SelectItem>
                                        <SelectItem value="inativo">Inativo (Bloqueado)</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>
                        <DialogFooter className="mt-6 gap-2 sm:gap-0">
                            <Button type="button" variant="ghost" onClick={() => setIsModalOpen(false)}>Cancelar</Button>
                            <Button type="submit" disabled={submitting}>
                                {submitting ? "Salvando..." : "Salvar Colaborador"}
                            </Button>
                        </DialogFooter>
                    </form>
                </DialogContent>
            </Dialog>
        </div>
    )
}
