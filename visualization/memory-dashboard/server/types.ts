export interface MemoryBlock {
    id: string;
    content: string;
    level: 'working' | 'short_term' | 'long_term';
    created_at: Date;
    last_accessed: Date;
    access_count: number;
    tokens: number;
    w3w: string;
}

export interface NexusPoint {
    id: string;
    memory_block_id: string;
    significance_type: 'user' | 'llm' | 'system';
    created_at: Date;
    description: string;
    related_points: Set<string>;
    w3w: string;
}

export interface MemoryStats {
    pools: {
        working: {
            size: number;
            count: number;
            limit: number;
            utilization: number;
        };
        short_term: {
            size: number;
            count: number;
            limit: number;
            utilization: number;
        };
        long_term: {
            size: number;
            count: number;
        };
    };
    operations: {
        promotions: number;
        demotions: number;
        merges: number;
        retrievals: number;
        avg_recall_time: number;
        compression_count: number;
    };
    nexus_points: {
        count: number;
        types: {
            user: number;
            llm: number;
            system: number;
        };
    };
    generations: number;
    total_tokens: number;
}

export interface LogMessage {
    id: string;
    timestamp: string;
    type: 'info' | 'warning' | 'error';
    message: string;
    w3w?: string;
}

export interface StatsMessage {
    pools: {
        working: {
            size: number;
            count: number;
            limit: number;
            utilization: number;
        };
        short_term: {
            size: number;
            count: number;
            limit: number;
            utilization: number;
        };
        long_term: {
            size: number;
            count: number;
        };
    };
    operations: {
        promotions: number;
        demotions: number;
        merges: number;
        retrievals: number;
        avg_recall_time: number;
        compression_count: number;
    };
    nexus_points: {
        count: number;
        types: {
            user: number;
            llm: number;
            system: number;
        };
    };
    generations: number;
    total_tokens: number;
}

export interface MemoryEvent {
    type: 'block_added' | 'block_moved' | 'nexus_point' | 'compression';
    data: {
        content?: string;
        from?: string;
        to?: string;
        type?: string;
        generation?: number;
        w3w?: string;
    };
}