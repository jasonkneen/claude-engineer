"use client"

import React, { useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { SendIcon } from 'lucide-react'

interface ChatInputProps {
  onSubmit: (message: string) => void
  isLoading?: boolean
  className?: string
}

export function ChatInput({ onSubmit, isLoading, className }: ChatInputProps) {
  const [input, setInput] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (input.trim() && !isLoading) {
      onSubmit(input)
      setInput('')
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }

    // Handle markdown shortcuts
    if (e.ctrlKey || e.metaKey) {
      switch (e.key) {
        case 'b':
          e.preventDefault()
          wrapText('**')
          break
        case 'i':
          e.preventDefault()
          wrapText('*')
          break
        case 'k':
          e.preventDefault()
          wrapText('`')
          break
      }
    }
  }

  const wrapText = (wrapper: string) => {
    const textarea = textareaRef.current
    if (!textarea) return

    const start = textarea.selectionStart
    const end = textarea.selectionEnd
    const text = textarea.value

    const beforeSelection = text.substring(0, start)
    const selection = text.substring(start, end)
    const afterSelection = text.substring(end)

    const newText = beforeSelection + wrapper + selection + wrapper + afterSelection
    setInput(newText)

    // Restore cursor position
    setTimeout(() => {
      textarea.selectionStart = start + wrapper.length
      textarea.selectionEnd = end + wrapper.length
      textarea.focus()
    }, 0)
  }

  return (
    <form
      onSubmit={handleSubmit}
      className={cn(
        "flex items-end gap-3 border-t bg-background/95 px-6 py-4 sticky bottom-0 backdrop-blur supports-[backdrop-filter]:bg-background/60 shadow-sm",
        className
      )}
    >
      <textarea
        ref={textareaRef}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Type a message... (Ctrl+B for bold, Ctrl+I for italic, Ctrl+K for code)"
        className="flex-1 resize-none rounded-md border border-input bg-background/50 px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
        rows={1}
        style={{
          height: 'auto',
          minHeight: '2.5rem',
          maxHeight: '10rem',
        }}
      />
      <Button 
        type="submit" 
        size="icon"
        className="transition-colors hover:bg-primary/90 active:scale-95"
        disabled={!input.trim() || isLoading}
      >
        <SendIcon className="h-4 w-4" />
      </Button>
    </form>
  )
}