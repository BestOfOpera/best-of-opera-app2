"use client"

import { useState } from "react"
import { cn } from "@/lib/utils"
import { ChevronDown, Check } from "lucide-react"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"

const brands = [
  { id: "best-of-opera", name: "Best of Opera", initials: "BO" },
  { id: "opera-legends", name: "Opera Legends", initials: "OL" },
  { id: "classical-voices", name: "Classical Voices", initials: "CV" },
]

export function BrandSelector() {
  const [selected, setSelected] = useState(brands[0])
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button className="flex items-center gap-2 rounded-md border border-border bg-card px-3 py-1.5 transition-colors hover:bg-muted/50">
          <span className="flex h-5 w-5 items-center justify-center rounded bg-primary/10 text-[9px] font-bold text-primary">{selected.initials}</span>
          <span className="text-sm font-medium text-foreground">{selected.name}</span>
          <ChevronDown className="ml-1 h-3 w-3 text-muted-foreground" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-52">
        {brands.map((brand) => (
          <DropdownMenuItem key={brand.id} onClick={() => setSelected(brand)} className={cn("flex items-center gap-2.5 cursor-pointer", selected.id === brand.id && "bg-muted")}>
            <span className="flex h-5 w-5 items-center justify-center rounded bg-primary/10 text-[9px] font-bold text-primary">{brand.initials}</span>
            <span className="flex-1 text-sm">{brand.name}</span>
            {selected.id === brand.id && <Check className="h-3.5 w-3.5 text-primary" />}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
