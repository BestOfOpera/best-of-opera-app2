"use client"

import { use } from "react"
import { RedatorExportPage } from "@/components/redator/export-page"

export default function ExportarPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  return <RedatorExportPage projectId={Number(id)} />
}
