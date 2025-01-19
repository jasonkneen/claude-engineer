#!/usr/bin/env node

import Anthropic from '@anthropic-ai/sdk';
import chalk from 'chalk';
import promptSync from 'prompt-sync';
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';
import { z } from 'zod';
import ora from 'ora';
import boxen from 'boxen';
import Table from 'cli-table3';
import { readFile } from 'fs/promises';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const prompt = promptSync({ sigint: true });
// Tool validation schema
const ToolSchema = z.object({
    name: z.string(),
    description: z.string(),
    schema: z.object({
        input: z.record(z.any()),
        output: z.record(z.any())
    }),
    execute: z.function()
});

// System prompts with fallback values
const DEFAULT_PROMPT = "You are Claude, an AI assistant. Respond to queries helpfully and honestly.";
const TOOLS_PROMPT = "When using tools, format response as valid JSON with 'tool' and 'parameters' fields.";

const SYSTEM_PROMPTS = {
    default: DEFAULT_PROMPT,
    tools: TOOLS_PROMPT
};

// Try to load custom prompts
try {
    const defaultPrompt = await readFile(path.join(__dirname, 'prompts', 'default.txt'), 'utf-8');
    const toolsPrompt = await readFile(path.join(__dirname, 'prompts', 'tools.txt'), 'utf-8');
    
    SYSTEM_PROMPTS.default = defaultPrompt;
    SYSTEM_PROMPTS.tools = toolsPrompt;
} catch (err) {
    console.log(chalk.yellow('Using default system prompts. Create custom prompts in the prompts directory.'));
}
class CE3 {
    constructor() {
        if (!process.env.ANTHROPIC_API_KEY) {
            throw new Error(
                'ANTHROPIC_API_KEY environment variable is required.\n' +
                'Please set it in your environment before running CE3.\n' +
                'Example: export ANTHROPIC_API_KEY=your-api-key'
            );
        }
        this.anthropic = new Anthropic({
            apiKey: process.env.ANTHROPIC_API_KEY,
        });
        
        this.history = [];
        this.totalTokens = 0;
        this.tools = new Map();
        this.spinner = ora();
        this.loadTools();
        
        // Initialize system message
        this.history.push({
            role: 'system',
            content: SYSTEM_PROMPTS.default
        });
    }

    async loadTools() {
        const toolsDir = path.join(__dirname, 'tools');
        if (!fs.existsSync(toolsDir)) return;

        for (const file of fs.readdirSync(toolsDir)) {
            if (file.endsWith('.js')) {
                try {
                    const toolPath = path.join(toolsDir, file);
                    const toolModule = await import(toolPath);
                    const tool = toolModule.default;
                    
                    // Validate tool with schema
                    const validatedTool = ToolSchema.parse(tool);
                    this.tools.set(validatedTool.name, validatedTool);
                } catch (err) {
                    console.error(chalk.red(`Error loading tool ${file}:`, err));
                }
            }
        }

        // Update system prompt with available tools
        if (this.tools.size > 0) {
            const toolsTable = new Table({
                head: ['Tool', 'Description'],
                style: { head: ['cyan'] }
            });

            for (const [name, tool] of this.tools) {
                toolsTable.push([name, tool.description]);
            }

            console.log(boxen(toolsTable.toString(), {
                padding: 1,
                margin: 1,
                borderStyle: 'round',
                borderColor: 'cyan',
                title: 'Available Tools'
            }));
        }
    }

    async handleCommand(input) {
        switch (input.toLowerCase()) {
            case 'quit':
                console.log(chalk.yellow('Goodbye!'));
                process.exit(0);
            case 'reset':
                this.history = [];
                this.totalTokens = 0;
                console.log(chalk.green('Conversation reset'));
                return true;
            case 'refresh':
                this.tools.clear();
                this.loadTools();
                console.log(chalk.green('Tools refreshed'));
                return true;
            default:
                return false;
        }
    }

    async chat() {
        console.log(boxen('CE3 - Claude Enhanced Environment', {
            padding: 1,
            margin: 1,
            borderStyle: 'double',
            borderColor: 'blue'
        }));
        console.log(chalk.gray('Type "quit" to exit, "reset" to clear history, "refresh" to reload tools\n'));

        while (true) {
            const userInput = prompt(chalk.green('You: '));
            
            if (!userInput.trim()) continue;
            
            if (await this.handleCommand(userInput)) continue;

            try {
                this.history.push({ role: 'user', content: userInput });

                this.spinner.start('Thinking...');
                const response = await this.anthropic.messages.create({
                    model: 'claude-3-opus-20240229',
                    max_tokens: 4096,
                    messages: this.history,
                    system: SYSTEM_PROMPTS.tools
                });
                this.spinner.stop();

                const assistantMessage = response.content[0].text;
                
                // Check for tool calls
                try {
                    const toolCall = JSON.parse(assistantMessage);
                    if (toolCall.tool && this.tools.has(toolCall.tool)) {
                        const tool = this.tools.get(toolCall.tool);
                        this.spinner.start(`Executing ${tool.name}...`);
                        const result = await tool.execute(toolCall.parameters);
                        this.spinner.stop();
                        
                        this.history.push({ 
                            role: 'assistant', 
                            content: `Tool ${tool.name} executed with result: ${JSON.stringify(result)}`
                        });
                    } else {
                        this.history.push({ role: 'assistant', content: assistantMessage });
                    }
                } catch {
                    this.history.push({ role: 'assistant', content: assistantMessage });
                }

                this.totalTokens += response.usage.input_tokens + response.usage.output_tokens;

                console.log(chalk.blue('\nClaude:'), assistantMessage);
                console.log(boxen(
                    `Tokens used this session: ${this.totalTokens}`, {
                        padding: 0,
                        margin: 1,
                        borderStyle: 'single',
                        borderColor: 'gray'
                    }
                ));

            } catch (error) {
                this.spinner.stop();
                console.error(chalk.red('Error:', error.message));
            }
        }
    }
}

const ce3 = new CE3();
ce3.chat().catch(err => {
    console.error(chalk.red('Fatal error:', err));
    process.exit(1);
});
