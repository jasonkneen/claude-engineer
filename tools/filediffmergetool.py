from tools.base import BaseTool
import difflib
import os
import json
from typing import Dict, List, Tuple
import ast
import re

class FileDiffMergeTool(BaseTool):
    name = "filediffmergetool"
    description = '''
    Intelligent file comparison and merge tool that performs comprehensive diff analysis
    and provides AI-powered merge capabilities.
    Supports multiple file formats and provides various levels of difference analysis
    including line-by-line, character-level, structural, and semantic differences.
    Features intelligent conflict resolution and bidirectional change application.
    '''
    input_schema = {
        "type": "object",
        "properties": {
            "file_a": {"type": "string", "description": "Path to first file"},
            "file_b": {"type": "string", "description": "Path to second file"},
            "operation": {
                "type": "string",
                "enum": ["diff", "merge", "patch", "preview"],
                "description": "Operation to perform"
            },
            "format": {
                "type": "string",
                "enum": ["raw", "summary", "semantic", "impact"],
                "description": "Output format desired"
            },
            "direction": {
                "type": "string",
                "enum": ["a_to_b", "b_to_a"],
                "description": "Direction for applying changes"
            }
        },
        "required": ["file_a", "file_b", "operation"]
    }

    def execute(self, **kwargs) -> str:
        file_a = kwargs.get("file_a")
        file_b = kwargs.get("file_b")
        operation = kwargs.get("operation")
        format_type = kwargs.get("format", "raw")
        direction = kwargs.get("direction", "a_to_b")

        if not os.path.exists(file_a) or not os.path.exists(file_b):
            return "Error: One or both files do not exist"

        try:
            with open(file_a, 'r') as f:
                content_a = f.readlines()
            with open(file_b, 'r') as f:
                content_b = f.readlines()

            if operation == "diff":
                return self._perform_diff(content_a, content_b, format_type)
            elif operation == "merge":
                return self._perform_merge(content_a, content_b, direction)
            elif operation == "patch":
                return self._generate_patch(content_a, content_b, direction)
            elif operation == "preview":
                return self._preview_changes(content_a, content_b, direction)
            else:
                return "Error: Invalid operation specified"

        except Exception as e:
            return f"Error processing files: {str(e)}"

    def _perform_diff(self, content_a: List[str], content_b: List[str], format_type: str) -> str:
        differ = difflib.Differ()
        diff = list(differ.compare(content_a, content_b))
        
        if format_type == "raw":
            return "".join(diff)
        elif format_type == "summary":
            return self._generate_diff_summary(diff)
        elif format_type == "semantic":
            return self._analyze_semantic_changes(content_a, content_b)
        elif format_type == "impact":
            return self._assess_impact(diff)
        return "Error: Invalid format type"

    def _perform_merge(self, content_a: List[str], content_b: List[str], direction: str) -> str:
        conflicts = self._detect_conflicts(content_a, content_b)
        if conflicts:
            resolved = self._resolve_conflicts(conflicts)
            return self._apply_merge(content_a, content_b, resolved, direction)
        return self._apply_direct_merge(content_a, content_b, direction)

    def _generate_patch(self, content_a: List[str], content_b: List[str], direction: str) -> str:
        differ = difflib.unified_diff(content_a, content_b)
        return "".join(differ)

    def _preview_changes(self, content_a: List[str], content_b: List[str], direction: str) -> str:
        changes = self._detect_changes(content_a, content_b)
        return json.dumps(changes, indent=2)

    def _detect_conflicts(self, content_a: List[str], content_b: List[str]) -> List[Dict]:
        matcher = difflib.SequenceMatcher(None, content_a, content_b)
        conflicts = []
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'replace':
                conflicts.append({
                    'type': 'conflict',
                    'a_start': i1,
                    'a_end': i2,
                    'b_start': j1,
                    'b_end': j2,
                    'a_content': content_a[i1:i2],
                    'b_content': content_b[j1:j2]
                })
        return conflicts

    def _resolve_conflicts(self, conflicts: List[Dict]) -> List[Dict]:
        resolved = []
        for conflict in conflicts:
            resolution = self._ai_resolve_conflict(
                conflict['a_content'],
                conflict['b_content']
            )
            resolved.append({
                'original': conflict,
                'resolution': resolution
            })
        return resolved

    def _ai_resolve_conflict(self, content_a: List[str], content_b: List[str]) -> str:
        # Simplified AI resolution logic
        # In real implementation, this would use more sophisticated AI analysis
        combined = []
        for line_a, line_b in zip(content_a, content_b):
            if line_a.strip() == line_b.strip():
                combined.append(line_a)
            else:
                # Choose the more complex/longer version as it likely contains more information
                combined.append(line_a if len(line_a) > len(line_b) else line_b)
        return combined

    def _analyze_semantic_changes(self, content_a: List[str], content_b: List[str]) -> str:
        # Simplified semantic analysis
        # Would use more sophisticated NLP/AI in real implementation
        changes = {
            'additions': [],
            'deletions': [],
            'modifications': []
        }
        
        for i, (line_a, line_b) in enumerate(zip(content_a, content_b)):
            if line_a != line_b:
                if not line_a.strip():
                    changes['additions'].append(f"Line {i}: Added {line_b.strip()}")
                elif not line_b.strip():
                    changes['deletions'].append(f"Line {i}: Removed {line_a.strip()}")
                else:
                    changes['modifications'].append(f"Line {i}: Changed from '{line_a.strip()}' to '{line_b.strip()}'")
        
        return json.dumps(changes, indent=2)

    def _assess_impact(self, diff: List[str]) -> str:
        impact = {
            'high_impact_changes': [],
            'medium_impact_changes': [],
            'low_impact_changes': []
        }
        
        for line in diff:
            if line.startswith('- ') or line.startswith('+ '):
                # Simplified impact assessment
                # Would use more sophisticated analysis in real implementation
                if re.search(r'(class|def|import)', line):
                    impact['high_impact_changes'].append(line)
                elif re.search(r'(if|for|while|return)', line):
                    impact['medium_impact_changes'].append(line)
                else:
                    impact['low_impact_changes'].append(line)
        
        return json.dumps(impact, indent=2)

    def _generate_diff_summary(self, diff: List[str]) -> str:
        summary = {
            'additions': len([l for l in diff if l.startswith('+ ')]),
            'deletions': len([l for l in diff if l.startswith('- ')]),
            'changes': len([l for l in diff if l.startswith('? ')]),
            'unchanged': len([l for l in diff if l.startswith('  ')])
        }
        return json.dumps(summary, indent=2)

    def _detect_changes(self, content_a: List[str], content_b: List[str]) -> Dict:
        matcher = difflib.SequenceMatcher(None, content_a, content_b)
        changes = []
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag != 'equal':
                changes.append({
                    'type': tag,
                    'a_start': i1,
                    'a_end': i2,
                    'b_start': j1,
                    'b_end': j2,
                    'a_content': content_a[i1:i2],
                    'b_content': content_b[j1:j2]
                })
        return {'changes': changes}

    def _apply_direct_merge(self, content_a: List[str], content_b: List[str], direction: str) -> str:
        if direction == 'a_to_b':
            return ''.join(content_a)
        return ''.join(content_b)

    def _apply_merge(self, content_a: List[str], content_b: List[str], resolved: List[Dict], direction: str) -> str:
        result = []
        current_pos = 0
        
        for resolution in resolved:
            conflict = resolution['original']
            # Add content up to conflict
            if direction == 'a_to_b':
                result.extend(content_a[current_pos:conflict['a_start']])
            else:
                result.extend(content_b[current_pos:conflict['b_start']])
            
            # Add resolved content
            result.extend(resolution['resolution'])
            
            # Update position
            current_pos = conflict['a_end'] if direction == 'a_to_b' else conflict['b_end']
        
        # Add remaining content
        if direction == 'a_to_b':
            result.extend(content_a[current_pos:])
        else:
            result.extend(content_b[current_pos:])
        
        return ''.join(result)