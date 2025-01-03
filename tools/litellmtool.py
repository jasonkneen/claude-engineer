from tools.base import BaseTool
from typing import Dict, List, Optional, Union, Literal
from dataclasses import dataclass
from enum import Enum
import litellm

@dataclass
class LLMResponse:
    content: str
    status: str
    usage: Dict[str, int]
    error: Optional[str] = None

class PromptType(Enum):
    BRAINSTORM = 'brainstorm'
    CODE_REVIEW = 'code_review'
    ARCHITECTURE = 'architecture'
    DEBUG = 'debug'
    REFACTOR = 'refactor'
    EXPLAIN = 'explain'
    IMPROVE = 'improve'

class LiteLLMTool(BaseTool):
    name = "litellmtool"
    description = '''
    A tool for interacting with local LLMs using LiteLLM.
    Supports multiple model providers and local models with Apple Silicon GPU acceleration.
    Features:
    - Specialized prompt templates for different tasks
    - GPU acceleration on Apple Silicon
    - Multiple model support
    - Structured responses
    - Error handling and retries
    '''
    input_schema = {
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "description": "The prompt to send to the model"},
            "prompt_type": {"type": "string", "enum": ["brainstorm", "code_review", "architecture", "debug", "refactor", "explain", "improve"]},
            "model": {"type": "string", "description": "Model to use (e.g., llama2, codellama, mistral)"},
            "context": {"type": "string", "description": "Additional context for the prompt"},
            "temperature": {"type": "number", "minimum": 0, "maximum": 2}
        },
        "required": ["prompt", "model"]
    }

    def __init__(self):
        # Configure litellm for local models
        litellm.set_verbose = True
        
        # System prompts for different tasks
        self.system_prompts = {
            PromptType.BRAINSTORM: """
            You are a creative problem-solving assistant. Help brainstorm ideas, solutions, and approaches.
            Consider multiple perspectives and generate diverse options. Focus on:
            - Different possible approaches
            - Pros and cons of each option
            - Creative and unconventional solutions
            - Practical considerations
            Structure your response with clear sections and bullet points.
            """,
            
            PromptType.CODE_REVIEW: """
            You are an expert code reviewer. Analyze code for:
            - Potential bugs and issues
            - Performance optimizations
            - Best practices and patterns
            - Security concerns
            - Readability and maintainability
            Provide specific suggestions for improvements with example code when relevant.
            """,
            
            PromptType.ARCHITECTURE: """
            You are a software architecture expert. Help design and evaluate system architectures focusing on:
            - Component relationships
            - Data flow and storage
            - Scalability considerations
            - Security implications
            - Integration points
            Provide clear diagrams descriptions and explain trade-offs.
            """,
            
            PromptType.DEBUG: """
            You are a debugging expert. Help analyze and fix issues by:
            - Breaking down the problem
            - Identifying potential root causes
            - Suggesting debugging approaches
            - Recommending solutions
            - Preventing similar issues
            Provide step-by-step guidance and example scenarios.
            """,
            
            PromptType.REFACTOR: """
            You are a code refactoring specialist. Help improve code quality by:
            - Identifying refactoring opportunities
            - Suggesting design patterns
            - Improving code structure
            - Enhancing maintainability
            Provide before/after examples and explain benefits.
            """,
            
            PromptType.EXPLAIN: """
            You are an expert teacher. Help explain complex concepts by:
            - Breaking down difficult topics
            - Using clear analogies
            - Providing examples
            - Building understanding step-by-step
            Focus on clarity and comprehension.
            """,
            
            PromptType.IMPROVE: """
            You are an optimization expert. Help improve existing solutions by:
            - Identifying enhancement opportunities
            - Suggesting optimizations
            - Recommending best practices
            - Considering edge cases
            Provide specific, actionable improvements.
            """
        }

    def execute(self, **kwargs) -> str:
        try:
            prompt = kwargs.get("prompt")
            model = kwargs.get("model")
            prompt_type = kwargs.get("prompt_type")
            context = kwargs.get("context")
            temperature = kwargs.get("temperature", 0.7)

            if prompt_type:
                return self._specialized_ask(
                    PromptType[prompt_type.upper()],
                    prompt,
                    model,
                    context,
                    temperature
                )
            else:
                return self._ask(
                    prompt,
                    model,
                    system_prompt=None,
                    temperature=temperature
                )

        except Exception as e:
            return f"Error executing LiteLLM request: {str(e)}"

    def _specialized_ask(self,
                       prompt_type: PromptType,
                       content: str,
                       model: str,
                       additional_context: Optional[str] = None,
                       temperature: float = 0.7) -> str:
        """Ask a specialized question using predefined system prompts"""
        
        system_prompt = self.system_prompts[prompt_type]
        if additional_context:
            system_prompt = f"{system_prompt}\n\nAdditional context: {additional_context}"
            
        return self._ask(content, model, system_prompt, temperature)

    def _ask(self,
            prompt: str,
            model: str,
            system_prompt: Optional[str] = None,
            temperature: float = 0.7) -> str:
        """Send a request to the model and get a response"""
        
        try:
            # Prepare messages
            messages = []
            if system_prompt:
                messages.append({
                    'role': 'system',
                    'content': system_prompt
                })
            messages.append({
                'role': 'user',
                'content': prompt
            })

            # Make API call using litellm
            response = litellm.completion(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=2000
            )

            # Extract and return the response
            if response and response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content
                usage = response.usage._asdict() if response.usage else {}
                
                return LLMResponse(
                    content=content,
                    status='success',
                    usage=usage
                ).__dict__
            else:
                return LLMResponse(
                    content='',
                    status='error',
                    usage={},
                    error='No response generated'
                ).__dict__

        except Exception as e:
            return LLMResponse(
                content='',
                status='error',
                usage={},
                error=f'Error: {str(e)}'
            ).__dict__

    def get_model_info(self) -> Dict:
        """Get information about available models"""
        try:
            # This would list available local models
            # Note: Implementation depends on how you're managing local models
            return {
                "available_models": [
                    "llama2",
                    "codellama",
                    "mistral",
                    # Add other available models
                ],
                "default_model": "llama2"
            }
        except Exception as e:
            return {"error": f"Error getting model info: {str(e)}"}
