"use client"

import { use } from "react"
import { RedatorApproveYouTube } from "@/components/redator/approve-youtube"

export default function YoutubePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  return <RedatorApproveYouTube projectId={Number(id)} />
}
