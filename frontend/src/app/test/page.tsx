'use client'

import { useEffect, useState } from 'react'

export default function TestPage() {
  const [status, setStatus] = useState<string>('Checking connection...')
  const [wsStatus, setWsStatus] = useState<string>('Initializing WebSocket...')

  useEffect(() => {
    // Test HTTP connection
    fetch('http://localhost:8000/health')
      .then(res => res.json())
      .then(data => {
        setStatus(`Backend is running: ${JSON.stringify(data)}`)
      })
      .catch(err => {
        setStatus(`Error connecting to backend: ${err.message}`)
      })

    // Test WebSocket connection
    const ws = new WebSocket('ws://localhost:8000/ws')
    
    ws.onopen = () => {
      setWsStatus('WebSocket Connected')
      ws.send(JSON.stringify({
        type: 'message',
        content: 'Test connection',
        timestamp: new Date().toISOString()
      }))
    }

    ws.onclose = () => {
      setWsStatus('WebSocket Disconnected')
    }

    ws.onerror = (error) => {
      setWsStatus(`WebSocket Error: ${error.toString()}`)
    }

    return () => {
      ws.close()
    }
  }, [])

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">Connection Test</h1>
      <div className="space-y-4">
        <div>
          <h2 className="text-lg font-semibold">HTTP Status:</h2>
          <p className="mt-2">{status}</p>
        </div>
        <div>
          <h2 className="text-lg font-semibold">WebSocket Status:</h2>
          <p className="mt-2">{wsStatus}</p>
        </div>
      </div>
    </div>
  )
}