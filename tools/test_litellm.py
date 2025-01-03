from litellmtool import LiteLLMTool, PromptType

def test_litellm():
    llm = LiteLLMTool()
    
    # Get model info
    print('\nGetting model information...')
    model_info = llm.get_model_info()
    print(f'Available models: {model_info}')
    
    # Test different specialized prompts
    test_cases = [
        (
            'brainstorm',
            'How can we improve code documentation practices in a development team?',
            'llama2'
        ),
        (
            'code_review',
            '''
            def calculate_total(items):
                total = 0
                for item in items:
                    total += item['price']
                return total
            ''',
            'codellama'
        ),
        (
            'debug',
            'My Python script is running slowly when processing large files. How can I debug and improve performance?',
            'codellama'
        ),
        (
            'explain',
            'What are coroutines in Python and how do they work?',
            'mistral'
        )
    ]
    
    for test_type, prompt, model in test_cases:
        print(f'\nTesting {test_type.upper()} prompt with {model}...')
        response = llm.execute(
            prompt=prompt,
            model=model,
            prompt_type=test_type
        )
        
        print(f'Response: {response}')

if __name__ == '__main__':
    test_litellm()