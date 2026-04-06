import { RedatorNewProject } from "@/components/redator/new-project"

export default async function RedatorNovoPage({ searchParams }: { searchParams: Promise<{ r2_folder?: string; scheduled_date?: string; project_id?: string }> }) {
  const params = await searchParams
  return <RedatorNewProject r2Folder={params.r2_folder} scheduledDate={params.scheduled_date} projectId={params.project_id} />
}
