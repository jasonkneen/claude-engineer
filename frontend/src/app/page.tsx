import { ChatLayout } from '@/components/chat/chat-layout'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Chat - Claude Engineer',
  description: 'Chat with your AI assistant',
}

export default function HomePage() {
  return (
    <div className="flex-1">
      <ChatLayout />
    </div>
  )
}