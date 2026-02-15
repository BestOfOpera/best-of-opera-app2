"use client"

import { use } from "react"
import { EditorValidateAlignment } from "@/components/editor/validate-alignment"

export default function AlinhamentoPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  return <EditorValidateAlignment edicaoId={Number(id)} />
}
