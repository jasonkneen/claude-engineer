"use client"

import * as React from "react"
import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

// Type declarations
declare global {
  interface Window {
    webkitSpeechRecognition: any;
    SpeechRecognition: any;
  }
}

interface SpeechRecognitionResult {
  readonly length: number;
  [index: number]: {
    readonly transcript: string;
    readonly confidence: number;
  };
}

interface SpeechRecognitionEvent {
  readonly resultIndex: number;
  readonly results: {
    readonly length: number;
    [index: number]: SpeechRecognitionResult;
  };
}
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ToolList } from './tool-list'
import { Mic, MicOff } from 'lucide-react'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'

type AgentRole = {
  value: string
  label: string
  description: string
  recommendedTools: string[]
}

const AGENT_ROLES: AgentRole[] = [
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

interface CreateAgentProps extends React.HTMLAttributes<HTMLDivElement> {
  className?: string
}

export function CreateAgent({ className, ...props }: CreateAgentProps): JSX.Element {
  const [description, setDescription] = useState<string>('')
  const [isRecording, setIsRecording] = useState<boolean>(false)
  const [isCreating, setIsCreating] = useState<boolean>(false)
  const [existingAgents, setExistingAgents] = useState<Agent[]>([])
  const [activeTab, setActiveTab] = useState<string>('create')
  const [parsedAgent, setParsedAgent] = useState<{
    name?: string;
    role?: string;
    tools?: string[];
  }>({})

  useEffect(() => {
    void fetchExistingAgents()
  }, [])

  useEffect(() => {
    if (description) {
      void parseAgentDescription(description)
    }
  }, [description])

  const parseAgentDescription = async (text: string): Promise<void> => {
    try {
      const response = await fetch('http://localhost:8000/parse-agent', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ description: text }),
      })

      if (!response.ok) throw new Error('Failed to parse agent description')
      const data = await response.json()
      setParsedAgent(data)
    } catch (error) {
      console.error('Error parsing agent description:', error)
      toast.error('Failed to parse agent description')
    }
  }

  const toggleRecording = async () => {
    if (!isRecording) {
      try {
        await navigator.mediaDevices.getUserMedia({ audio: true })
        // Initialize voice recognition
        const SpeechRecognition = window.webkitSpeechRecognition || window.SpeechRecognition
        if (!SpeechRecognition) {
          throw new Error('Speech recognition is not supported in this browser')
        }
        const recognition = new SpeechRecognition()
        recognition.continuous = true
        recognition.onresult = (event: SpeechRecognitionEvent) => {
          const results = event.results;
          const lastResult = results[results.length - 1];
          if (lastResult?.[0]?.transcript) {
            setDescription(prev => prev + ' ' + lastResult[0].transcript);
          }
        }
        recognition.start()
        setIsRecording(true)
      } catch (error) {
        console.error('Error accessing microphone:', error)
        toast.error('Failed to access microphone')
      }
    } else {
      // Stop recording
      setIsRecording(false)
    }
  }

  const fetchExistingAgents = async (): Promise<void> => {
    try {
      const response = await fetch('http://localhost:8000/agents')
      if (!response.ok) throw new Error('Failed to fetch agents')
      const data = await response.json()
      setExistingAgents(Array.isArray(data) ? data : [])
    } catch (error) {
      console.error('Error fetching agents:', error)
      toast.error('Failed to load existing agents')
      setExistingAgents([])
    }
  }

  const handleCreateAgent = async (): Promise<void> => {
    if (!description) {
      toast.error('Please provide a description of the agent');
      return;
    }

    setIsCreating(true);
    try {
      // First parse the description
      const parseResponse = await fetch('http://localhost:8000/parse-agent', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ description })
      }).catch(error => {
        throw new Error(`Network error: ${error.message}`);
      });

      if (!parseResponse.ok) {
        const errorData = await parseResponse.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to parse agent description');
      }

      const parsedData = await parseResponse.json();
      setParsedAgent(parsedData);

      // Then create the agent
      const response = await fetch('http://localhost:8000/agents', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          description,
          ...parsedData
        })
      }).catch(error => {
        throw new Error(`Network error: ${error.message}`);
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to create agent');
      }

      const data = await response.json();
      toast.success(`Agent created successfully with ID: ${data.agent_id}`);
      
      // Reset form state
      setDescription('');
      setParsedAgent({});
      void fetchExistingAgents();
          ...parsedData
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to create agent')
      }

      const data = await response.json()
      toast.success(`Agent created successfully with ID: ${data.agent_id}`)
      
      setDescription('')
      setParsedAgent({})
      void fetchExistingAgents()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to create agent')
    } finally {
      setIsCreating(false)
    }
  }

  return (
    <Card className={cn("w-full max-w-2xl mx-auto", className)} {...props}>
      <CardHeader>
        <CardTitle>Create New Agent</CardTitle>
        <CardDescription>Configure your agent with tools and capabilities</CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="create">Create Agent</TabsTrigger>
            <TabsTrigger value="existing">Existing Agents</TabsTrigger>
          </TabsList>

          <TabsContent value="create" className="space-y-6">
            <div className="space-y-6">
              <div className="space-y-2">
                <label htmlFor="description" className="text-sm font-medium">
                  Describe Your Agent
                </label>
                <div className="flex gap-2">
                  <Textarea
                    id="description"
                    placeholder="Describe what you want your agent to do... (e.g., 'Create a test agent that can validate API endpoints')"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    className="min-h-[100px]"
                  />
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={toggleRecording}
                    className="flex-shrink-0"
                  >
                    {isRecording ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
                  </Button>
                </div>
              </div>

              {parsedAgent.name && (
                <div className="space-y-4 p-4 bg-muted rounded-lg">
                  <div>
                    <span className="font-medium">Name:</span> {parsedAgent.name}
                  </div>
                  <div>
                    <span className="font-medium">Role:</span> {parsedAgent.role}
                  </div>
                  {parsedAgent.tools && parsedAgent.tools.length > 0 && (
                    <div>
                      <span className="font-medium">Selected Tools:</span>
                      <ul className="list-disc list-inside mt-1">
                        {parsedAgent.tools.map((tool) => (
                          <li key={tool}>{tool}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
            <div className="mt-6">
              <div className="space-y-4">
                {parsedAgent.name && (
                  <div className="text-sm text-muted-foreground">
                    Parsed agent details will appear here...
                  </div>
                )}
                <Button 
                  className="w-full" 
                  onClick={handleCreateAgent} 
                  disabled={isCreating || !description}
                >
                  {isCreating ? (
                    <div className="flex items-center gap-2">
                      <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                      Creating...
                    </div>
                  ) : (
                    'Create Agent'
                  )}
                </Button>
              </div>
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
              )) : (
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