import React, { useEffect, useState } from 'react';
import {
Box,
Card,
CardContent,
Typography,
LinearProgress,
List,
ListItem,
Divider,
Grid,
Paper,
} from '@mui/material';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';

interface MemoryStats {
workingMemoryTokens: number;
workingMemoryLimit: number;
archivedMemoryCount: number;
operationStats: {
    archiveCount: number;
    recallCount: number;
    compressionCount: number;
};
recentOperations: Array<{
    timestamp: string;
    operation: string;
    tokens: number;
}>;
}

interface ArchivedMemory {
w3wToken: string;
timestamp: string;
metadata: {
    significance: string;
    tokens: number;
    summary?: string;
};
}

interface WebSocketMessage {
type: 'stats' | 'archived_memories';
data: MemoryStats | ArchivedMemory[];
}

export const MemoryDisplay: React.FC = () => {
const [stats, setStats] = useState<MemoryStats>({
    workingMemoryTokens: 0,
    workingMemoryLimit: 200000,
    archivedMemoryCount: 0,
    operationStats: {
    archiveCount: 0,
    recallCount: 0,
    compressionCount: 0,
    },
    recentOperations: [],
});
const [archivedMemories, setArchivedMemories] = useState<ArchivedMemory[]>([]);
const [wsConnected, setWsConnected] = useState(false);

useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000');

    ws.onopen = () => {
    setWsConnected(true);
    console.log('Connected to memory server');
    };

    ws.onmessage = (event) => {
    const message: WebSocketMessage = JSON.parse(event.data);
    if (message.type === 'stats') {
        setStats(message.data as MemoryStats);
    } else if (message.type === 'archived_memories') {
        setArchivedMemories(message.data as ArchivedMemory[]);
    }
    };

    ws.onclose = () => {
    setWsConnected(false);
    console.log('Disconnected from memory server');
    };

    return () => ws.close();
}, []);

return (
    <Box sx={{ p: 3 }}>
    <Typography variant="h4" gutterBottom>
        Memory Dashboard {wsConnected && '(Connected)'}
    </Typography>

    <Grid container spacing={3}>
        {/* Memory Usage Card */}
        <Grid item xs={12} md={6}>
        <Card>
            <CardContent>
            <Typography variant="h6">Working Memory Usage</Typography>
            <Box sx={{ mt: 2 }}>
                <LinearProgress
                variant="determinate"
                value={(stats.workingMemoryTokens / stats.workingMemoryLimit) * 100}
                />
                <Typography variant="body2" sx={{ mt: 1 }}>
                {stats.workingMemoryTokens} / {stats.workingMemoryLimit} tokens
                </Typography>
            </Box>
            </CardContent>
        </Card>
        </Grid>

        {/* Operation Stats Card */}
        <Grid item xs={12} md={6}>
        <Card>
            <CardContent>
            <Typography variant="h6">Operation Statistics</Typography>
            <Box sx={{ mt: 2 }}>
                <Typography>Archives: {stats.operationStats.archiveCount}</Typography>
                <Typography>Recalls: {stats.operationStats.recallCount}</Typography>
                <Typography>Compressions: {stats.operationStats.compressionCount}</Typography>
            </Box>
            </CardContent>
        </Card>
        </Grid>

        {/* Operations Chart */}
        <Grid item xs={12}>
        <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>Recent Operations</Typography>
            <LineChart width={800} height={300} data={stats.recentOperations}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="timestamp" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="tokens" stroke="#8884d8" />
            </LineChart>
        </Paper>
        </Grid>

        {/* Archived Memories */}
        <Grid item xs={12}>
        <Card>
            <CardContent>
            <Typography variant="h6">Archived Memories</Typography>
            <List>
                {archivedMemories.map((memory, index) => (
                <React.Fragment key={memory.w3wToken}>
                    <ListItem>
                    <Box sx={{ width: '100%' }}>
                        <Typography variant="subtitle1">
                        W3W: {memory.w3wToken}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                        Tokens: {memory.metadata.tokens} | Type: {memory.metadata.significance}
                        </Typography>
                        {memory.metadata.summary && (
                        <Typography variant="body2">
                            Summary: {memory.metadata.summary}
                        </Typography>
                        )}
                    </Box>
                    </ListItem>
                    {index < archivedMemories.length - 1 && <Divider />}
                </React.Fragment>
                ))}
            </List>
            </CardContent>
        </Card>
        </Grid>
    </Grid>
    </Box>
);
};

export default MemoryDisplay;

