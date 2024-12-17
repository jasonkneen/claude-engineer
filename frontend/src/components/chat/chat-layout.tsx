"use client"

import React, { useState } from 'react'
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
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (content: string) => {
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
      const response = await fetch(`${apiUrl}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content: content.trim() })
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        content: data.content,
        role: data.role,
        timestamp: data.timestamp
      }])
    } catch (error) {
      console.error('Error sending message:', error)
      // Optionally add error message to chat
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        content: 'An error occurred while sending your message. Please try again.',
        role: 'assistant',
        timestamp: new Date().toISOString()
      }])
    } finally {
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
      />
    </div>
  )
}