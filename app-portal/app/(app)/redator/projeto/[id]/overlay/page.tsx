"use client"

import { use } from "react"
import { RedatorApproveOverlay } from "@/components/redator/approve-overlay"

export default function OverlayPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  return <RedatorApproveOverlay projectId={Number(id)} />
}
