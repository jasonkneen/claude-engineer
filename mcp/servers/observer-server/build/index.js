#!/usr/bin/env node
/**
 * This is an MCP server that implements a supervision system.
 * It allows:
 * - Evaluating proposed solutions
 * - Tracking conversation context
 * - Providing feedback on approaches
 * - AI-powered code review
 */
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema, ListToolsRequestSchema, ErrorCode, McpError, } from "@modelcontextprotocol/sdk/types.js";
import OpenAI from "openai";
const OPENAI_API_KEY = process.env.OPENAI_API_KEY;
if (!OPENAI_API_KEY) {
    throw new Error("OPENAI_API_KEY environment variable is required");
}
const openai = new OpenAI({
    apiKey: OPENAI_API_KEY
});
/**
 * In-memory storage
 */
const context = {
    messages: [],
    currentTask: undefined,
    lastEvaluation: undefined
};
const server = new Server({
    name: "observer-server",
    version: "0.1.0",
}, {
    capabilities: {
        tools: {},
    },
});
server.setRequestHandler(ListToolsRequestSchema, async () => {
    return {
        tools: [
            {
                name: "evaluate_solution",
                description: "Evaluate a proposed solution or approach",
                inputSchema: {
                    type: "object",
                    properties: {
                        task: {
                            type: "string",
                            description: "The current task being worked on"
                        },
                        proposal: {
                            type: "string",
                            description: "The proposed solution or approach"
                        },
                        context: {
                            type: "string",
                            description: "Additional context about the current state"
                        }
                    },
                    required: ["task", "proposal"]
                }
            }
        ]
    };
});
server.setRequestHandler(CallToolRequestSchema, async (request) => {
    if (request.params.name !== "evaluate_solution") {
        throw new McpError(ErrorCode.MethodNotFound, "Unknown tool");
    }
    const task = String(request.params.arguments?.task);
    const proposal = String(request.params.arguments?.proposal);
    const additionalContext = String(request.params.arguments?.context || "");
    // Update context
    context.currentTask = task;
    context.messages.push({
        role: "assistant",
        content: proposal,
        timestamp: Date.now()
    });
    try {
        // Get AI review of the proposal
        const aiReview = await getAIReview(task, proposal, additionalContext);
        // Evaluate the proposal based on context and AI review
        const evaluation = await evaluateProposal(task, proposal, additionalContext, context, aiReview);
        // Store evaluation
        context.lastEvaluation = evaluation;
        context.messages.push({
            role: "system",
            content: `Evaluation: ${evaluation}`,
            timestamp: Date.now()
        });
        return {
            content: [{
                    type: "text",
                    text: evaluation
                }]
        };
    }
    catch (error) {
        console.error("Evaluation error:", error);
        throw new McpError(ErrorCode.InternalError, "Failed to evaluate proposal");
    }
});
/**
 * Get AI review using GPT-4-turbo
 */
async function getAIReview(task, proposal, context) {
    try {
        const response = await openai.chat.completions.create({
            model: "gpt-4-1106-preview",
            messages: [
                {
                    role: "system",
                    content: "You are a code observation model overseeing work done by another developer. You must give your full and honest appraisal of the proposed solution so the assistant can do this correctly. You should also be checking the work is completed properly."
                },
                {
                    role: "user",
                    content: `
Task: ${task}

Proposed Solution:
${proposal}

Additional Context:
${context}

Please evaluate this proposal considering:
1. Does it directly address the task requirements?
2. Are there any potential issues or risks?
3. Are there any suggested improvements?
4. Is the approach efficient and well-structured?
`
                }
            ],
            temperature: 0.7,
            max_tokens: 1000
        });
        return response.choices[0]?.message?.content || "No AI review available";
    }
    catch (error) {
        console.error("AI review error:", error);
        return "AI review unavailable";
    }
}
/**
 * Helper function to evaluate proposals
 */
async function evaluateProposal(task, proposal, additionalContext, context, aiReview) {
    const evaluation = [];
    // Add AI review
    evaluation.push("🤖 AI Review:");
    evaluation.push(aiReview);
    evaluation.push("\n📋 Additional Checks:");
    // Check task alignment
    if (!proposal.toLowerCase().includes(task.toLowerCase().split(" ")[0])) {
        evaluation.push("⚠️ Proposal may not directly address the task at hand");
    }
    // Check context awareness
    const recentMessages = context.messages.slice(-5);
    const hasContextAwareness = recentMessages.some(msg => proposal.toLowerCase().includes(msg.content.toLowerCase()));
    if (!hasContextAwareness) {
        evaluation.push("⚠️ Proposal may not consider recent conversation context");
    }
    // Check for verification steps
    if (proposal.includes("test") || proposal.includes("verify") || proposal.includes("check")) {
        evaluation.push("✅ Good practice: Includes verification step");
    }
    // Check for iterative approach
    if (proposal.includes("step by step") || proposal.includes("iterative")) {
        evaluation.push("✅ Good practice: Takes iterative approach");
    }
    // Check for specific implementation details
    if (proposal.includes("implement") && !proposal.includes("how")) {
        evaluation.push("⚠️ Proposal lacks implementation details");
    }
    // Check for consideration of existing state
    if (additionalContext.includes("existing") && proposal.includes("create new")) {
        evaluation.push("❌ Consider modifying existing implementation instead of creating new");
    }
    // Compare with previous evaluation if available
    if (context.lastEvaluation) {
        evaluation.push("\n🔄 Progress Check:");
        if (context.lastEvaluation.includes("⚠️") && !evaluation.join("\n").includes("⚠️")) {
            evaluation.push("✅ Previous warnings have been addressed");
        }
    }
    // If no specific feedback generated, provide general guidance
    if (evaluation.length === 0) {
        evaluation.push("✓ Proposal seems reasonable, proceed with caution");
    }
    return evaluation.join("\n");
}
/**
 * Start the server using stdio transport
 */
async function main() {
    const transport = new StdioServerTransport();
    await server.connect(transport);
    console.error("Observer MCP server running on stdio");
}
main().catch((error) => {
    console.error("Server error:", error);
    process.exit(1);
});
