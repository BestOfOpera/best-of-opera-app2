"use client"

import { use } from "react"
import { EditorValidateLyrics } from "@/components/editor/validate-lyrics"

export default function LetraPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  return <EditorValidateLyrics edicaoId={Number(id)} />
}
