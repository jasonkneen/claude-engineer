import Link from 'next/link'

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-24">
      <h1 className="text-4xl font-bold mb-8">Claude Engineer</h1>
      <div className="flex gap-4">
        <Link 
          href="/manage" 
          className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
        >
          Manage Agents
        </Link>
        <Link 
          href="/test" 
          className="px-4 py-2 bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/90"
        >
          Connection Test
        </Link>
      </div>
    </div>
  )
}