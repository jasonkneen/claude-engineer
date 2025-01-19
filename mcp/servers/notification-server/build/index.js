#!/usr/bin/env node
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ErrorCode, ListToolsRequestSchema, McpError, } from '@modelcontextprotocol/sdk/types.js';
import axios from 'axios';
const SSE_SERVER_PORT = 3500; // Default SSE server port
class NotificationServer {
    server;
    sseBaseUrl;
    constructor() {
        this.server = new Server({
            name: 'notification-server',
            version: '0.1.0',
        }, {
            capabilities: {
                tools: {},
            },
        });
        this.sseBaseUrl = `http://localhost:${SSE_SERVER_PORT}`;
        this.setupTools();
    }
    setupTools() {
        // List available tools
        this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
            tools: [
                {
                    name: 'send_notification',
                    description: 'Send a notification to subscribed clients',
                    inputSchema: {
                        type: 'object',
                        properties: {
                            message: {
                                type: 'string',
                                description: 'The notification message',
                            },
                            type: {
                                type: 'string',
                                enum: ['info', 'warning', 'error'],
                                description: 'The type of notification',
                            },
                            metadata: {
                                type: 'object',
                                description: 'Optional additional data',
                                additionalProperties: true,
                            },
                        },
                        required: ['message', 'type'],
                    },
                },
                {
                    name: 'broadcast_status',
                    description: 'Broadcast a system status update',
                    inputSchema: {
                        type: 'object',
                        properties: {
                            status: {
                                type: 'string',
                                enum: ['online', 'offline', 'maintenance', 'degraded'],
                                description: 'The system status',
                            },
                            message: {
                                type: 'string',
                                description: 'Status message',
                            },
                            affectedServices: {
                                type: 'array',
                                items: {
                                    type: 'string',
                                },
                                description: 'List of affected services',
                            },
                        },
                        required: ['status', 'message'],
                    },
                },
            ],
        }));
        // Handle tool calls
        this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
            switch (request.params.name) {
                case 'send_notification':
                    return this.handleSendNotification(request.params.arguments);
                case 'broadcast_status':
                    return this.handleBroadcastStatus(request.params.arguments);
                default:
                    throw new McpError(ErrorCode.MethodNotFound, `Unknown tool: ${request.params.name}`);
            }
        });
    }
    async handleSendNotification(args) {
        const payload = {
            message: args.message,
            type: args.type,
            timestamp: Date.now(),
            metadata: args.metadata,
        };
        try {
            await axios.post(`${this.sseBaseUrl}/emit/notifications`, {
                type: 'notification',
                data: payload,
            });
            return {
                content: [
                    {
                        type: 'text',
                        text: `Notification sent successfully: ${args.message}`,
                    },
                ],
            };
        }
        catch (error) {
            const message = error?.message || 'Unknown error';
            throw new McpError(ErrorCode.InternalError, `Failed to send notification: ${message}`);
        }
    }
    async handleBroadcastStatus(args) {
        const payload = {
            status: args.status,
            message: args.message,
            timestamp: Date.now(),
            affectedServices: args.affectedServices,
        };
        try {
            await axios.post(`${this.sseBaseUrl}/emit/system-status`, {
                type: 'status-update',
                data: payload,
            });
            return {
                content: [
                    {
                        type: 'text',
                        text: `Status broadcast sent successfully: ${args.status} - ${args.message}`,
                    },
                ],
            };
        }
        catch (error) {
            const message = error?.message || 'Unknown error';
            throw new McpError(ErrorCode.InternalError, `Failed to broadcast status: ${message}`);
        }
    }
    async run() {
        const transport = new StdioServerTransport();
        await this.server.connect(transport);
        console.error('Notification MCP server running on stdio');
    }
}
const server = new NotificationServer();
server.run().catch(console.error);
