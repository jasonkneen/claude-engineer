"use client"

import * as React from "react"
import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ToolList } from './tool-list'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'

const AGENT_ROLES = [
  { 
    value: 'test', 
    label: 'Test Agent',
    description: 'Agent for testing and validation',
    recommendedTools: ['agent_test_testagenttool_3']
  },
  { 
    value: 'context', 
    label: 'Context Manager',
    description: 'Manages context and knowledge base',
    recommendedTools: ['context_manager', 'file_reader']
  },
  { 
    value: 'orchestrator', 
    label: 'Orchestrator',
    description: 'Coordinates multiple agents and workflows',
    recommendedTools: ['agent_manager', 'context_manager']
  },
  { 
    value: 'custom', 
    label: 'Custom Agent',
    description: 'Create a custom agent with selected tools',
    recommendedTools: []
  },
]

interface Agent {
  id: string
  name: string
  role: string
  tools: string[]
}

interface CreateAgentProps {
  className?: string
}

export function CreateAgent({ className }: CreateAgentProps) {
  const [name, setName] = useState('')
  const [role, setRole] = useState('')
  const [selectedTools, setSelectedTools] = useState<string[]>([])
  const [isCreating, setIsCreating] = useState(false)
  const [existingAgents, setExistingAgents] = useState<Agent[]>([])
  const [activeTab, setActiveTab] = useState('create')

  useEffect(() => {
    fetchExistingAgents()
  }, [])

  useEffect(() => {
    if (role) {
      const selectedRole = AGENT_ROLES.find(r => r.value === role)
      if (selectedRole && selectedRole.recommendedTools.length > 0) {
        setSelectedTools(selectedRole.recommendedTools)
      }
    }
  }, [role])

  const fetchExistingAgents = async () => {
    try {
      const response = await fetch('http://localhost:8000/agents')
      if (!response.ok) throw new Error('Failed to fetch agents')
      const data = await response.json()
      // Ensure data is an array
      setExistingAgents(Array.isArray(data) ? data : [])
    } catch (error) {
      console.error('Error fetching agents:', error)
      toast.error('Failed to load existing agents')
      setExistingAgents([])
    }
  }

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
        <CardTitle>Agent Management</CardTitle>
        <CardDescription>Create and manage your AI agents</CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="create">Create Agent</TabsTrigger>
            <TabsTrigger value="existing">Existing Agents</TabsTrigger>
          </TabsList>

          <TabsContent value="create">
            <div className="space-y-6">
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

              <ToolList 
                onToolSelect={setSelectedTools} 
                recommendedTools={role ? AGENT_ROLES.find(r => r.value === role)?.recommendedTools || [] : []}
              />
            </div>
            <div className="mt-6">
              <Button 
                className="w-full" 
                onClick={handleCreateAgent} 
                disabled={isCreating || !name || !role || selectedTools.length === 0}
              >
                {isCreating ? 'Creating...' : 'Create Agent'}
              </Button>
            </div>
          </TabsContent>

          <TabsContent value="existing">
            <div className="space-y-4">
              {existingAgents.length > 0 ? existingAgents.map((agent) => (
                <Card key={agent.id || agent.name}>
                  <CardHeader>
                    <CardTitle className="text-lg">{agent.name}</CardTitle>
                    <CardDescription>
                      Role: {AGENT_ROLES.find(r => r.value === agent.role)?.label || agent.role}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="text-sm text-muted-foreground">
                      <div>Tools:</div>
                      <ul className="list-disc list-inside mt-1">
                        {agent.tools.map((tool) => (
                          <li key={tool}>{tool}</li>
                        ))}
                      </ul>
                    </div>
                  </CardContent>
                </Card>
              ))}
              {existingAgents.length === 0 && (
                <div className="text-center text-muted-foreground py-8">
                  No agents created yet
                </div>
              )}
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}