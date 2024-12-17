import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { ToolList } from './tool-list'
import { toast } from 'sonner'

const AGENT_ROLES = [
  { value: 'test', label: 'Test Agent' },
  { value: 'context', label: 'Context Manager' },
  { value: 'orchestrator', label: 'Orchestrator' },
  { value: 'custom', label: 'Custom Agent' },
]

export function CreateAgent() {
  const [name, setName] = useState('')
  const [role, setRole] = useState('')
  const [selectedTools, setSelectedTools] = useState<string[]>([])
  const [isCreating, setIsCreating] = useState(false)

  const handleCreateAgent = async () => {
    if (!name || !role || selectedTools.length === 0) {
      toast.error('Please fill in all fields and select at least one tool')
      return
    }

    setIsCreating(true)
    try {
      const response = await fetch('http://localhost:8000/agents', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name,
          role,
          tools: selectedTools,
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to create agent')
      }

      const data = await response.json()
      toast.success(`Agent created successfully with ID: ${data.agent_id}`)
      
      // Reset form
      setName('')
      setRole('')
      setSelectedTools([])
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to create agent')
    } finally {
      setIsCreating(false)
    }
  }

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle>Create New Agent</CardTitle>
        <CardDescription>Configure your agent with tools and capabilities</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-2">
          <label htmlFor="name" className="text-sm font-medium">
            Agent Name
          </label>
          <Input
            id="name"
            placeholder="Enter agent name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>
        
        <div className="space-y-2">
          <label className="text-sm font-medium">
            Agent Role
          </label>
          <Select value={role} onValueChange={setRole}>
            <SelectTrigger>
              <SelectValue placeholder="Select a role" />
            </SelectTrigger>
            <SelectContent>
              {AGENT_ROLES.map((role) => (
                <SelectItem key={role.value} value={role.value}>
                  {role.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <ToolList onToolSelect={setSelectedTools} />
      </CardContent>
      <CardFooter>
        <Button 
          className="w-full" 
          onClick={handleCreateAgent} 
          disabled={isCreating || !name || !role || selectedTools.length === 0}
        >
          {isCreating ? 'Creating...' : 'Create Agent'}
        </Button>
      </CardFooter>
    </Card>
  )
}