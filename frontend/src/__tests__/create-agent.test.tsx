import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { CreateAgent } from '../components/tool-management/create-agent'
import { vi } from 'vitest'

// Mock WebSocket
class MockWebSocket {
  onopen: ((this: WebSocket, ev: Event) => any) | null = null
  onclose: ((this: WebSocket, ev: CloseEvent) => any) | null = null
  onmessage: ((this: WebSocket, ev: MessageEvent) => any) | null = null
  onerror: ((this: WebSocket, ev: Event) => any) | null = null
  readyState: number = WebSocket.CONNECTING
  send = vi.fn()
  close = vi.fn()
}

// Mock window.WebSocket
const mockWebSocket = MockWebSocket as any
global.WebSocket = mockWebSocket

describe('CreateAgent', () => {
  let ws: MockWebSocket

  beforeEach(() => {
    ws = new MockWebSocket()
    vi.spyOn(global, 'WebSocket').mockImplementation(() => ws)
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('establishes WebSocket connection on mount', async () => {
    render(<CreateAgent />)
    
    // Simulate successful connection
    if (ws.onopen) {
      ws.onopen(new Event('open'))
    }

    // Verify initial message is sent
    expect(ws.send).toHaveBeenCalledWith(
      expect.stringContaining('Agent creation client connected')
    )
  })

  it('handles WebSocket connection errors', async () => {
    render(<CreateAgent />)
    
    // Simulate connection error
    if (ws.onerror) {
      ws.onerror(new Event('error'))
    }

    // Verify error state
    expect(screen.getByText(/Disconnected/i)).toBeInTheDocument()
  })

  it('creates agent successfully', async () => {
    render(<CreateAgent />)
    
    // Simulate successful connection
    if (ws.onopen) {
      ws.onopen(new Event('open'))
    }

    // Fill in description
    const textarea = screen.getByPlaceholderText(/Describe what you want your agent to do/i)
    fireEvent.change(textarea, { target: { value: 'Create a test agent' } })

    // Click create button
    const createButton = screen.getByText(/Create Agent/i)
    fireEvent.click(createButton)

    // Verify message is sent
    expect(ws.send).toHaveBeenCalledWith(
      expect.stringContaining('Create a test agent')
    )

    // Simulate successful response
    if (ws.onmessage) {
      ws.onmessage(new MessageEvent('message', {
        data: JSON.stringify({
          type: 'agent_created',
          content: {
            id: '123',
            name: 'Test Agent',
            role: 'test',
            tools: ['test_runner']
          }
        })
      }))
    }

    // Verify success state
    await waitFor(() => {
      expect(screen.getByText(/Agent created successfully/i)).toBeInTheDocument()
    })
  })

  it('handles agent creation errors', async () => {
    render(<CreateAgent />)
    
    // Simulate successful connection
    if (ws.onopen) {
      ws.onopen(new Event('open'))
    }

    // Fill in description
    const textarea = screen.getByPlaceholderText(/Describe what you want your agent to do/i)
    fireEvent.change(textarea, { target: { value: 'Create a test agent' } })

    // Click create button
    const createButton = screen.getByText(/Create Agent/i)
    fireEvent.click(createButton)

    // Simulate error response
    if (ws.onmessage) {
      ws.onmessage(new MessageEvent('message', {
        data: JSON.stringify({
          type: 'error',
          content: 'Failed to create agent'
        })
      }))
    }

    // Verify error state
    await waitFor(() => {
      expect(screen.getByText(/Failed to create agent/i)).toBeInTheDocument()
    })
  })
})