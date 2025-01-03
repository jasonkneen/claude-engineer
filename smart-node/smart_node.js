import express from 'express';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import fs from 'fs/promises';
import { createProxyMiddleware } from 'http-proxy-middleware';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

class SmartNode {
    constructor() {
        this.app = express();
        this.memory = {};
        this.tools = {};
        this.instances = new Set();
        this.setupServer();
    }

    async setupServer() {
        this.app.use(express.json());
        
        // API endpoints
        this.app.post('/api/chat', async (req, res) => {
            try {
                const { message } = req.body;
                // TODO: Implement actual chat completion logic
                const response = `Echo: ${message}`;
                res.json({ response });
            } catch (error) {
                res.status(500).json({ error: error.message });
            }
        });

        this.app.get('/api/status', (req, res) => {
            res.json({
                status: 'active',
                instances: Array.from(this.instances),
                memory_size: Object.keys(this.memory).length,
                tools: Object.keys(this.tools)
            });
        });

        // Development mode: Proxy requests to Vite dev server
        if (process.env.NODE_ENV === 'development') {
            this.app.use('/', createProxyMiddleware({
                target: 'http://localhost:5173',
                changeOrigin: true,
                ws: true,
                router: {
                    // Keep /api requests pointing to the Express server
                    '/api': 'http://localhost:3000'
                }
            }));
        } else {
            // Production: Serve the built React app
            this.app.use(express.static(join(__dirname, 'frontend/dist')));
            this.app.get('*', (req, res) => {
                res.sendFile(join(__dirname, 'frontend/dist/index.html'));
            });
        }

        // Start server with port retry logic
        const startServer = (port) => {
            try {
                this.app.listen(port, () => {
                    console.log(`SmartNode active on http://localhost:${port}`);
                }).on('error', (err) => {
                    if (err.code === 'EADDRINUSE') {
                        console.log(`Port ${port} is busy, trying ${port + 1}...`);
                        startServer(port + 1);
                    } else {
                        console.error('Server error:', err);
                    }
                });
            } catch (err) {
                console.error('Failed to start server:', err);
            }
        };

        const PORT = process.env.PORT || 3000;
        startServer(PORT);
    }

    registerTool(name, handler) {
        this.tools[name] = handler;
        console.log(`Registered tool: ${name}`);
    }

    async registerInstance(id, metadata) {
        this.instances.add({ id, ...metadata, timestamp: Date.now() });
        console.log(`New instance registered: ${id}`);
    }
}

// Start the SmartNode
new SmartNode();