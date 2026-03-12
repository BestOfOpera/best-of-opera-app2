"use client"

import { useEffect, useRef, useState } from "react"

export function usePolling(callback: () => Promise<void>, intervalMs: number, enabled: boolean) {
  const savedCallback = useRef(callback)
  savedCallback.current = callback

  useEffect(() => {
    if (!enabled) return
    const tick = async () => {
      try {
        await savedCallback.current()
      } catch (err) {
        console.error("usePolling error:", err)
      }
    }
    tick()
    const id = setInterval(tick, intervalMs)
    return () => clearInterval(id)
  }, [intervalMs, enabled])
}

const FAST_INTERVAL_MS = 3_000
const SLOW_INTERVAL_MS = 15_000
const SLOW_AFTER_MS    = 120_000 // 2 minutes

export function useAdaptivePolling(
  callback: () => Promise<void>,
  enabled: boolean,
): { isSlowPolling: boolean } {
  const savedCallback = useRef(callback)
  savedCallback.current = callback
  const [isSlowPolling, setIsSlowPolling] = useState(false)

  useEffect(() => {
    if (!enabled) {
      setIsSlowPolling(false)
      return
    }

    const startedAt = Date.now()
    let timeoutId: ReturnType<typeof setTimeout>

    const tick = async () => {
      try {
        await savedCallback.current()
      } catch (err) {
        console.error("useAdaptivePolling error:", err)
      }
      const slow = Date.now() - startedAt >= SLOW_AFTER_MS
      setIsSlowPolling(slow)
      timeoutId = setTimeout(tick, slow ? SLOW_INTERVAL_MS : FAST_INTERVAL_MS)
    }

    // Run immediately, then schedule next tick
    tick()

    return () => clearTimeout(timeoutId)
  }, [enabled])

  return { isSlowPolling }
}
