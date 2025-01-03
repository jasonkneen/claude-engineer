/**
 * Universal MCP - Browser Test Interface
 */

let eventSource = null;

function appendOutput(text) {
    const output = document.getElementById('output');
    output.textContent += text + '\n';
}

function clearOutput() {
    document.getElementById('output').textContent = '';
}

async function sendRequest() {
    clearOutput();
    const useSSE = document.getElementById('useSSE').checked;
    const input = document.getElementById('input').value;

    try {
        const request = JSON.parse(input);

        if (useSSE) {
            // Close existing SSE connection if any
            if (eventSource) {
                eventSource.close();
            }

            // Create new SSE connection
            eventSource = new EventSource(`/mcp/stream?request=${encodeURIComponent(input)}`);
            
            eventSource.onmessage = (event) => {
                appendOutput(event.data);
            };

            eventSource.onerror = (error) => {
                appendOutput('SSE Error: Connection closed');
                eventSource.close();
            };
        } else {
            // Regular HTTP POST request
            const response = await fetch('/mcp', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: input
            });

            const result = await response.json();
            appendOutput(JSON.stringify(result, null, 2));
        }
    } catch (error) {
        appendOutput(`Error: ${error.message}`);
    }
}