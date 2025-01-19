from tools.base import BaseTool
from textblob import TextBlob
import spacy
from typing import Dict, Any

class TextAnalyzer(BaseTool):
    @property
    def name(self) -> str:
        return "text_analyzer"
        
    @property
    def description(self) -> str:
        return "Analyzes text for sentiment and complexity"
        
    @property
    def input_schema(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to analyze"
                }
            },
            "required": ["text"]
        }
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        text = params["text"]
        blob = TextBlob(text)
        
        # Sentiment analysis
        sentiment = blob.sentiment.polarity
        
        # Complexity analysis with spaCy
        nlp = spacy.load("en_core_web_sm")
        doc = nlp(text)
        avg_word_length = sum(len(token.text) for token in doc) / len(doc)
        sentence_count = len(list(doc.sents))
        
        return {
            "sentiment": sentiment,
            "complexity": {
                "avg_word_length": avg_word_length,
                "sentence_count": sentence_count,
                "word_count": len(doc)
            },
            "original_text": text
        }
        
class TextFormatter(BaseTool):
    @property
    def name(self) -> str:
        return "text_formatter"
        
    @property
    def description(self) -> str:
        return "Formats text based on analysis"
        
    @property
    def input_schema(self) -> Dict:
        return {
            "type": "object", 
            "properties": {
                "sentiment": {
                    "type": "number",
                    "description": "Sentiment score from -1 to 1"
                },
                "complexity": {
                    "type": "object",
                    "properties": {
                        "avg_word_length": {"type": "number"},
                        "sentence_count": {"type": "number"},
                        "word_count": {"type": "number"}
                    }
                },
                "original_text": {
                    "type": "string",
                    "description": "Original text to format"
                }
            },
            "required": ["sentiment", "complexity", "original_text"]
        }
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        sentiment = params["sentiment"]
        complexity = params["complexity"]
        text = params["original_text"]
        
        # Format based on sentiment
        if sentiment > 0.5:
            text = text.upper() + " 😄"
        elif sentiment < -0.5:
            text = text.lower() + " 😢"
            
        # Add complexity indicators
        stats = (
            f"\nStats:\n"
            f"- Sentiment: {sentiment:.2f}\n"
            f"- Words: {complexity['word_count']}\n"
            f"- Avg word length: {complexity['avg_word_length']:.1f}\n"
            f"- Sentences: {complexity['sentence_count']}"
        )
        
        return {
            "formatted_text": text + stats
        }

