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
          "h-2 w-2 rounded-full",
          isLoading && "bg-yellow-500",
          isConnected && !isLoading && "bg-green-500",
          !isConnected && !isLoading && "bg-red-500"
        )}
      />
      <span className="text-sm text-muted-foreground">
        {isLoading
          ? "Connecting..."
          : isConnected
          ? "Connected to API"
          : "Disconnected"}
      </span>
    </div>
  )
}