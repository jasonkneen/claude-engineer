import WebSocket from 'ws';
import sqlite3 from 'sqlite3';
import { open } from 'sqlite-db';
import { encode } from '@dqbd/tiktoken';

// Types for memory data structures
interface Memory {
id: string;
content: string;
embedding: number[];
timestamp: number;
importance: number;
tags: string[];
metadata: {
    source: string;
    context?: string;
    tokens: number;
};
}

interface MemoryQuery {
content?: string;
tags?: string[];
importance?: number;
limit?: number;
semantic?: boolean;
}

// Message types for WebSocket communication
type MessageType = 'archive' | 'recall' | 'delete' | 'update';

interface WSMessage {
type: MessageType;
payload: any;
}

class MemoryStore {
private db: sqlite3.Database;
private wss: WebSocket.Server;

constructor(port: number = 8765) {
    // Initialize WebSocket server
    this.wss = new WebSocket.Server({ port });
    this.setupWebSocket();

    // Initialize SQLite database
    this.initDatabase();
}

private async initDatabase() {
    this.db = await open('memories.db');
    
    // Create tables if they don't exist
    await this.db.exec(`
    CREATE TABLE IF NOT EXISTS memories (
        id TEXT PRIMARY KEY,
        content TEXT NOT NULL,
        embedding BLOB,
        timestamp INTEGER,
        importance REAL,
        metadata JSON
    );

    CREATE TABLE IF NOT EXISTS memory_tags (
        memory_id TEXT,
        tag TEXT,
        FOREIGN KEY(memory_id) REFERENCES memories(id)
    );

    CREATE INDEX IF NOT EXISTS idx_embedding ON memories(embedding);
    CREATE INDEX IF NOT EXISTS idx_timestamp ON memories(timestamp);
    CREATE INDEX IF NOT EXISTS idx_tags ON memory_tags(tag);
    `);
}

private setupWebSocket() {
    this.wss.on('connection', (ws: WebSocket) => {
    ws.on('message', async (message: string) => {
        try {
        const { type, payload } = JSON.parse(message) as WSMessage;
        
        switch (type) {
            case 'archive':
            await this.archiveMemory(payload);
            ws.send(JSON.stringify({ type: 'success', operation: 'archive' }));
            break;
            
            case 'recall':
            const memories = await this.recallMemories(payload);
            ws.send(JSON.stringify({ type: 'recall', memories }));
            break;
            
            case 'delete':
            await this.deleteMemory(payload.id);
            ws.send(JSON.stringify({ type: 'success', operation: 'delete' }));
            break;
            
            case 'update':
            await this.updateMemory(payload);
            ws.send(JSON.stringify({ type: 'success', operation: 'update' }));
            break;
        }
        } catch (error) {
        ws.send(JSON.stringify({ type: 'error', message: error.message }));
        }
    });
    });
}

private async generateEmbedding(text: string): Promise<number[]> {
    // TODO: Replace with actual embedding model
    // For now, using simple token counts as placeholder
    const tokens = encode(text);
    return Array.from(tokens).map(t => t / 100);
}

private async archiveMemory(memory: Memory) {
    const embedding = await this.generateEmbedding(memory.content);
    
    await this.db.run(
    `INSERT INTO memories (id, content, embedding, timestamp, importance, metadata)
    VALUES (?, ?, ?, ?, ?, ?)`,
    [
        memory.id,
        memory.content,
        Buffer.from(new Float32Array(embedding).buffer),
        memory.timestamp,
        memory.importance,
        JSON.stringify(memory.metadata)
    ]
    );

    // Insert tags
    for (const tag of memory.tags) {
    await this.db.run(
        'INSERT INTO memory_tags (memory_id, tag) VALUES (?, ?)',
        [memory.id, tag]
    );
    }
}

private async recallMemories(query: MemoryQuery): Promise<Memory[]> {
    let sql = 'SELECT * FROM memories m';
    const params: any[] = [];

    if (query.tags?.length) {
    sql += ` JOIN memory_tags mt ON m.id = mt.memory_id 
            WHERE mt.tag IN (${query.tags.map(() => '?').join(',')})`;
    params.push(...query.tags);
    }

    if (query.importance) {
    sql += params.length ? ' AND' : ' WHERE';
    sql += ' importance >= ?';
    params.push(query.importance);
    }

    if (query.semantic && query.content) {
    const searchEmbedding = await this.generateEmbedding(query.content);
    // Add cosine similarity calculation
    sql += params.length ? ' AND' : ' WHERE';
    sql += ` EXISTS (SELECT 1 FROM embeddings WHERE memory_id = m.id 
            AND cosine_similarity(embedding, ?) > 0.8)`;
    params.push(Buffer.from(new Float32Array(searchEmbedding).buffer));
    }

    sql += ' ORDER BY timestamp DESC';
    if (query.limit) {
    sql += ' LIMIT ?';
    params.push(query.limit);
    }

    const memories = await this.db.all(sql, params);
    return memories.map(this.mapRowToMemory);
}

private async deleteMemory(id: string) {
    await this.db.run('DELETE FROM memory_tags WHERE memory_id = ?', [id]);
    await this.db.run('DELETE FROM memories WHERE id = ?', [id]);
}

private async updateMemory(memory: Partial<Memory> & { id: string }) {
    const updates: string[] = [];
    const params: any[] = [];

    if (memory.content) {
    updates.push('content = ?');
    params.push(memory.content);
    }

    if (memory.importance !== undefined) {
    updates.push('importance = ?');
    params.push(memory.importance);
    }

    if (memory.metadata) {
    updates.push('metadata = ?');
    params.push(JSON.stringify(memory.metadata));
    }

    if (updates.length) {
    params.push(memory.id);
    await this.db.run(
        `UPDATE memories SET ${updates.join(', ')} WHERE id = ?`,
        params
    );
    }

    if (memory.tags) {
    await this.db.run(
        'DELETE FROM memory_tags WHERE memory_id = ?',
        [memory.id]
    );
    for (const tag of memory.tags) {
        await this.db.run(
        'INSERT INTO memory_tags (memory_id, tag) VALUES (?, ?)',
        [memory.id, tag]
        );
    }
    }
}

private mapRowToMemory(row: any): Memory {
    return {
    id: row.id,
    content: row.content,
    embedding: new Float32Array(row.embedding),
    timestamp: row.timestamp,
    importance: row.importance,
    tags: row.tags?.split(',') || [],
    metadata: JSON.parse(row.metadata)
    };
}
}

// Export server instance
export const memoryStore = new MemoryStore();

