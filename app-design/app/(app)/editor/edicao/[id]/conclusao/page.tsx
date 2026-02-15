"use client"

import { use } from "react"
import { EditorConclusion } from "@/components/editor/conclusion"

export default function ConclusaoPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  return <EditorConclusion edicaoId={Number(id)} />
}
