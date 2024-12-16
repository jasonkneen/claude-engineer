"use client"

import React, { useEffect, useState } from 'react'
import { io, Socket } from 'socket.io-client'
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
  const [socket, setSocket] = useState<Socket | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    const newSocket = io(apiUrl)
    setSocket(newSocket)

    newSocket.on('message', (message: Message) => {
      setMessages(prev => [...prev, message])
      setIsLoading(false)
    })

    newSocket.on('error', (error: string) => {
      console.error('Socket error:', error)
      setIsLoading(false)
    })

    return () => {
      newSocket.close()
    }
  }, [apiUrl])

  const handleSubmit = (content: string) => {
    if (!socket) return

    const newMessage: Message = {
      id: Date.now().toString(),
      content,
      role: 'user',
      timestamp: new Date().toISOString()
    }

    setMessages(prev => [...prev, newMessage])
    setIsLoading(true)
    socket.emit('message', content)
  }

  return (
    <div className={cn("flex flex-col h-screen", className)} {...props}>
      <div className="flex-1 overflow-hidden">
        <ChatContainer messages={messages} />
      </div>
      <ChatInput onSubmit={handleSubmit} isLoading={isLoading} />
    </div>
  )
}