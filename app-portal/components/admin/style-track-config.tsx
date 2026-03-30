import * as React from "react"
import { useState } from "react"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Card } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Button } from "@/components/ui/button"
import { ChevronDown, ChevronUp } from "lucide-react"
import { cn } from "@/lib/utils"

export interface StyleConfig {
    fontname?: string
    fontsize?: number
    primarycolor?: string
    outlinecolor?: string
    outline?: number
    shadow?: number
    alignment?: number
    marginv?: number
    bold?: boolean
    italic?: boolean
    [key: string]: any
}

interface StyleTrackConfigProps {
    title: string
    description?: string
    value: StyleConfig
    onChange: (value: StyleConfig) => void
    showHookSizes?: boolean
}

export function StyleTrackConfig({ title, description, value = {}, onChange, showHookSizes = false }: StyleTrackConfigProps) {
    const [showRaw, setShowRaw] = useState(false)

    const handleChange = (field: keyof StyleConfig, val: any) => {
        const v = Number.isNaN(val) ? undefined : val
        onChange({ ...value, [field]: v })
    }

    const alignmentGrid = [
        [7, 8, 9],
        [4, 5, 6],
        [1, 2, 3]
    ]

    return (
        <Card className="p-5 space-y-5 bg-card/50 border-border/50 shadow-sm">
            <div className="flex items-start justify-between">
                <div>
                    <h4 className="font-semibold text-sm text-foreground">{title}</h4>
                    {description && <p className="text-[11px] text-muted-foreground mt-0.5">{description}</p>}
                </div>
                <Button type="button" variant="ghost" size="sm" onClick={() => setShowRaw(!showRaw)} className="h-8 gap-1 text-xs text-muted-foreground">
                    {showRaw ? "Ocultar JSON bruto" : "JSON bruto (Experts)"}
                    {showRaw ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                </Button>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {/* Font Name */}
                <div className="col-span-2 space-y-2">
                    <Label className="text-xs font-semibold text-muted-foreground">Font Name</Label>
                    <Input
                        value={value.fontname || ""}
                        onChange={e => handleChange("fontname", e.target.value)}
                        placeholder="TeX Gyre Pagella"
                        className="h-9 bg-background font-mono text-sm"
                    />
                </div>

                {/* Font Size */}
                <div className="space-y-2">
                    <Label className="text-xs font-semibold text-muted-foreground">Font Size (px)</Label>
                    <Input
                        type="number"
                        value={value.fontsize !== undefined ? value.fontsize : ""}
                        onChange={e => handleChange("fontsize", parseInt(e.target.value))}
                        className="h-9 bg-background font-mono text-sm"
                    />
                </div>

                {/* Bold & Italic */}
                <div className="flex gap-4 items-end pb-1">
                    <div className="flex items-center space-x-2">
                        <Checkbox
                            id={`bold-${title.replace(/\s/g, "")}`}
                            checked={!!value.bold}
                            onCheckedChange={c => handleChange("bold", !!c)}
                        />
                        <Label htmlFor={`bold-${title.replace(/\s/g, "")}`} className="cursor-pointer text-xs font-semibold">Bold</Label>
                    </div>
                    <div className="flex items-center space-x-2">
                        <Checkbox
                            id={`italic-${title.replace(/\s/g, "")}`}
                            checked={!!value.italic}
                            onCheckedChange={c => handleChange("italic", !!c)}
                        />
                        <Label htmlFor={`italic-${title.replace(/\s/g, "")}`} className="cursor-pointer text-xs font-semibold">Italic</Label>
                    </div>
                </div>

                {/* Gancho & CTA font sizes (overlay only) */}
                {showHookSizes && (
                    <>
                        <div className="space-y-2">
                            <Label className="text-xs font-semibold text-muted-foreground">Gancho (px)</Label>
                            <Input
                                type="number"
                                value={value.gancho_fontsize !== undefined ? value.gancho_fontsize : ""}
                                onChange={e => handleChange("gancho_fontsize", parseInt(e.target.value))}
                                placeholder="60"
                                className="h-9 bg-background font-mono text-sm"
                            />
                        </div>
                        <div className="space-y-2">
                            <Label className="text-xs font-semibold text-muted-foreground">CTA (px)</Label>
                            <Input
                                type="number"
                                value={value.cta_fontsize !== undefined ? value.cta_fontsize : ""}
                                onChange={e => handleChange("cta_fontsize", parseInt(e.target.value))}
                                placeholder="58"
                                className="h-9 bg-background font-mono text-sm"
                            />
                        </div>
                    </>
                )}

                {/* Primary Color */}
                <div className="space-y-2">
                    <Label className="text-xs font-semibold text-muted-foreground">Primary Color</Label>
                    <div className="flex gap-1 p-1 bg-background border border-input rounded-md focus-within:ring-1 focus-within:ring-ring h-9 overflow-hidden">
                        <input
                            type="color"
                            className="w-8 h-full p-0 border-0 cursor-pointer bg-transparent shrink-0"
                            value={value.primarycolor || "#FFFFFF"}
                            onChange={e => handleChange("primarycolor", e.target.value.toUpperCase())}
                        />
                        <Input
                            value={value.primarycolor || ""}
                            onChange={e => handleChange("primarycolor", e.target.value.toUpperCase())}
                            placeholder="#FFFFFF"
                            maxLength={7}
                            className="flex-1 min-w-0 border-0 h-full uppercase font-mono text-xs focus-visible:ring-0 shadow-none px-1"
                        />
                    </div>
                </div>

                {/* Outline Color */}
                <div className="space-y-2">
                    <Label className="text-xs font-semibold text-muted-foreground">Outline Color</Label>
                    <div className="flex gap-1 p-1 bg-background border border-input rounded-md focus-within:ring-1 focus-within:ring-ring h-9 overflow-hidden">
                        <input
                            type="color"
                            className="w-8 h-full p-0 border-0 cursor-pointer bg-transparent shrink-0"
                            value={value.outlinecolor || "#000000"}
                            onChange={e => handleChange("outlinecolor", e.target.value.toUpperCase())}
                        />
                        <Input
                            value={value.outlinecolor || ""}
                            onChange={e => handleChange("outlinecolor", e.target.value.toUpperCase())}
                            placeholder="#000000"
                            maxLength={7}
                            className="flex-1 min-w-0 border-0 h-full uppercase font-mono text-xs focus-visible:ring-0 shadow-none px-1"
                        />
                    </div>
                </div>

                {/* Outline & Shadow & Margin V */}
                <div className="space-y-2">
                    <Label className="text-xs font-semibold text-muted-foreground">Outline (0-5)</Label>
                    <Input
                        type="number"
                        min={0} max={5}
                        value={value.outline !== undefined ? value.outline : ""}
                        onChange={e => handleChange("outline", parseInt(e.target.value))}
                        className="h-9 bg-background font-mono text-sm"
                    />
                </div>
                <div className="space-y-2">
                    <Label className="text-xs font-semibold text-muted-foreground">Shadow (0-5)</Label>
                    <Input
                        type="number"
                        min={0} max={5}
                        value={value.shadow !== undefined ? value.shadow : ""}
                        onChange={e => handleChange("shadow", parseInt(e.target.value))}
                        className="h-9 bg-background font-mono text-sm"
                    />
                </div>

                {/* Margin V */}
                <div className="space-y-2">
                    <Label className="text-xs font-semibold text-muted-foreground" title="Posição vertical (px) — Canvas 1920px">Margin V (px)</Label>
                    <Input
                        type="number"
                        value={value.marginv !== undefined ? value.marginv : ""}
                        onChange={e => handleChange("marginv", parseInt(e.target.value))}
                        className="h-9 bg-background font-mono text-sm"
                    />
                </div>

                {/* Alignment Grid */}
                <div className="md:col-span-12 space-y-3 mt-1 pt-4 border-t border-border/50">
                    <div className="flex flex-col items-center">
                        <Label className="text-xs font-semibold text-muted-foreground block mb-2">Alignment (Numpad 1-9)</Label>
                        <div className="grid grid-cols-3 gap-1 p-1 bg-muted rounded-md border border-border/50">
                            {alignmentGrid.map((row) => (
                                row.map(num => (
                                    <button
                                        key={num}
                                        type="button"
                                        onClick={() => handleChange("alignment", num)}
                                        className={cn(
                                            "w-9 h-9 rounded text-xs font-medium transition-colors flex items-center justify-center",
                                            value.alignment === num 
                                                ? "bg-primary text-primary-foreground shadow-sm ring-1 ring-primary" 
                                                : "bg-background text-muted-foreground hover:bg-background/80 hover:text-foreground border border-transparent hover:border-border"
                                        )}
                                    >
                                        {num}
                                    </button>
                                ))
                            ))}
                        </div>
                    </div>
                </div>
            </div>

            {/* Raw JSON */}
            {showRaw && (
                <div className="space-y-2 pt-4 border-t border-border/50 animate-in fade-in slide-in-from-top-2">
                    <Label className="font-semibold text-muted-foreground text-xs">JSON Bruto (Fallback)</Label>
                    <Textarea
                        value={JSON.stringify(value, null, 2)}
                        onChange={e => {
                            try {
                                const parsed = JSON.parse(e.target.value)
                                onChange(parsed)
                            } catch (err) {}
                        }}
                        className="font-mono text-[11px] min-h-[150px] bg-zinc-950 text-emerald-400 border-zinc-800 shadow-inner focus-visible:ring-emerald-500/50"
                        spellCheck={false}
                    />
                </div>
            )}
        </Card>
    )
}
