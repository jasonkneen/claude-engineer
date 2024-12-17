"use client"

import React, { useEffect, useState } from 'react'
import { ChatContainer } from './chat-container'
import { ChatInput } from './chat-input'
import { cn } from '@/lib/utils'

interface Message {
  id: string
  content: string
  role: 'user' | 'assistant'
  timestamp: string
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
  const [socket, setSocket] = useState<WebSocket | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isConnected, setIsConnected] = useState(false)

  useEffect(() => {
    let reconnectTimer: NodeJS.Timeout;
    
    const connectWebSocket = () => {
      try {
        const ws = new WebSocket('ws://localhost:8085/ws', [], {
          headers: {
            'Origin': 'http://localhost:3000'
          }
        })
        setSocket(ws)

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            if (data.type === 'message') {
              setMessages(prev => [...prev, {
                id: Date.now().toString(),
                content: data.content,
                role: data.role,
                timestamp: new Date().toISOString()
              }])
              setIsLoading(false)
            }
          } catch (error) {
            console.error('Error parsing message:', error)
            setIsLoading(false)
          }
        }

        ws.onerror = (error) => {
          console.error('WebSocket error:', error)
          setIsLoading(false)
          setIsConnected(false)
        }

        ws.onclose = () => {
          console.log('WebSocket connection closed, attempting to reconnect...')
          setIsConnected(false)
          reconnectTimer = setTimeout(connectWebSocket, 3000)
        }

        ws.onopen = () => {
          console.log('WebSocket connection established')
          setIsConnected(true)
        }
      } catch (error) {
        console.error('Error creating WebSocket:', error)
        setIsConnected(false)
        reconnectTimer = setTimeout(connectWebSocket, 3000)
      }
    }

    connectWebSocket()

    return () => {
      if (socket) {
        socket.close()
      }
      if (reconnectTimer) {
        clearTimeout(reconnectTimer)
      }
    }
  }, [])

  const handleSubmit = (content: string) => {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      console.error('WebSocket is not connected')
      return
    }

    if (!content.trim()) {
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
    
    try {
      socket.send(JSON.stringify({ content: content.trim() }))
    } catch (error) {
      console.error('Error sending message:', error)
      setIsLoading(false)
    }
  }

  return (
    <div className={cn("flex flex-col h-screen", className)} {...props}>
      <div className="flex-1 overflow-hidden">
        <ChatContainer messages={messages} />
      </div>
      <ChatInput 
        onSubmit={handleSubmit} 
        isLoading={isLoading} 
        disabled={!isConnected}
      />
    </div>
  )
}