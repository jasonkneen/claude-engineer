from tools.text_processor import TextAnalyzer, TextFormatter
from rich import print
from rich.panel import Panel
from typing import Dict, Any

# Example 1: Basic tool chain
def test_basic_chain():
    print(Panel.fit("Test 1: Basic Tool Chain"))
    text = "I absolutely love this new feature! It's amazing and innovative."
    
    analyzer = TextAnalyzer()
    formatter = TextFormatter()
    
    # Chain the tools manually
    analysis = analyzer.execute({"text": text})
    result = formatter.execute(analysis)
    
    print("Input:", text)
    print("Analysis:", analysis)
    print("Formatted:", result)

# Example 2: Natural language chain creation
def test_natural_language_chain():
    print(Panel.fit("Test 2: Natural Language Chain"))
    commands = [
        "analyze the text and then format it",
        "first analyze sentiment then apply formatting",
        "use text analyzer followed by formatter"
    ]
    
    text = "This product has some good features but needs improvement."
    
    for cmd in commands:
        print(f"\nCommand: {cmd}")
        # In practice, this would be handled by ce3-2d's chain manager
        analyzed = TextAnalyzer().execute({"text": text})
        formatted = TextFormatter().execute(analyzed)
        print(f"Result: {formatted}")

# Example 3: Chain with intermediate results
def test_chain_with_results():
    print(Panel.fit("Test 3: Chain with Intermediate Results"))
    text = "The new interface is clean and intuitive, though some options are hard to find."
    
    print("\nStep 1: Text Analysis")
    analysis = TextAnalyzer().execute({"text": text})
    print("Sentiment Score:", analysis["sentiment"])
    print("Complexity Score:", analysis["complexity"])
    
    print("\nStep 2: Text Formatting")
    result = TextFormatter().execute(analysis)
    print("Final Output:", result)

if __name__ == "__main__":
    print(Panel.fit("[bold]Text Processing Chain Demonstration[/bold]"))
    
    test_basic_chain()
    print("\n")
    test_natural_language_chain()
    print("\n")
    test_chain_with_results()

    print("""
Example commands for ce3-2d:
- "analyze this text: 'Hello world' then format the results"
- "use analyzer and formatter on 'Great product, highly recommend!'"
- "create chain: text_analyzer -> text_formatter"
""")

