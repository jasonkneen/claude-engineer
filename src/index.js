/**
 * Universal MCP Server - Entry Point
 */

const MCPServer = require('./server');
const MCPStdio = require('./stdio');

class UniversalMCP {
    constructor(options = {}) {
        this.options = {
            mode: process.env.MCP_MODE || 'http',
            port: parseInt(process.env.MCP_PORT || '3000', 10),
            enableUI: process.env.MCP_UI === 'true',
            ...options
        };

        this.initializeServer();
    }

    initializeServer() {
        switch (this.options.mode) {
            case 'stdio':
                this.instance = new MCPStdio();
                break;
            case 'http':
                this.instance = new MCPServer(this.options.port);
                break;
            case 'hybrid':
                // TODO: Implement hybrid mode
                throw new Error('Hybrid mode not yet implemented');
            default:
                throw new Error(`Unknown mode: ${this.options.mode}`);
        }
    }

    registerMethod(name, handler) {
        this.instance.registerMethod(name, handler);
    }

    start() {
        if (this.instance instanceof MCPServer) {
            this.instance.start();
        }
    }
}

// CLI handling
if (require.main === module) {
    const args = process.argv.slice(2);
    const options = {
        mode: args.includes('--stdio') ? 'stdio' : 'http',
        port: args.includes('--port') ? parseInt(args[args.indexOf('--port') + 1], 10) : 3000,
        enableUI: args.includes('--enableUI')
    };

    const server = new UniversalMCP(options);
    
    // Register built-in methods
    server.registerMethod('ping', async () => ({ pong: Date.now() }));
    server.registerMethod('getServerCapabilities', async () => ({
        methods: ['ping', 'getServerCapabilities'],
        transport: [options.mode],
        version: '1.0.0',
        nodeID: 'universal-mcp-instance'
    }));

    server.start();
}

module.exports = UniversalMCP;