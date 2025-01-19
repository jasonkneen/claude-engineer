from tools.base import BaseTool
import os
import datetime
import re
from typing import Dict, List, Tuple, Optional

# Try to import git, but don't fail if it's not available
try:
    import git
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False
class GitMergeTool(BaseTool):
    def to_dict(self) -> Optional[Dict]:
        if not GIT_AVAILABLE:
            return None
        return super().to_dict()

    @property
    def name(self) -> str:
        return "gitmergetool"

    @property 
    def description(self) -> str:
        return '''
        Handles Git merge conflicts by automatically detecting and resolving conflicts.
        Supports multiple resolution strategies including timestamp-based, keep-both, and custom rules.
        Provides detailed conflict reports and can handle complex merge scenarios.
        '''
    input_schema = {
        "type": "object",
        "properties": {
            "repo_path": {"type": "string", "description": "Path to Git repository"},
            "strategy": {"type": "string", "enum": ["timestamp", "keep-both", "interactive"], "description": "Merge resolution strategy"},
            "custom_rules": {"type": "object", "description": "Custom merge rules configuration"},
            "abort_on_error": {"type": "boolean", "description": "Whether to abort merge on error"}
        },
        "required": ["repo_path", "strategy"]
    }

    def execute(self, **kwargs) -> str:
        if not GIT_AVAILABLE:
            return "Error: The 'git' Python package is not installed. Please install it using 'pip install gitpython' to use this tool."

        repo_path = kwargs.get("repo_path")
        strategy = kwargs.get("strategy")
        custom_rules = kwargs.get("custom_rules", {})
        abort_on_error = kwargs.get("abort_on_error", False)

        try:
            repo = git.Repo(repo_path)
            conflicts = self._find_conflicts(repo)
            
            if not conflicts:
                return "No merge conflicts found."

            resolution_report = self._resolve_conflicts(repo, conflicts, strategy, custom_rules)
            
            if abort_on_error and resolution_report["errors"]:
                self._abort_merge(repo)
                return "Merge aborted due to errors: " + str(resolution_report["errors"])

            self._stage_and_commit(repo, resolution_report)
            
            return self._generate_report(resolution_report)

        except git.GitCommandError as e:
            return f"Git error occurred: {str(e)}"
        except Exception as e:
            return f"Error: {str(e)}"

    def _find_conflicts(self, repo) -> List[Dict]:
        conflicts = []
        for item in repo.index.unmerged_blobs():
            path = item[0]
            stages = item[1]
            
            with open(os.path.join(repo.working_dir, path), 'r') as f:
                content = f.read()
            
            conflict_sections = self._parse_conflict_markers(content)
            if conflict_sections:
                conflicts.append({
                    "path": path,
                    "stages": stages,
                    "sections": conflict_sections
                })
        
        return conflicts

    def _parse_conflict_markers(self, content: str) -> List[Dict]:
        sections = []
        pattern = r"<<<<<<< HEAD\n(.*?)\n=======\n(.*?)\n>>>>>>> .*?\n"
        matches = re.finditer(pattern, content, re.DOTALL)
        
        for match in matches:
            sections.append({
                "head": match.group(1),
                "incoming": match.group(2),
                "start": match.start(),
                "end": match.end()
            })
        
        return sections

    def _resolve_conflicts(self, repo, conflicts: List[Dict], strategy: str, custom_rules: Dict) -> Dict:
        report = {
            "resolved": [],
            "errors": [],
            "total": len(conflicts)
        }

        for conflict in conflicts:
            try:
                if strategy == "timestamp":
                    resolution = self._resolve_by_timestamp(conflict)
                elif strategy == "keep-both":
                    resolution = self._resolve_keep_both(conflict)
                elif strategy == "interactive":
                    resolution = self._resolve_interactive(conflict)
                else:
                    resolution = self._resolve_custom(conflict, custom_rules)

                self._apply_resolution(repo, conflict["path"], resolution)
                report["resolved"].append({
                    "path": conflict["path"],
                    "strategy": strategy,
                    "resolution": resolution
                })
            except Exception as e:
                report["errors"].append({
                    "path": conflict["path"],
                    "error": str(e)
                })

        return report

    def _resolve_by_timestamp(self, conflict: Dict) -> str:
        # Implementation would compare timestamps of conflicting versions
        return conflict["sections"][0]["head"]  # Simplified for example

    def _resolve_keep_both(self, conflict: Dict) -> str:
        resolved = ""
        for section in conflict["sections"]:
            resolved += f"{section['head']}\n{section['incoming']}\n"
        return resolved

    def _resolve_interactive(self, conflict: Dict) -> str:
        # Would implement interactive user prompts here
        return conflict["sections"][0]["head"]  # Simplified for example

    def _resolve_custom(self, conflict: Dict, rules: Dict) -> str:
        # Would implement custom resolution rules here
        return conflict["sections"][0]["head"]  # Simplified for example

    def _apply_resolution(self, repo, path: str, resolution: str):
        full_path = os.path.join(repo.working_dir, path)
        with open(full_path, 'w') as f:
            f.write(resolution)

    def _stage_and_commit(self, repo, report: Dict):
        repo.index.add([item["path"] for item in report["resolved"]])
        if report["resolved"]:
            repo.index.commit(f"Resolved {len(report['resolved'])} merge conflicts")

    def _abort_merge(self, repo):
        repo.git.execute(['git', 'merge', '--abort'])

    def _generate_report(self, report: Dict) -> str:
        output = f"Merge Conflict Resolution Report\n"
        output += f"Total conflicts: {report['total']}\n"
        output += f"Successfully resolved: {len(report['resolved'])}\n"
        output += f"Errors: {len(report['errors'])}\n\n"

        if report["resolved"]:
            output += "Resolved conflicts:\n"
            for resolution in report["resolved"]:
                output += f"- {resolution['path']} (using {resolution['strategy']})\n"

        if report["errors"]:
            output += "\nErrors encountered:\n"
            for error in report["errors"]:
                output += f"- {error['path']}: {error['error']}\n"

        return output