import express from 'express';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const app = express();
app.use(express.json());
app.use(express.static(__dirname));

const memory = {};
const tools = {};

// Serve index.html at root
app.get('/', (req, res) => {
    res.sendFile(join(__dirname, 'index.html'));
});

// API endpoints
app.get('/api/status', (req, res) => {
    res.json({
        status: 'Smart Node Active',
        memory_status: Object.keys(memory).length,
        available_tools: Object.keys(tools)
    });
});

app.post('/api/tool/:toolName', (req, res) => {
    const { toolName } = req.params;
    const params = req.body;
    
    // Tool execution logic
    const result = executeToolAction(toolName, params);
    
    res.json({
        tool: toolName,
        params,
        result
    });
});

function executeToolAction(toolName, params) {
    if (!tools[toolName]) {
        return { error: 'Tool not found' };
    }
    
    try {
        return tools[toolName](params);
    } catch (error) {
        return { error: error.message };
    }
}

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Smart Node running on http://localhost:${PORT}`);
});