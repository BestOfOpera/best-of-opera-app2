"use client"

import { useEffect, useRef, useState } from "react"

export function usePolling(callback: () => Promise<void>, intervalMs: number, enabled: boolean) {
  const savedCallback = useRef(callback)
  savedCallback.current = callback

  useEffect(() => {
    if (!enabled) return
    savedCallback.current()
    const id = setInterval(() => savedCallback.current(), intervalMs)
    return () => clearInterval(id)
  }, [intervalMs, enabled])
}

/**
 * Polling com timeout — para de fazer polling após timeoutMs e sinaliza via `timedOut`.
 * Útil para tarefas longas (transcrição, renderização, tradução) onde o backend pode travar.
 */
export function usePollingWithTimeout(
  callback: () => Promise<void>,
  intervalMs: number,
  enabled: boolean,
  timeoutMs: number,
) {
  const savedCallback = useRef(callback)
  savedCallback.current = callback
  const [timedOut, setTimedOut] = useState(false)
  const startRef = useRef<number>(0)

  useEffect(() => {
    if (!enabled) {
      setTimedOut(false)
      return
    }
    startRef.current = Date.now()
    setTimedOut(false)
    savedCallback.current()
    const id = setInterval(() => {
      if (Date.now() - startRef.current > timeoutMs) {
        clearInterval(id)
        setTimedOut(true)
        return
      }
      savedCallback.current()
    }, intervalMs)
    return () => clearInterval(id)
  }, [intervalMs, enabled, timeoutMs])

  return { timedOut }
}
