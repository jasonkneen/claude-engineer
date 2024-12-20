"use client"

import * as React from "react"
import { useState, useEffect, useCallback } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Mic, MicOff } from 'lucide-react'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'

interface Agent {
  id: string
  name: string
  role: string
  tools: string[]
}

interface AgentState {
  name?: string
  role?: string
  tools?: string[]
}

interface WebSocketMessage {
  type: string
  content: any
  timestamp: string
}

interface WebSocketState {
  ws: WebSocket | null
  cleanup: boolean
  reconnectTimeout: NodeJS.Timeout | null
  pingInterval: NodeJS.Timeout | null
}

interface CreateAgentProps extends React.HTMLAttributes<HTMLDivElement> {
  className?: string
}

interface SpeechRecognitionResult {
  readonly length: number
  item(index: number): SpeechRecognitionAlternative
  [index: number]: SpeechRecognitionAlternative
}

interface SpeechRecognitionAlternative {
  readonly transcript: string
  readonly confidence: number
}

interface SpeechRecognitionEvent extends Event {
  readonly resultIndex: number
  readonly results: SpeechRecognitionResultList
}

interface SpeechRecognition extends EventTarget {
  continuous: boolean
  onresult: ((this: SpeechRecognition, ev: SpeechRecognitionEvent) => any) | null
  start(): void
}

interface SpeechRecognitionConstructor {
  new(): SpeechRecognition
  prototype: SpeechRecognition
}

declare global {
  interface Window {
    webkitSpeechRecognition: SpeechRecognitionConstructor
    SpeechRecognition: SpeechRecognitionConstructor
  }
}

export function CreateAgent({ className, ...props }: CreateAgentProps) {
  // State declarations
  const [description, setDescription] = useState<string>('')
  const [isRecording, setIsRecording] = useState<boolean>(false)
  const [isCreating, setIsCreating] = useState<boolean>(false)
  const [existingAgents, setExistingAgents] = useState<Agent[]>([])
  const [activeTab, setActiveTab] = useState<string>('create')
  const [socket, setSocket] = useState<WebSocket | null>(null)
  const [isConnected, setIsConnected] = useState<boolean>(false)
  const [parsedAgent, setParsedAgent] = useState<AgentState>({})
  const [reconnectAttempt, setReconnectAttempt] = useState<number>(0)

  // Constants
  const maxReconnectAttempts = 5

  // Fetch existing agents
  const fetchExistingAgents = useCallback(async () => {
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
  }, [])

  // Initialize WebSocket connection
  useEffect(() => {
    const state: WebSocketState = {
      ws: null,
      cleanup: false,
      reconnectTimeout: null,
      pingInterval: null
    }

    const handleMessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data) as WebSocketMessage
        console.log('Received message:', data)
        
        switch (data.type) {
          case 'ping':
            if (state.ws?.readyState === WebSocket.OPEN) {
              state.ws.send(JSON.stringify({
                type: 'pong',
                content: 'pong',
                timestamp: new Date().toISOString()
              }))
            }
            break
          case 'connected':
            console.log('Connection confirmed by server')
            break
          case 'agent_parsed':
            setParsedAgent(data.content)
            break
          case 'agent_created':
            toast.success('Agent created successfully')
            setDescription('')
            setParsedAgent({})
            void fetchExistingAgents()
            setIsCreating(false)
            break
          case 'error':
            toast.error(data.content)
            setIsCreating(false)
            break
          default:
            console.warn('Unknown message type:', data.type)
        }
      } catch (error) {
        console.error('Error handling message:', error)
        toast.error('Error processing server response')
        setIsCreating(false)
      }
    }

    const resetConnection = () => {
      if (state.ws) {
        state.ws.onclose = null
        state.ws.onerror = null
        state.ws.onmessage = null
        state.ws.close()
      }
      setIsConnected(false)
      setSocket(null)
      setReconnectAttempt(0)
    }

    const handleReconnect = () => {
      if (!state.cleanup) {
        setReconnectAttempt(prev => {
          const nextAttempt = prev + 1
          if (nextAttempt <= maxReconnectAttempts) {
            const delay = Math.min(1000 * Math.pow(2, nextAttempt), 10000)
            console.log(`Reconnecting in ${delay}ms (attempt ${nextAttempt})`)
            if (state.reconnectTimeout) {
              clearTimeout(state.reconnectTimeout)
            }
            state.reconnectTimeout = setTimeout(() => {
              connect()
            }, delay)
            return nextAttempt
          } else {
            console.log('Max reconnection attempts reached')
            toast.error('Failed to connect to server after multiple attempts')
            return prev
          }
        })
      }
    }

    const connect = () => {
      if (state.cleanup || state.ws?.readyState === WebSocket.OPEN) return

      try {
        console.log('Attempting to connect to WebSocket server...')
        // Connect directly to the backend WebSocket server
        const wsUrl = 'ws://localhost:8000/ws'
        console.log(`WebSocket URL: ${wsUrl}`)
        
        state.ws = new WebSocket(wsUrl)
        
        // Set a connection timeout
        const connectionTimeout = setTimeout(() => {
          if (state.ws?.readyState !== WebSocket.OPEN) {
            console.error('WebSocket connection timeout - server might not be running')
            state.ws?.close()
          }
        }, 5000)

        // Set a connection timeout
        const connectionTimeout = setTimeout(() => {
          if (state.ws?.readyState !== WebSocket.OPEN) {
            console.error('WebSocket connection timeout - server might not be running')
            state.ws?.close()
          }
        }, 10000) // Increased timeout to 10 seconds
        
        state.ws.onopen = () => {
          console.log('WebSocket Connected')
          clearTimeout(connectionTimeout)
          
          // Send initial connection message
          try {
            const message = {
              type: 'message',
              content: 'Agent creation client connected',
              timestamp: new Date().toISOString()
            }
            state.ws?.send(JSON.stringify(message))
            console.log('Sent initial message:', message)
            
            setIsConnected(true)
            setSocket(state.ws)
            setReconnectAttempt(0)
          } catch (error) {
            console.error('Error sending initial message:', error)
            state.ws?.close()
          }
        }

        state.ws.onclose = (event) => {
          console.log(`WebSocket Disconnected - Code: ${event.code}, Reason: ${event.reason || 'No reason provided'}`)
          setIsConnected(false)
          setSocket(null)
          
          // Add delay before reconnect to prevent rapid reconnection attempts
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempt), 10000)
          console.log(`Will attempt reconnect in ${delay}ms (attempt ${reconnectAttempt + 1})`)
          
          // Only attempt reconnect if not cleanup
          if (!state.cleanup) {
            setTimeout(() => {
              if (reconnectAttempt < maxReconnectAttempts) {
                handleReconnect()
              } else {
                console.log('Max reconnection attempts reached')
                toast.error('Failed to connect to server after multiple attempts')
              }
            }, delay)
          }
        }

        state.ws.onerror = (error: Event) => {
          console.error('WebSocket error:', error)
          console.log('Current WebSocket state:', state.ws?.readyState)
          console.log('Checking server status at http://localhost:8000/...')
          
          // Try to fetch the server status
          fetch('http://localhost:8000/')
            .then(response => {
              console.log('Server is responding to HTTP requests')
            })
            .catch(err => {
              console.error('Server is not responding to HTTP requests:', err)
            })

          if (state.ws?.readyState === WebSocket.OPEN) {
            state.ws.close()
          }
        }

        state.ws.onmessage = handleMessage
      } catch (error) {
        console.error('Error creating WebSocket:', error)
        handleReconnect()
      }
    }

    connect()

    return () => {
      state.cleanup = true
      if (state.reconnectTimeout) {
        clearTimeout(state.reconnectTimeout)
      }
      if (state.pingInterval) {
        clearInterval(state.pingInterval)
      }
      resetConnection()
    }
  }, [
    fetchExistingAgents,
    maxReconnectAttempts,
    setDescription,
    setIsConnected,
    setIsCreating,
    setParsedAgent,
    setReconnectAttempt,
    setSocket
  ])

  // Handle voice recording
  const toggleRecording = useCallback(async () => {
    if (!isRecording) {
      try {
        await navigator.mediaDevices.getUserMedia({ audio: true })
        const SpeechRecognition = window.webkitSpeechRecognition || window.SpeechRecognition
        if (!SpeechRecognition) {
          throw new Error('Speech recognition is not supported in this browser')
        }
        const recognition = new SpeechRecognition()
        recognition.continuous = true
        recognition.onresult = (event: SpeechRecognitionEvent) => {
          const results = event.results
          const lastResult = results[results.length - 1]
          if (lastResult?.[0]?.transcript) {
            setDescription(prev => prev + ' ' + lastResult[0].transcript)
          }
        }
        recognition.start()
        setIsRecording(true)
      } catch (error) {
        console.error('Error accessing microphone:', error)
        toast.error('Failed to access microphone')
      }
    } else {
      setIsRecording(false)
    }
  }, [isRecording])

  // Handle agent creation
  const handleCreateAgent = useCallback(async () => {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      toast.error('Not connected to server. Please wait for reconnection.')
      return
    }

    if (!description) {
      toast.error('Please provide a description of the agent')
      return
    }

    setIsCreating(true)
    try {
      socket.send(JSON.stringify({
        type: 'message',
        content: description,
        voice: false
      }))
    } catch (error) {
      console.error('Error sending message:', error)
      toast.error(error instanceof Error ? error.message : 'Failed to create agent')
      setIsCreating(false)
    }
  }, [description, socket])

  return (
    <Card className={cn("w-full max-w-2xl mx-auto", className)} {...props}>
      <CardHeader>
        <CardTitle>Create New Agent</CardTitle>
        <CardDescription>Configure your agent with tools and capabilities</CardDescription>
      </CardHeader>

      <CardContent>
        <Tabs defaultValue="create" className="space-y-6">
          <TabsList>
            <TabsTrigger value="create">Create Agent</TabsTrigger>
            <TabsTrigger value="existing">Existing Agents</TabsTrigger>
          </TabsList>

          <TabsContent value="create" className="space-y-6">
            <div className="space-y-6">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label htmlFor="description" className="text-sm font-medium">
                    Describe Your Agent
                  </label>
                  <div className="flex items-center gap-2">
                    <div className="text-sm text-muted-foreground">
                      {isConnected ? (
                        <div className="flex items-center gap-2">
                          <div className="h-2 w-2 rounded-full bg-green-500" />
                          <span className="text-green-500">Connected</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-2">
                          <div className="h-2 w-2 rounded-full bg-red-500 animate-pulse" />
                          <span className="text-red-500">
                            {reconnectAttempt > 0 ? `Reconnecting (${reconnectAttempt})` : 'Disconnected'}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
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
          </TabsContent>

          <TabsContent value="existing">
            <div className="space-y-4">
              {existingAgents.length > 0 ? (
                existingAgents.map((agent) => (
                  <Card key={agent.id}>
                    <CardHeader>
                      <CardTitle>{agent.name}</CardTitle>
                      <CardDescription>{agent.role}</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        <div>
                          <span className="font-medium">Tools:</span>
                          <ul className="list-disc list-inside mt-1">
                            {agent.tools.map((tool) => (
                              <li key={tool}>{tool}</li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))
              ) : (
                <div className="text-center text-muted-foreground">
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