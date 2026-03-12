"use client"

import { createContext, useContext, useState, ReactNode } from "react"
import { Perfil } from "@/lib/api/editor"

interface BrandContextType {
  selectedBrand: Perfil | null
  setSelectedBrand: (brand: Perfil | null) => void
}

const BrandContext = createContext<BrandContextType>({
  selectedBrand: null,
  setSelectedBrand: () => {},
})

export function BrandProvider({ children }: { children: ReactNode }) {
  const [selectedBrand, setSelectedBrand] = useState<Perfil | null>(null)

  return (
    <BrandContext.Provider value={{ selectedBrand, setSelectedBrand }}>
      {children}
    </BrandContext.Provider>
  )
}

export function useBrand() {
  return useContext(BrandContext)
}
