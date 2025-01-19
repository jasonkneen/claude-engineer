import unittest
import subprocess
import sys
from tools.context_interceptor import ContextInterceptor
from typing import Dict, Any

class TokenUsageInterceptor(ContextInterceptor):
    name = "token_usage"
    description = "Monitors and tracks token usage during conversations"
    input_schema = {
        "type": "object",
        "properties": {
            "context": {
                "type": "object",
                "description": "The conversation context to process"
            }
        },
        "required": ["context"]
    }
    def __init__(self):
        super().__init__()
        self.token_limit = 1000
        self.warnings = []
    
    def pre_completion(self, context: Dict[str, Any]) -> Dict[str, Any]:
        # Add token tracking metadata
        context['token_tracking'] = {
            'start_tokens': context.get('total_tokens_used', 0),
            'warnings': []
        }
        return context
        
    def post_completion(self, context: Dict[str, Any]) -> Dict[str, Any]:
        tokens_used = context.get('total_tokens_used', 0)
        
        # Initialize token_tracking if it doesn't exist 
        if 'token_tracking' not in context:
            context['token_tracking'] = {
                'start_tokens': tokens_used,
                'warnings': []
            }
        
        if tokens_used > self.token_limit * 0.8:
            context['token_tracking']['warnings'].append(
                f"Warning: Using {tokens_used}/{self.token_limit} tokens"
            )
        return context
        
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the token usage tracking tool"""
        context = self.pre_completion(context)
        context = self.post_completion(context)
        return context

class TestContextInterceptor(unittest.TestCase):
    def setUp(self):
        self.interceptor = TokenUsageInterceptor()
        self.context = {
            'conversation_history': [
                {'role': 'user', 'content': 'Hello'},
                {'role': 'assistant', 'content': 'Hi there'}
            ],
            'total_tokens_used': 850
        }
        
    def test_pre_completion(self):
        # Test pre-completion hook
        modified = self.interceptor.pre_completion(self.context)
        
        self.assertIn('token_tracking', modified)
        self.assertEqual(modified['token_tracking']['start_tokens'], 850)
        self.assertEqual(modified['token_tracking']['warnings'], [])
        
    def test_post_completion(self):
        # Test post-completion hook
        self.context['total_tokens_used'] = 850
        modified = self.interceptor.post_completion(self.context)
        
        self.assertIn('token_tracking', modified)
        self.assertTrue(any('Warning' in w for w in modified['token_tracking']['warnings']))
        
    def test_full_completion_cycle(self):
        # Simulate full completion cycle
        ctx = self.interceptor.pre_completion(self.context.copy())
        
        # Simulate some token usage
        ctx['total_tokens_used'] += 100
        
        final_ctx = self.interceptor.post_completion(ctx)
        
        self.assertEqual(final_ctx['total_tokens_used'], 950)
        self.assertTrue(any('Warning' in w for w in final_ctx['token_tracking']['warnings']))

        def _startup_check():
            """
            Verify that TokenUsageInterceptor can be instantiated.
            This function runs in a subprocess before the main test suite.
            """
            try:
                interceptor = TokenUsageInterceptor()
                # If we get here, initialization succeeded
                sys.exit(0)
            except Exception as e:
                print(f"TokenUsageInterceptor initialization failed: {e}", file=sys.stderr)
                sys.exit(1)
                
        if __name__ == '__main__':
            if len(sys.argv) > 1 and sys.argv[1] == '--startup-check':
                _startup_check()
            else:
                # Run startup check in subprocess
                process = subprocess.run([sys.executable, __file__, '--startup-check'],
                                    capture_output=True)
                if process.returncode != 0:
                    sys.stderr.write(process.stderr.decode())
                    sys.exit(1)
                
                # If startup check passed, run the main test suite
                unittest.main()
