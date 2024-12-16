"use client"

import React, { useEffect, useRef } from 'react'
import { cn } from '@/lib/utils'

interface ChatContainerProps extends React.HTMLAttributes<HTMLDivElement> {
  messages: {
    id: string
    content: string
    role: 'user' | 'assistant'
    timestamp?: string
  }[]
  className?: string
}

export function ChatContainer({ messages, className, ...props }: ChatContainerProps) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight
    }
  }, [messages])

  return (
    <div
      ref={containerRef}
      className={cn(
        "flex flex-col gap-6 overflow-y-auto p-4 h-[calc(100vh-12rem)] bg-muted/10",
        className
      )}
      {...props}
    >
      {messages.map((message) => (
        <div
          key={message.id}
          className={cn(
            "flex w-full",
            message.role === "user" ? "justify-end" : "justify-start"
          )}
        >
          <div
            className={cn(
              "rounded-lg px-4 py-3 max-w-[80%] shadow-sm",
              message.role === "user"
                ? "bg-primary text-primary-foreground ml-auto"
                : "bg-card border"
            )}
          >
            <div className="prose dark:prose-invert prose-sm max-w-none">
              {message.content}
            </div>
            {message.timestamp && (
              <div className="text-xs opacity-50 mt-1">
                {message.timestamp}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}