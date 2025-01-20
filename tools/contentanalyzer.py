from tools.base import BaseTool
from datetime import datetime
import re
from typing import Dict, List, Any

class ContentAnalyzer(BaseTool):
    name = "contentanalyzer"
    description = '''
    Analyzes content (text, code, or images) and generates structured summaries.
    Provides organized analysis with main points, technical details, and action items.
    Supports multiple output formats and content type detection.
    Includes metadata and contextual information in analysis results.
    '''
    input_schema = {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "Content to analyze (text, code, or base64 image)"
            },
            "format": {
                "type": "string",
                "enum": ["bullet", "numbered", "sections"],
                "description": "Desired output format"
            },
            "template": {
                "type": "string",
                "enum": ["technical", "summary", "detailed"],
                "description": "Analysis template to use"
            }
        },
        "required": ["content"]
    }

    def execute(self, **kwargs) -> str:
        content = kwargs.get("content")
        output_format = kwargs.get("format", "sections")
        template = kwargs.get("template", "technical")

        analysis = self._analyze_content(content)
        formatted_result = self._format_analysis(analysis, output_format, template)
        
        return formatted_result

    def _analyze_content(self, content: str) -> Dict[str, Any]:
        content_type = self._detect_content_type(content)
        
        analysis = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "content_type": content_type,
                "length": len(content)
            },
            "main_points": self._extract_main_points(content, content_type),
            "technical_details": self._extract_technical_details(content, content_type),
            "action_items": self._identify_action_items(content),
            "context": self._extract_context(content)
        }
        
        return analysis

    def _detect_content_type(self, content: str) -> str:
        if content.startswith(("```", "    ")):
            return "code"
        elif any(pattern in content.lower() for pattern in ["error:", "warning:", "debug:"]):
            return "logs"
        elif "<" in content and ">" in content and ("div" in content or "span" in content):
            return "markup"
        else:
            return "text"

    def _extract_main_points(self, content: str, content_type: str) -> List[str]:
        points = []
        if content_type == "code":
            points = self._analyze_code_structure(content)
        elif content_type == "logs":
            points = self._analyze_log_patterns(content)
        else:
            sentences = content.split(". ")
            points = [s.strip() for s in sentences if len(s.split()) > 5][:5]
        return points

    def _extract_technical_details(self, content: str, content_type: str) -> Dict[str, Any]:
        details = {}
        if content_type == "code":
            details["language"] = self._detect_language(content)
            details["functions"] = len(re.findall(r"def\s+\w+", content))
            details["classes"] = len(re.findall(r"class\s+\w+", content))
        elif content_type == "logs":
            details["error_count"] = len(re.findall(r"error:", content, re.IGNORECASE))
            details["warning_count"] = len(re.findall(r"warning:", content, re.IGNORECASE))
        return details

    def _identify_action_items(self, content: str) -> List[str]:
        action_keywords = ["todo", "fix", "implement", "update", "change"]
        actions = []
        for line in content.lower().split("\n"):
            if any(keyword in line for keyword in action_keywords):
                actions.append(line.strip())
        return actions

    def _extract_context(self, content: str) -> Dict[str, Any]:
        return {
            "references": self._find_references(content),
            "dependencies": self._find_dependencies(content)
        }

    def _format_analysis(self, analysis: Dict[str, Any], output_format: str, template: str) -> str:
        if output_format == "bullet":
            return self._format_bullet_points(analysis, template)
        elif output_format == "numbered":
            return self._format_numbered_list(analysis, template)
        else:
            return self._format_sections(analysis, template)

    def _format_sections(self, analysis: Dict[str, Any], template: str) -> str:
        sections = []
        sections.append(f"Content Analysis Report ({analysis['metadata']['timestamp']})")
        sections.append(f"\nContent Type: {analysis['metadata']['content_type']}")
        
        sections.append("\nMain Points:")
        for point in analysis['main_points']:
            sections.append(f"- {point}")
        
        sections.append("\nTechnical Details:")
        for key, value in analysis['technical_details'].items():
            sections.append(f"- {key}: {value}")
        
        if analysis['action_items']:
            sections.append("\nAction Items:")
            for item in analysis['action_items']:
                sections.append(f"- {item}")
        
        return "\n".join(sections)

    def _format_bullet_points(self, analysis: Dict[str, Any], template: str) -> str:
        return self._format_sections(analysis, template).replace("\n-", "\n•")

    def _format_numbered_list(self, analysis: Dict[str, Any], template: str) -> str:
        sections = self._format_sections(analysis, template).split("\n")
        numbered = []
        count = 1
        for line in sections:
            if line.startswith("-"):
                numbered.append(f"{count}. {line[2:]}")
                count += 1
            else:
                numbered.append(line)
        return "\n".join(numbered)

    def _analyze_code_structure(self, content: str) -> List[str]:
        return [line.strip() for line in content.split("\n") 
                if line.strip().startswith(("def ", "class ", "import ", "from "))][:5]

    def _analyze_log_patterns(self, content: str) -> List[str]:
        return [line.strip() for line in content.split("\n") 
                if any(level in line.lower() for level in ["error:", "warning:", "critical:"])][:5]

    def _detect_language(self, content: str) -> str:
        if "def " in content and "import " in content:
            return "Python"
        elif "{" in content and "function" in content:
            return "JavaScript"
        elif "public class" in content:
            return "Java"
        return "Unknown"

    def _find_references(self, content: str) -> List[str]:
        urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', content)
        return urls

    def _find_dependencies(self, content: str) -> List[str]:
        deps = []
        if "import " in content:
            deps.extend(re.findall(r'import\s+(\w+)', content))
        if "require(" in content:
            deps.extend(re.findall(r'require\([\'"](.+?)[\'"]\)', content))
        return deps