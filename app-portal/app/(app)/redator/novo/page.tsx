import { RedatorNewProject } from "@/components/redator/new-project"

export default function RedatorNovoPage({ searchParams }: { searchParams: { r2_folder?: string } }) {
  return <RedatorNewProject r2Folder={searchParams.r2_folder} />
}
