#!/usr/bin/env node
import { WebSocketServer, WebSocket } from 'ws';
import { createServer } from 'net';

const WS_CONFIG = {
    pingInterval: 10000,  // 10 seconds
    pingTimeout: 5000,    // 5 seconds
    startPort: 8000,
    maxPort: 8010,
};

// Function to find an available port
async function findAvailablePort(startPort: number, endPort: number): Promise<number> {
    for (let port = startPort; port <= endPort; port++) {
        try {
            const server = createServer();
            await new Promise<void>((resolve, reject) => {
                server.once('error', reject);
                server.once('listening', () => {
                    server.close(() => resolve());
                });
                server.listen(port);
            });
            return port;
        } catch {
            if (port === endPort) {
                throw new Error('No available ports found');
            }
            // Continue to next port
            continue;
        }
    }
    throw new Error('No available ports found');
}

async function startServer() {
    try {
        const port = await findAvailablePort(WS_CONFIG.startPort, WS_CONFIG.maxPort);
        const wss = new WebSocketServer({
            port,
            clientTracking: true,
            perMessageDeflate: false
        });

        console.log(`Memory stats WebSocket server running on ws://localhost:${port}`);
        // Write the port to a file so other processes can find it
        const fs = await import('fs');
        const path = await import('path');
        const portFilePath = path.join(process.cwd(), '.ws-port');
        fs.writeFileSync(portFilePath, port.toString());

        function heartbeat(ws: WebSocket) {
            const client = ws as WebSocket & { isAlive?: boolean };
            client.isAlive = true;
        }

        function noop() { }

        const pingInterval = setInterval(() => {
            wss.clients.forEach((ws) => {
                const client = ws as WebSocket & { isAlive?: boolean };
                if (client.isAlive === false) {
                    console.log('Client connection terminated due to timeout');
                    return client.terminate();
                }

                client.isAlive = false;
                client.ping(noop);
            });
        }, WS_CONFIG.pingInterval);

        wss.on('connection', (ws) => {
            console.log('Client connected');
            const client = ws as WebSocket & { isAlive?: boolean };
            client.isAlive = true;

            // Handle pong messages to keep connection alive
            client.on('pong', () => heartbeat(client));

            // Clean up event listeners on disconnect
            client.on('close', () => {
                console.log('Client disconnected');
                client.isAlive = false;
            });

            client.on('error', (error) => {
                console.error('WebSocket error:', error);
                client.isAlive = false;
            });

            // Handle incoming messages
            client.on('message', (data) => {
                try {
                    // Broadcast the message to all connected clients
                    wss.clients.forEach((c) => {
                        if (c.readyState === WebSocket.OPEN) {
                            c.send(data.toString());
                        }
                    });
                } catch (error) {
                    console.error('Error handling message:', error);
                }
            });
        });

        wss.on('error', (error) => {
            console.error('WebSocket server error:', error);
        });

        // Clean up interval on server close
        wss.on('close', () => {
            clearInterval(pingInterval);
            try {
                fs.unlinkSync(portFilePath);
            } catch {
                // Ignore error if file doesn't exist
                void 0;
            }
        });

        // Handle process termination
        process.on('SIGINT', () => {
            wss.close(() => {
                console.log('WebSocket server closed');
                try {
                    fs.unlinkSync(portFilePath);
                } catch {
                    // Ignore error if file doesn't exist
                    void 0;
                }
                process.exit(0);
            });
        });

    } catch (error) {
        console.error('Failed to start WebSocket server:', error);
        process.exit(1);
    }
}

startServer().catch(console.error);