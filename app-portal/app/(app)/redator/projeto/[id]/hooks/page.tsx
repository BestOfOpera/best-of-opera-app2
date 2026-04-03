"use client"

import { use } from "react"
import { RedatorApproveHooksRC } from "@/components/redator/approve-hooks-rc"

export default function HooksPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  return <RedatorApproveHooksRC projectId={Number(id)} />
}
