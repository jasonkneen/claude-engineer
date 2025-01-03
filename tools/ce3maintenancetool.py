```python
from tools.base import BaseTool
import os
import shutil
import git
import semver
import subprocess
import json
from datetime import datetime

class Ce3MaintenanceTool(BaseTool):
    name = "ce3maintenancetool"
    description = '''
    Manages the CE3 upgrade and maintenance process.
    Handles backups, branching, testing, versioning and promotion.
    Includes validation and rollback capabilities.
    '''
    input_schema = {
        "type": "object",
        "properties": {
            "version": {
                "type": "string",
                "description": "New version number (SemVer format)"
            },
            "changes": {
                "type": "array",
                "description": "List of changes to apply",
                "items": {
                    "type": "object",
                    "properties": {
                        "file": {"type": "string"},
                        "patch": {"type": "string"}
                    }
                }
            },
            "skip_tests": {
                "type": "boolean",
                "description": "Skip test execution",
                "default": False
            }
        },
        "required": ["version", "changes"]
    }

    def execute(self, **kwargs) -> str:
        results = {
            "status": "started",
            "steps": [],
            "validation": {},
            "tests": {},
            "promotion": None
        }

        try:
            # Validate version
            new_version = semver.VersionInfo.parse(kwargs["version"])
            results["validation"]["version"] = "valid"
            
            # Backup
            backup_path = self._create_backup()
            results["steps"].append({"backup": "success", "path": backup_path})

            # Create branch
            branch_name = f"upgrade/ce3-{kwargs['version']}"
            repo = git.Repo(".")
            new_branch = repo.create_head(branch_name)
            new_branch.checkout()
            results["steps"].append({"branch": "created"})

            # Apply changes
            for change in kwargs["changes"]:
                self._apply_change(change)
            results["steps"].append({"changes": "applied"})

            # Run tests if not skipped
            if not kwargs.get("skip_tests"):
                test_results = self._run_tests()
                results["tests"] = test_results
                if not test_results["success"]:
                    raise Exception("Tests failed")

            # Update version and docs
            self._update_version(str(new_version))
            self._update_docs(kwargs["changes"])
            results["steps"].append({"docs": "updated"})

            # Commit changes
            repo.index.add("*")
            repo.index.commit(f"CE3 Upgrade to {kwargs['version']}")
            results["steps"].append({"commit": "success"})

            results["status"] = "completed"
            results["promotion"] = {
                "branch": branch_name,
                "ready": True
            }

        except Exception as e:
            results["status"] = "failed"
            results["error"] = str(e)
            self._rollback(backup_path)
            results["steps"].append({"rollback": "completed"})

        return json.dumps(results, indent=2)

    def _create_backup(self) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = f"backups/ce3_{timestamp}"
        os.makedirs(backup_dir, exist_ok=True)
        shutil.copy2("ce3.py", backup_dir)
        return backup_dir

    def _apply_change(self, change):
        with open(change["file"], "r") as f:
            content = f.read()
        
        modified = self._apply_patch(content, change["patch"])
        
        with open(change["file"], "w") as f:
            f.write(modified)

    def _apply_patch(self, content: str, patch: str) -> str:
        # Simple patch application - could be enhanced with proper diff/patch
        return content + "\n" + patch

    def _run_tests(self) -> dict:
        result = subprocess.run(["python", "-m", "pytest", "tests/"], 
                              capture_output=True, text=True)
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "errors": result.stderr
        }

    def _update_version(self, version: str):
        with open("ce3.py", "r") as f:
            content = f.read()
        
        content = content.replace("__version__ = ", f"__version__ = '{version}'")
        
        with open("ce3.py", "w") as f:
            f.write(content)

    def _update_docs(self, changes):
        with open("CHANGELOG.md", "a") as f:
            f.write(f"\n## {datetime.now().strftime('%Y-%m-%d')}\n")
            for change in changes:
                f.write(f"- {change['file']}: Applied patch\n")

    def _rollback(self, backup_path: str):
        if os.path.exists(backup_path):
            shutil.copy2(f"{backup_path}/ce3.py", "ce3.py")
```