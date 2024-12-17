"use client"

import React, { useState, useEffect, useRef, useCallback } from 'react'
import { ChatContainer } from './chat-container'
import { ChatInput } from './chat-input'
import { cn } from '@/lib/utils'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'

interface Message {
  id: string
  content: string
  role: 'user' | 'assistant'
  timestamp: string
  audio?: string
}

interface WebSocketMessage {
  type: string
  content: string
  role: string
  timestamp: string
  id: string
  audio?: string
}

interface ChatLayoutProps extends React.HTMLAttributes<HTMLDivElement> {
  apiUrl?: string
  initialMessages?: Message[]
}

export function ChatLayout({ 
  apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  initialMessages = [],
  className,
  ...props 
}: ChatLayoutProps) {
  const [messages, setMessages] = useState<Message[]>(initialMessages)
  const [isLoading, setIsLoading] = useState(false)
  const [isVoiceEnabled, setIsVoiceEnabled] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>()

  const connectWebSocket = useCallback(() => {
    const wsUrl = apiUrl.replace('http', 'ws') + '/ws'
    const ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      console.log('WebSocket connected')
    }

    ws.onmessage = (event) => {
      const data: WebSocketMessage = JSON.parse(event.data)
      setMessages(prev => [...prev, {
        id: data.id,
        content: data.content,
        role: data.role as 'user' | 'assistant',
        timestamp: data.timestamp,
        audio: data.audio
      }])
      setIsLoading(false)

      // Play audio if voice is enabled and audio data is present
      if (isVoiceEnabled && data.audio) {
        const audio = new Audio(`data:audio/wav;base64,${data.audio}`)
        audio.play()
      }
    }

    ws.onclose = () => {
      console.log('WebSocket disconnected. Reconnecting...')
      reconnectTimeoutRef.current = setTimeout(connectWebSocket, 3000)
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      ws.close()
    }

    wsRef.current = ws
  }, [apiUrl, isVoiceEnabled])

  useEffect(() => {
    connectWebSocket()
    return () => {
      wsRef.current?.close()
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
    }
  }, [connectWebSocket])

  const handleSubmit = async (content: string) => {
    if (!content.trim() || !wsRef.current) {
      return
    }

    const newMessage: Message = {
      id: Date.now().toString(),
      content,
      role: 'user',
      timestamp: new Date().toISOString()
    }

    setMessages(prev => [...prev, newMessage])
    setIsLoading(true)

    // Send message through WebSocket
    wsRef.current.send(JSON.stringify({
      content: content.trim(),
      voice: isVoiceEnabled
    }))
  }

  return (
    <div 
      className={cn(
        "flex flex-col h-screen transition-colors duration-150",
        className
      )} 
      {...props}
    >
      <div className="flex items-center justify-end gap-2 p-4 border-b">
        <Label htmlFor="voice-mode">Voice Mode</Label>
        <Switch
          id="voice-mode"
          checked={isVoiceEnabled}
          onCheckedChange={setIsVoiceEnabled}
        />
      </div>
      <div className="flex-1 overflow-hidden">
        <ChatContainer messages={messages} />
      </div>
      <ChatInput 
        onSubmit={handleSubmit} 
        isLoading={isLoading} 
        className="transition-all duration-150"
      />
      {isLoading && (
        <div className="absolute bottom-24 left-1/2 transform -translate-x-1/2">
          <div className="bg-primary/10 dark:bg-primary/5 text-primary dark:text-primary/90 px-4 py-2 rounded-full text-sm font-medium animate-pulse">
            Claude is thinking...
          </div>
        </div>
      )}
    </div>
  )
}