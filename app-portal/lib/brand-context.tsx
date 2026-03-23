"use client"

import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from "react"
import { Perfil } from "@/lib/api/editor"

const STORAGE_KEY = "selectedBrandId"

interface BrandContextType {
  selectedBrand: Perfil | null
  setSelectedBrand: (brand: Perfil | null) => void
  savedBrandId: string | null
}

const BrandContext = createContext<BrandContextType>({
  selectedBrand: null,
  setSelectedBrand: () => {},
  savedBrandId: null,
})

export function BrandProvider({ children }: { children: ReactNode }) {
  const [selectedBrand, setSelectedBrandState] = useState<Perfil | null>(null)
  const [savedBrandId, setSavedBrandId] = useState<string | null>(null)

  useEffect(() => {
    const id = localStorage.getItem(STORAGE_KEY)
    setSavedBrandId(id)
  }, [])

  const setSelectedBrand = useCallback((brand: Perfil | null) => {
    setSelectedBrandState(brand)
    if (brand) {
      localStorage.setItem(STORAGE_KEY, String(brand.id))
    } else {
      localStorage.removeItem(STORAGE_KEY)
    }
  }, [])

  return (
    <BrandContext.Provider value={{ selectedBrand, setSelectedBrand, savedBrandId }}>
      {children}
    </BrandContext.Provider>
  )
}

export function useBrand() {
  return useContext(BrandContext)
}
