"use client"

import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { ScrollArea } from '../ui/scroll-area'
import { Checkbox } from '../ui/checkbox'
import { Badge } from '../ui/badge'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../ui/tooltip'
import { StarIcon } from 'lucide-react'

type CategoryInfo = {
  label: string
  description: string
}

type ToolCategories = {
  [key in 'agent' | 'context' | 'file' | 'web' | 'voice' | 'test' | 'other']: CategoryInfo
}

interface Tool {
  name: string
  description: string
  input_schema: Record<string, any>
  category?: string
}

const TOOL_CATEGORIES: ToolCategories = {
  'agent': { label: 'Agent Management', description: 'Tools for managing and controlling agents' },
  'context': { label: 'Context Management', description: 'Tools for handling context and state' },
  'file': { label: 'File Operations', description: 'Tools for file system operations' },
  'web': { label: 'Web Tools', description: 'Tools for web interactions and scraping' },
  'voice': { label: 'Voice & Audio', description: 'Tools for voice and audio processing' },
  'test': { label: 'Testing', description: 'Tools for testing and validation' },
  'other': { label: 'Other Tools', description: 'Additional utility tools' }
} as const

type CategoryKey = keyof typeof TOOL_CATEGORIES;

function getToolCategory(toolName: string): CategoryKey {
  if (toolName.includes('agent')) return 'agent'
  if (toolName.includes('context')) return 'context'
  if (toolName.includes('file')) return 'file'
  if (toolName.includes('web') || toolName.includes('browser')) return 'web'
  if (toolName.includes('voice') || toolName.includes('audio')) return 'voice'
  if (toolName.includes('test')) return 'test'
  return 'other'
}

export function ToolList({ 
  onToolSelect,
  recommendedTools = []
}: { 
  onToolSelect: (tools: string[]) => void
  recommendedTools?: string[]
}) {
  const [tools, setTools] = useState<Tool[]>([])
  const [selectedTools, setSelectedTools] = useState<string[]>([])
  const [error, setError] = useState<string>('')

  useEffect(() => {
    const fetchTools = async () => {
      try {
        const response = await fetch('http://localhost:8000/tools')
        if (!response.ok) throw new Error('Failed to fetch tools')
        const data = await response.json()
        
        // Group tools by category
        const toolsWithCategories = data.map((tool: Tool) => ({
          ...tool,
          category: getToolCategory(tool.name)
        }))
        
        setTools(toolsWithCategories)
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
        <ScrollArea className="h-[400px] pr-4">
          <div className="space-y-6">
            {Object.entries(TOOL_CATEGORIES).map(([category, label]) => {
              const categoryTools = tools.filter(tool => tool.category === category)
              if (categoryTools.length === 0) return null

              return (
                <div key={category} className="space-y-3">
                  <div className="space-y-1">
                    <h3 className="font-medium text-sm">{TOOL_CATEGORIES[category].label}</h3>
                    <p className="text-sm text-muted-foreground">{TOOL_CATEGORIES[category].description}</p>
                  </div>
                  <div className="space-y-2">
                    {categoryTools.map((tool) => (
                      <TooltipProvider key={tool.name}>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <div className="flex items-start space-x-3 p-3 hover:bg-accent rounded-lg border">
                              <Checkbox
                                id={tool.name}
                                checked={selectedTools.includes(tool.name)}
                                onCheckedChange={() => handleToolToggle(tool.name)}
                              />
                              <div className="flex-1">
                                <div className="flex items-center gap-2">
                                  <label
                                    htmlFor={tool.name}
                                    className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                                  >
                                    {tool.name}
                                  </label>
                                  {recommendedTools.includes(tool.name) && (
                                    <Badge variant="secondary" className="text-xs">
                                      <StarIcon className="h-3 w-3 mr-1" />
                                      Recommended
                                    </Badge>
                                  )}
                                </div>
                                <p className="text-sm text-muted-foreground mt-1">{tool.description}</p>
                              </div>
                            </div>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p className="text-sm">{tool.description}</p>
                            {recommendedTools.includes(tool.name) && (
                              <p className="text-sm text-primary mt-1">Recommended for selected role</p>
                            )}
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}