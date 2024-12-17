import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Checkbox } from '@/components/ui/checkbox'

interface Tool {
  name: string
  description: string
  input_schema: Record<string, any>
}

export function ToolList({ onToolSelect }: { onToolSelect: (tools: string[]) => void }) {
  const [tools, setTools] = useState<Tool[]>([])
  const [selectedTools, setSelectedTools] = useState<string[]>([])
  const [error, setError] = useState<string>('')

  useEffect(() => {
    const fetchTools = async () => {
      try {
        const response = await fetch('http://localhost:8000/tools')
        if (!response.ok) throw new Error('Failed to fetch tools')
        const data = await response.json()
        setTools(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load tools')
      }
    }

    fetchTools()
  }, [])

  const handleToolToggle = (toolName: string) => {
    setSelectedTools(prev => {
      const newSelection = prev.includes(toolName)
        ? prev.filter(t => t !== toolName)
        : [...prev, toolName]
      onToolSelect(newSelection)
      return newSelection
    })
  }

  if (error) {
    return <div className="text-red-500">Error: {error}</div>
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Available Tools</CardTitle>
        <CardDescription>Select tools for your agent</CardDescription>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[300px] pr-4">
          <div className="space-y-4">
            {tools.map((tool) => (
              <div key={tool.name} className="flex items-start space-x-3 p-2 hover:bg-accent rounded-lg">
                <Checkbox
                  id={tool.name}
                  checked={selectedTools.includes(tool.name)}
                  onCheckedChange={() => handleToolToggle(tool.name)}
                />
                <div>
                  <label
                    htmlFor={tool.name}
                    className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                  >
                    {tool.name}
                  </label>
                  <p className="text-sm text-muted-foreground">{tool.description}</p>
                </div>
              </div>
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}