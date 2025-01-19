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

export interface LogMessage {
    id: string;
    timestamp: string;
    type: 'info' | 'warning' | 'error';
    message: string;
    w3w?: string;
}

export interface WebSocketMessage {
    type: 'stats' | 'log';
    payload: StatsMessage | LogMessage;
}

export interface ComponentBaseProps {
    className?: string;
}

export interface StatsComponentProps extends ComponentBaseProps {
    stats: StatsMessage;
}

export interface EventLogProps extends ComponentBaseProps {
    logs: LogMessage[];
}