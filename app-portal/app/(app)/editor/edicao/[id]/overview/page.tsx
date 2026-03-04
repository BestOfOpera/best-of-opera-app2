"use client"

import { use } from "react"
import { EditorOverview } from "@/components/editor/overview"

export default function OverviewPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  return <EditorOverview edicaoId={Number(id)} />
}
