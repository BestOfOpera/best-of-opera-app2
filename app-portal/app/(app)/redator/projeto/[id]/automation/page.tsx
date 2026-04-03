"use client"

import { use } from "react"
import { RedatorApproveAutomationRC } from "@/components/redator/approve-automation-rc"

export default function AutomationPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  return <RedatorApproveAutomationRC projectId={Number(id)} />
}
