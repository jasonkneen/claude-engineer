# Universal MCP Server

**A single instance that supports multiple MCP modes (SSE, Stdio, REST), can act as both server and test client, and can be deployed in Docker or as a StackBlitz WebContainer.**

---

## Table of Contents
1. [Introduction](#introduction)  
2. [Core Features](#core-features)  
3. [Architecture Overview](#architecture-overview)  
4. [Deployment Modes](#deployment-modes)  
5. [Configuration & Discovery](#configuration--discovery)  
6. [Usage Examples](#usage-examples)  
7. [Example Directory Structure](#example-directory-structure)  
8. [Conclusion](#conclusion)

---

## Introduction

**Universal MCP Server** (or `universal-mcp`) is a single application that implements the [Model Context Protocol (MCP)](https://github.com/anthropic/mcp-spec) while supporting multiple transport mechanisms:

- **SSE** (Server-Sent Events)  
- **Stdio** (standard input/output)  
- **REST API** (for synchronous calls)  
- **Browser UI** (a test client interface)

In addition, it can be deployed as:

- A **Docker** container  
- A **StackBlitz WebContainer**  
- Or run **locally** on any Node.js or Python environment (depending on your chosen implementation language)

This universal server is designed for **maximum flexibility**—it can operate as both a *server* for handling MCP requests and a *test client* to issue requests to itself or other MCP endpoints.

---

## Core Features

1. **JSON-RPC 2.0 Compliance**  
   - Requests and responses follow the JSON-RPC 2.0 specification.  
   - Handles standard `jsonrpc`, `method`, `params`, and `id` fields for requests/responses.

2. **Transport Protocols**  
   - **HTTP + SSE**: Streams results in real-time.  
   - **REST**: Allows for direct POST requests without SSE.  
   - **STDIO**: Can run headless, reading JSON-RPC from `stdin` and returning results to `stdout`.

3. **Browser-Based UI**  
   - When accessed in a browser, it provides a minimal test interface (e.g., simple HTML/JS or Streamlit).  
   - Allows users to send JSON-RPC requests and view results (including streaming data).

4. **Deployment Flexibility**  
   - **Local CLI**: Run via command line (Node.js or Python).  
   - **Docker**: Self-contained container exposing ports for HTTP/SSE.  
   - **StackBlitz WebContainer**: In-browser Node-based environment for demos or rapid prototyping.

5. **Extensibility**  
   - Plug in new methods (e.g., `methodA`, `methodB`) using a modular approach.  
   - Optionally configure internal routing to other MCP servers (acting as a parent or aggregator node).

6. **Discovery & Metadata**  
   - Implements a standard method (e.g., `listMethods` or `getServerCapabilities`) to describe available RPC methods, version info, transport modes, etc.

---

## Architecture Overview

The **Universal MCP Server** can be viewed as a single node that:

- Listens for JSON-RPC requests via **HTTP**, **SSE**, or **STDIO**.  
- Optionally hosts a **UI** at `/ui` (or similar) when running in HTTP mode, so users can quickly test method calls.  
- Can **forward** certain calls to other MCP endpoints, effectively acting as a router or orchestrator.

### Key Components

1. **Core MCP Dispatcher**  
   - Interprets requests (JSON-RPC objects) and routes them to the correct “method” handler.

2. **Protocol Handlers**  
   - **HTTP/SSE**:  
     - Handles streaming vs. non-streaming calls (e.g., `curl` or browser-based SSE clients).  
   - **Stdio**:  
     - Reads one or multiple JSON-RPC requests from `stdin`, writes responses to `stdout`.  
   - **REST**:  
     - A simple `/mcp` POST endpoint for JSON requests (converts them internally to JSON-RPC calls).

3. **UI/Testing Interface**  
   - A minimal HTML or framework-based interface served on `/ui`.  
   - Contains an input area to craft JSON-RPC requests, a display area for results, and logic for SSE streaming.

4. **Deployment-Specific Wrappers**  
   - **Docker**: A `Dockerfile` that installs dependencies, exposes ports, and starts the server.  
   - **StackBlitz**: A config file (e.g., `stackblitz.toml`) ensuring it runs seamlessly in a web-based container.

---

## Deployment Modes

1. **Local/CLI**  
   - Run with a command-line flag or environment variable indicating `stdio` mode.  
   - Reads/writes JSON-RPC from/to `stdin`/`stdout`.

2. **HTTP & SSE**  
   - Run in server mode (default, or specify `--http 3000`).  
   - Exposes endpoints for REST-based JSON calls and SSE streaming.  
   - Optionally serves a UI at `/ui`.

3. **Docker**  
   - Build and run the container.  
   - Exposes a port (e.g., `3000`) for HTTP, SSE, and the UI.

4. **StackBlitz WebContainer**  
   - Runs the same Node-based server in-browser.  
   - Useful for demos, ephemeral testing, or quick prototyping.

---

## Configuration & Discovery

1. **Environment Variables / Config**  
   - `MCP_PORT`: The port to run the HTTP server on (default `3000`).  
   - `MCP_MODE`: One of `http`, `stdio`, or `hybrid`.  
   - `MCP_UI`: Enables or disables serving the test interface.

2. **Discovery Endpoint**  
   - A JSON-RPC method like `getServerCapabilities` or `listMethods` can return details:  
     ```json
     {
       "jsonrpc": "2.0",
       "result": {
         "methods": ["methodA", "methodB", ...],
         "transport": ["http", "sse", "stdio"],
         "version": "1.0.0",
         "nodeID": "universal-mcp-instance"
       },
       "id": "discover-1"
     }
     ```
   - This allows clients (including other MCP servers) to query what’s available.

3. **Metadata & Parent/Child Communication**  
   - Each instance can define a “node ID,” and optionally reference a “parent” node.  
   - Requests forwarded to child nodes or other MCP endpoints are simply additional JSON-RPC calls, possibly via SSE or REST bridging.

---

## Usage Examples

### 1. Local Testing (Stdio)

```bash
# Start in stdio mode:
node index.js --stdio

# Pass a JSON-RPC request in another shell:
echo '{"jsonrpc":"2.0","method":"ping","params":{},"id":"1"}' | node index.js --stdio

# Launch as an HTTP server with SSE and a test UI:
node index.js --http 3000 --enableUI

# Then visit http://localhost:3000/ui in a browser
# You can also send requests via:
curl -X POST -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"ping","params":{},"id":"1"}' \
  http://localhost:3000/mcp

  # Build the image:
docker build -t universal-mcp .

# Run the container, exposing port 3000:
docker run -p 3000:3000 universal-mcp

# Access http://localhost:3000/ui or /mcp


4. StackBlitz WebContainer
	•	Import the repository into StackBlitz or click a “Deploy to StackBlitz” link.
	•	A stackblitz.toml ensures Node 18 environment and auto-runs npm start.
	•	The server becomes accessible in the StackBlitz preview, where /ui can be tested.


   Example Directory Structure

Below is an example file layout for a Node.js implementation.

universal-mcp/
├── src/
│   ├── server.js         # HTTP & SSE logic
│   ├── stdio.js          # Stdio driver
│   ├── index.js          # Entry point (detect mode, run server or stdio)
│   ├── ui/
│   │   ├── index.html    # Test interface
│   │   └── ui.js         # JS for SSE + JSON-RPC UI
│   └── methods/
│       ├── ping.js       # Example JSON-RPC method
│       └── ...
├── Dockerfile
├── package.json
├── stackblitz.toml
└── README.md             # This document

Conclusion

The Universal MCP Server (universal-mcp) consolidates all MCP transport and deployment options into a single, flexible component. It can:
	1.	Run locally (stdin/stdout), over HTTP/SSE, or both at once.
	2.	Act as an HTTP server and a minimal test client UI in the browser.
	3.	Deploy seamlessly in a Docker container or a StackBlitz WebContainer.
	4.	Integrate with other MCP servers as a parent/child node, forwarding or aggregating JSON-RPC calls.

This approach ensures a single codebase can adapt to virtually any environment or workflow, providing a robust foundation for developing and testing agentic systems that follow the Model Context Protocol.