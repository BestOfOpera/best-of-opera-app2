import { RedatorNewProject } from "@/components/redator/new-project"

export default async function RedatorNovoPage({ searchParams }: { searchParams: Promise<{ r2_folder?: string }> }) {
  const params = await searchParams
  return <RedatorNewProject r2Folder={params.r2_folder} />
}
