/**
 * Universal MCP Server - HTTP & SSE Implementation
 */

class MCPServer {
    constructor(port = 3000) {
        this.port = port;
        this.methods = new Map();
    }

    registerMethod(name, handler) {
        this.methods.set(name, handler);
    }

    async handleJSONRPC(request) {
        const { jsonrpc, method, params, id } = request;
        
        if (jsonrpc !== '2.0') {
            return {
                jsonrpc: '2.0',
                error: { code: -32600, message: 'Invalid Request' },
                id: null
            };
        }

        const handler = this.methods.get(method);
        if (!handler) {
            return {
                jsonrpc: '2.0',
                error: { code: -32601, message: 'Method not found' },
                id
            };
        }

        try {
            const result = await handler(params);
            return { jsonrpc: '2.0', result, id };
        } catch (error) {
            return {
                jsonrpc: '2.0',
                error: { code: -32000, message: error.message },
                id
            };
        }
    }

    start() {
        // TODO: Implement Express/HTTP server setup
        console.log(`MCP Server starting on port ${this.port}`);
    }
}

module.exports = MCPServer;