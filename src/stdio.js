/**
 * Universal MCP Server - Stdio Implementation
 */

class MCPStdio {
    constructor() {
        this.methods = new Map();
        this.setupStdioHandlers();
    }

    setupStdioHandlers() {
        process.stdin.setEncoding('utf8');
        
        let buffer = '';
        process.stdin.on('data', (chunk) => {
            buffer += chunk;
            this.tryParseAndProcess(buffer);
        });
    }

    async tryParseAndProcess(buffer) {
        try {
            const request = JSON.parse(buffer);
            const response = await this.handleJSONRPC(request);
            process.stdout.write(JSON.stringify(response) + '\n');
        } catch (e) {
            // If it's not valid JSON yet, wait for more data
            if (!(e instanceof SyntaxError)) {
                process.stdout.write(JSON.stringify({
                    jsonrpc: '2.0',
                    error: { code: -32700, message: 'Parse error' },
                    id: null
                }) + '\n');
            }
        }
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
}

module.exports = MCPStdio;