import { useState, useEffect } from 'react';
import type { StatsMessage, LogMessage, WebSocketMessage } from '../types/memory';

export type { LogMessage, StatsMessage, WebSocketMessage };

const WS_PORTS = [8000, 8001, 8002, 8003, 8004, 8005];

export function useMemoryStats() {
    const [stats, setStats] = useState<StatsMessage>({
        pools: {
            working: {
                size: 0,
                count: 0,
                limit: 8192,
                utilization: 0
            },
            short_term: {
                size: 0,
                count: 0,
                limit: 128000,
                utilization: 0
            },
            long_term: {
                size: 0,
                count: 0
            }
        },
        operations: {
            promotions: 0,
            demotions: 0,
            merges: 0,
            retrievals: 0,
            avg_recall_time: 0,
            compression_count: 0
        },
        nexus_points: {
            count: 0,
            types: {
                user: 0,
                llm: 0,
                system: 0
            }
        },
        generations: 0,
        total_tokens: 0
    });

    const [logs, setLogs] = useState<LogMessage[]>([]);
    const [connected, setConnected] = useState(false);

    useEffect(() => {
        let ws: WebSocket | null = null;
        let reconnectTimeout: NodeJS.Timeout;
        let reconnectAttempts = 0;
        const maxReconnectAttempts = 5;
        let currentPortIndex = 0;

        const tryNextPort = async () => {
            try {
                // Try to read the port from the .ws-port file first
                const response = await fetch('/.ws-port');
                if (response.ok) {
                    const port = await response.text();
                    return parseInt(port, 10);
                }
            } catch {
                // Ignore error and try default ports
            }

            // Try the next port from our list
            const port = WS_PORTS[currentPortIndex];
            currentPortIndex = (currentPortIndex + 1) % WS_PORTS.length;
            return port;
        };

        const connect = async () => {
            if (reconnectAttempts >= maxReconnectAttempts) {
                console.error('Max reconnection attempts reached');
                return;
            }

            try {
                const port = await tryNextPort();
                if (!port) {
                    throw new Error('No available ports');
                }

                ws = new WebSocket(`ws://localhost:${port}`);

                ws.onopen = () => {
                    console.log('Connected to memory stats service');
                    setConnected(true);
                    reconnectAttempts = 0;
                };

                ws.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data) as WebSocketMessage;
                        if (data.type === 'stats') {
                            setStats(data.payload as StatsMessage);
                        } else if (data.type === 'log') {
                            setLogs(prev => [...prev, data.payload as LogMessage]);
                        }
                    } catch (error) {
                        console.error('Error parsing message:', error);
                    }
                };

                ws.onclose = () => {
                    console.log('Connection closed, attempting to reconnect...');
                    setConnected(false);
                    ws = null;

                    // Try to reconnect with exponential backoff
                    const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
                    reconnectTimeout = setTimeout(() => {
                        reconnectAttempts++;
                        connect();
                    }, delay);
                };

                ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    ws?.close();
                };

            } catch (error) {
                console.error('Failed to connect:', error);
                const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
                reconnectTimeout = setTimeout(() => {
                    reconnectAttempts++;
                    connect();
                }, delay);
            }
        };

        connect();

        return () => {
            clearTimeout(reconnectTimeout);
            if (ws) {
                ws.close();
            }
        };
    }, []);

    return { stats, logs, connected };
}