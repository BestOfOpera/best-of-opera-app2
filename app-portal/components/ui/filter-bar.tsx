"use client"

import { useEffect, useState } from "react"
import { Search, X, ChevronLeft, ChevronRight } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

const ALL_VALUE = "__all__"

interface FilterBarProps {
  searchPlaceholder?: string
  searchValue: string
  onSearchChange: (value: string) => void
  statusOptions?: { value: string; label: string }[]
  statusValue?: string
  onStatusChange?: (value: string) => void
  showStatus?: boolean
  sortOptions: { value: string; label: string }[]
  sortValue: string
  onSortChange: (value: string) => void
  page?: number
  totalPages?: number
  total?: number
  onPageChange?: (page: number) => void
  showPagination?: boolean
}

export function FilterBar({
  searchPlaceholder = "Buscar...",
  searchValue,
  onSearchChange,
  statusOptions,
  statusValue,
  onStatusChange,
  showStatus = true,
  sortOptions,
  sortValue,
  onSortChange,
  page = 1,
  totalPages = 1,
  total = 0,
  onPageChange,
  showPagination = false,
}: FilterBarProps) {
  const [localSearch, setLocalSearch] = useState(searchValue)

  useEffect(() => {
    setLocalSearch(searchValue)
  }, [searchValue])

  useEffect(() => {
    const timer = setTimeout(() => {
      if (localSearch !== searchValue) {
        onSearchChange(localSearch)
      }
    }, 400)
    return () => clearTimeout(timer)
  }, [localSearch])

  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:flex-wrap">
      <div className="relative flex-1 min-w-[200px]">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder={searchPlaceholder}
          value={localSearch}
          onChange={(e) => setLocalSearch(e.target.value)}
          className="pl-9 pr-8"
        />
        {localSearch && (
          <button
            type="button"
            onClick={() => { setLocalSearch(""); onSearchChange("") }}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {showStatus && statusOptions && statusOptions.length > 0 && onStatusChange && (
        <Select
          value={statusValue || ALL_VALUE}
          onValueChange={(v) => onStatusChange(v === ALL_VALUE ? "" : v)}
        >
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            {statusOptions.map((opt) => (
              <SelectItem key={opt.value || ALL_VALUE} value={opt.value || ALL_VALUE}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}

      <Select value={sortValue} onValueChange={onSortChange}>
        <SelectTrigger className="w-[180px]">
          <SelectValue placeholder="Ordenar" />
        </SelectTrigger>
        <SelectContent>
          {sortOptions.map((opt) => (
            <SelectItem key={opt.value} value={opt.value}>
              {opt.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {showPagination && totalPages > 1 && onPageChange && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground ml-auto">
          <span>{total} itens</span>
          <span className="mx-1">·</span>
          <span>Pag {page}/{totalPages}</span>
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            disabled={page <= 1}
            onClick={() => onPageChange(page - 1)}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            disabled={page >= totalPages}
            onClick={() => onPageChange(page + 1)}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      )}
    </div>
  )
}
