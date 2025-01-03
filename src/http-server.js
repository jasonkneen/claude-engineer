/**
 * Universal MCP Server - HTTP & SSE Implementation
 * Extends the base server with Express HTTP and SSE support
 */

const express = require('express');
const path = require('path');

class HTTPServer {
    constructor(port = 3000) {
        this.port = port;
        this.app = express();
        this.setupMiddleware();
        this.setupRoutes();
        this.sseClients = new Set();
    }

    setupMiddleware() {
        this.app.use(express.json());
        this.app.use(express.static(path.join(__dirname, 'ui')));
    }

    setupRoutes() {
        // REST endpoint for JSON-RPC calls
        this.app.post('/mcp', async (req, res) => {
            try {
                const result = await this.handleJSONRPC(req.body);
                res.json(result);
            } catch (error) {
                res.status(500).json({
                    jsonrpc: '2.0',
                    error: { code: -32000, message: error.message },
                    id: null
                });
            }
        });

        // SSE endpoint for streaming responses
        this.app.get('/mcp/stream', (req, res) => {
            const requestData = req.query.request;
            if (!requestData) {
                res.status(400).send('Missing request parameter');
                return;
            }

            // Set up SSE headers
            res.writeHead(200, {
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive'
            });

            // Add client to active SSE connections
            this.sseClients.add(res);

            try {
                const request = JSON.parse(decodeURIComponent(requestData));
                this.handleStreamingRequest(request, res);
            } catch (error) {
                const errorResponse = {
                    jsonrpc: '2.0',
                    error: { code: -32700, message: 'Parse error' },
                    id: null
                };
                res.write(`data: ${JSON.stringify(errorResponse)}\n\n`);
                res.end();
                this.sseClients.delete(res);
            }

            // Handle client disconnect
            req.on('close', () => {
                this.sseClients.delete(res);
            });
        });

        // UI endpoint
        this.app.get('/', (req, res) => {
            res.sendFile(path.join(__dirname, 'ui', 'index.html'));
        });
    }

    async handleStreamingRequest(request, res) {
        try {
            const handler = this.methods.get(request.method);
            if (!handler) {
                const errorResponse = {
                    jsonrpc: '2.0',
                    error: { code: -32601, message: 'Method not found' },
                    id: request.id
                };
                res.write(`data: ${JSON.stringify(errorResponse)}\n\n`);
                res.end();
                return;
            }

            // Create wrapper for streaming responses
            const streamWrapper = {
                send: (data) => {
                    const response = {
                        jsonrpc: '2.0',
                        result: data,
                        id: request.id
                    };
                    res.write(`data: ${JSON.stringify(response)}\n\n`);
                },
                error: (error) => {
                    const response = {
                        jsonrpc: '2.0',
                        error: { code: -32000, message: error.message },
                        id: request.id
                    };
                    res.write(`data: ${JSON.stringify(response)}\n\n`);
                },
                end: () => {
                    res.end();
                    this.sseClients.delete(res);
                }
            };

            // Call handler with streaming wrapper
            await handler(request.params, streamWrapper);
        } catch (error) {
            const errorResponse = {
                jsonrpc: '2.0',
                error: { code: -32000, message: error.message },
                id: request.id
            };
            res.write(`data: ${JSON.stringify(errorResponse)}\n\n`);
            res.end();
            this.sseClients.delete(res);
        }
    }

    start() {
        return new Promise((resolve, reject) => {
            try {
                this.server = this.app.listen(this.port, () => {
                    console.log(`MCP Server listening on port ${this.port}`);
                    resolve();
                });
            } catch (error) {
                reject(error);
            }
        });
    }

    stop() {
        return new Promise((resolve, reject) => {
            if (this.server) {
                // Close all SSE connections
                for (const client of this.sseClients) {
                    client.end();
                }
                this.sseClients.clear();

                // Close HTTP server
                this.server.close((error) => {
                    if (error) {
                        reject(error);
                    } else {
                        resolve();
                    }
                });
            } else {
                resolve();
            }
        });
    }
}

module.exports = HTTPServer;