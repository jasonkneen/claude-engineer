import { z } from 'zod';

const echo = {
    name: 'echo',
    description: 'Echoes back the input message',
    schema: {
        input: {
            message: z.string().describe('The message to echo back')
        },
        output: {
            echo: z.string().describe('The echoed message')
        }
    },
    execute: async (params) => {
        return {
            echo: params.message
        };
    }
};

export default echo;

