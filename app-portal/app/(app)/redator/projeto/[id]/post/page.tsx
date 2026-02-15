"use client"

import { use } from "react"
import { RedatorApprovePost } from "@/components/redator/approve-post"

export default function PostPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  return <RedatorApprovePost projectId={Number(id)} />
}
