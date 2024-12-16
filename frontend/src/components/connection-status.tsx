"use client"

import { cn } from "@/lib/utils"
import { useEffect, useState } from "react"

interface ConnectionStatusProps {
  className?: string
}

export function ConnectionStatus({ className }: ConnectionStatusProps) {
  const [isConnected, setIsConnected] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    // Simulate connection check
    const timeout = setTimeout(() => {
      setIsConnected(true)
      setIsLoading(false)
    }, 1000)

    return () => clearTimeout(timeout)
  }, [])

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div
        className={cn(
          "relative flex h-2.5 w-2.5 items-center justify-center rounded-full",
          isLoading && "bg-yellow-500 animate-pulse",
          isConnected && !isLoading && "bg-green-500 after:absolute after:h-full after:w-full after:rounded-full after:bg-green-500/20 after:animate-ping",
          !isConnected && !isLoading && "bg-red-500"
        )}
      />
      <span className="text-sm font-medium text-muted-foreground transition-colors">
        {isLoading
          ? "Connecting..."
          : isConnected
          ? "Connected to API"
          : "Disconnected"}
      </span>
    </div>
  )
}