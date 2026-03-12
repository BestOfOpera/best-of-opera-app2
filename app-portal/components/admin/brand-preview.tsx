"use client"

import * as React from "react"
import { type Perfil } from "@/lib/api/editor"
import { type StyleConfig } from "./style-track-config"
import { cn } from "@/lib/utils"

interface BrandPreviewProps {
    perfil: Partial<Perfil>
}

export function BrandPreview({ perfil }: BrandPreviewProps) {
    const videoWidth = perfil.video_width || 1080
    const videoHeight = perfil.video_height || 1920
    const aspectRatio = videoWidth / videoHeight
    
    // Scale factor for the preview
    const previewWidth = 260
    const previewHeight = previewWidth / aspectRatio
    const scale = previewWidth / videoWidth

    // Inject fonts
    React.useEffect(() => {
        if (!perfil.font_name || !perfil.font_file_r2_key) return

        const fontUrl = `https://pub-8f924df9742c43108600d81c20e58814.r2.dev/${perfil.font_file_r2_key}`
        const fontFace = new FontFace(perfil.font_name, `url(${fontUrl})`)
        
        fontFace.load().then((loadedFace) => {
            document.fonts.add(loadedFace)
        }).catch(err => {
            console.error("Erro ao carregar fonte:", err)
        })
    }, [perfil.font_name, perfil.font_file_r2_key])

    const getStyle = (config: StyleConfig): React.CSSProperties => {
        const {
            fontname,
            fontsize = 20,
            primarycolor = "#FFFFFF",
            outlinecolor = "#000000",
            outline = 0,
            shadow = 0,
            bold,
            italic,
            alignment = 2,
            marginv = 0
        } = config

        const style: React.CSSProperties = {
            fontFamily: fontname || perfil.font_name || "var(--font-sans)",
            fontSize: `${fontsize * scale}px`,
            color: primarycolor,
            fontWeight: bold ? "bold" : "normal",
            fontStyle: italic ? "italic" : "normal",
            position: "absolute",
            width: "100%",
            left: 0,
            textAlign: alignment % 3 === 1 ? "left" : alignment % 3 === 2 ? "center" : "right",
            paddingLeft: alignment % 3 === 1 ? "10%" : "5%",
            paddingRight: alignment % 3 === 3 ? "10%" : "5%",
            zIndex: 10,
            pointerEvents: "none",
        }

        // Vertical positioning
        if (alignment >= 1 && alignment <= 3) { // Bottom
            style.bottom = `${marginv * scale}px`
        } else if (alignment >= 4 && alignment <= 6) { // Middle
            style.top = "50%"
            style.transform = "translateY(-50%)"
        } else if (alignment >= 7 && alignment <= 9) { // Top
            style.top = `${marginv * scale}px`
        }

        // Outline & Shadow mapping
        const shadows = []
        if (outline > 0) {
            const o = outline * scale
            shadows.push(`${o}px ${o}px 0 ${outlinecolor}`)
            shadows.push(`-${o}px ${o}px 0 ${outlinecolor}`)
            shadows.push(`${o}px -${o}px 0 ${outlinecolor}`)
            shadows.push(`-${o}px -${o}px 0 ${outlinecolor}`)
        }
        if (shadow > 0) {
            const s = shadow * scale
            shadows.push(`${s}px ${s}px ${s}px rgba(0,0,0,0.8)`)
        }

        if (shadows.length > 0) {
            style.textShadow = shadows.join(", ")
        }

        return style
    }

    return (
        <div 
            className="relative bg-zinc-800 rounded-md overflow-hidden shadow-2xl border border-zinc-700/50 flex flex-col items-center"
            style={{ 
                width: `${previewWidth}px`, 
                height: `${previewHeight}px` 
            }}
        >
            {/* Background placeholder */}
            <div className="absolute inset-0 block bg-gradient-to-t from-black/90 via-black/40 to-black/40" />
            
            {/* Overlay Track */}
            {perfil.overlay_style && (
                <div style={getStyle(perfil.overlay_style as StyleConfig)}>
                    {(perfil.overlay_style as any).text || "CONTEÚDO DO OVERLAY"}
                </div>
            )}

            {/* Lyrics Track */}
            {perfil.lyrics_style && (
                <div style={getStyle(perfil.lyrics_style as StyleConfig)}>
                    {(perfil.lyrics_style as any).text || "Lírica Principal (Lyrics)"}
                </div>
            )}

            {/* Tradução Track */}
            {perfil.traducao_style && (
                <div style={getStyle(perfil.traducao_style as StyleConfig)}>
                    {(perfil.traducao_style as any).text || "Tradução Acompanhamento"}
                </div>
            )}

            {/* Info overlay */}
            <div className="absolute bottom-2 right-2 text-[10px] text-zinc-500 font-mono">
                {videoWidth}x{videoHeight}
            </div>
        </div>
    )
}
