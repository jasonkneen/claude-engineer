import { ChatLayout } from '@/components/chat/chat-layout'
import { ThemeToggle } from '@/components/theme-toggle'

export const metadata = {
  title: 'Claude Engineer',
  description: 'A self-improving assistant framework with tool creation',
}

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col bg-background">
      <div className="flex h-16 items-center border-b px-4">
        <h1 className="text-xl font-semibold">Claude Engineer</h1>
        <div className="ml-auto flex items-center space-x-4">
          <span className="text-sm text-muted-foreground">
            Connected to API
          </span>
          <ThemeToggle />
        </div>
      </div>
      <div className="flex-1">
        <ChatLayout />
      </div>
    </main>
  )
}