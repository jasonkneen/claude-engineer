"use client"

import React, { useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { SendIcon } from 'lucide-react'

interface ChatInputProps extends React.HTMLAttributes<HTMLDivElement> {
  onSubmit: (message: string) => void
  isLoading?: boolean
}

export function ChatInput({ onSubmit, isLoading, className, ...props }: ChatInputProps) {
  const [input, setInput] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSubmit = (e: React.FormEvent) => {
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
        "flex items-end gap-2 border-t bg-background p-4",
        className
      )}
      {...props}
    >
      <textarea
        ref={textareaRef}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Type a message... (Ctrl+B for bold, Ctrl+I for italic, Ctrl+K for code)"
        className="flex-1 resize-none bg-background p-2 focus:outline-none"
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
        disabled={!input.trim() || isLoading}
      >
        <SendIcon className="h-4 w-4" />
      </Button>
    </form>
  )
}