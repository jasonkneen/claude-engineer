import { LogMessage, StatsMessage } from '../types/memory';

export const generateMockEventLogs = (): LogMessage[] => {
    const now = new Date();
    return [
        {
            id: '1',
            type: 'info',
            message: 'Nexus point created: user',
            timestamp: new Date(now.getTime() - 5000).toISOString(),
            w3w: 'eta.theta.beta'
        },
        {
            id: '2',
            type: 'info',
            message: 'Memory block added: Sample memory content',
            timestamp: new Date(now.getTime() - 4000).toISOString(),
            w3w: 'theta.kappa.delta'
        },
        {
            id: '3',
            type: 'warning',
            message: 'High memory utilization detected in working memory',
            timestamp: new Date(now.getTime() - 3000).toISOString(),
            w3w: 'omega.phi.gamma'
        },
        {
            id: '4',
            type: 'error',
            message: 'Failed to compress memory block: Insufficient tokens',
            timestamp: new Date(now.getTime() - 2000).toISOString(),
            w3w: 'alpha.beta.gamma'
        },
        {
            id: '5',
            type: 'info',
            message: 'Successfully merged overlapping memory blocks',
            timestamp: new Date(now.getTime() - 1000).toISOString(),
            w3w: 'delta.epsilon.zeta'
        }
    ];
};

export const generateMockOperationStats = (): StatsMessage => {
    return {
        pools: {
            working: {
                size: 5045,
                count: 50,
                limit: 8192,
                utilization: 0.62
            },
            short_term: {
                size: 23758,
                count: 118,
                limit: 128000,
                utilization: 0.19
            },
            long_term: {
                size: 20904,
                count: 41
            }
        },
        operations: {
            avg_recall_time: 145,
            compression_count: 32,
            promotions: 156,
            demotions: 89,
            merges: 45,
            retrievals: 278
        },
        nexus_points: {
            count: 14,
            types: {
                user: 5,
                llm: 6,
                system: 3
            }
        },
        generations: 42,
        total_tokens: 49707
    };
};