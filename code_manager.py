import os
import shutil
import subprocess
import hashlib
import logging
import asyncio
import git
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

class ModificationLog:
    def __init__(self, log_file: str = "code_modifications.log"):
        self.log_file = log_file
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
    def log_modification(self, action: str, details: str, success: bool):
        status = "SUCCESS" if success else "FAILED"
        logging.info(f"{action} - {status} - {details}")
        
    def log_error(self, action: str, error: Exception):
        logging.error(f"{action} - ERROR: {str(error)}")

class SafetyChecks:
    @staticmethod
    def calculate_checksum(file_path: str) -> str:
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
        
    @staticmethod
    async def run_tests(file_path: str) -> bool:
        try:
            # Run pytest in subprocess
            result = subprocess.run(
                ['python', '-m', 'pytest', file_path],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception as e:
            logging.error(f"Test execution failed: {str(e)}")
            return False
        
    @staticmethod
    def verify_syntax(file_path: str) -> bool:
        try:
            with open(file_path, 'r') as f:
                compile(f.read(), file_path, 'exec')
            return True
        except SyntaxError:
            return False

class VersionControl:
    def __init__(self, repo_path: str = '.'):
        self.repo = git.Repo(repo_path)
        
    def create_branch(self, branch_name: str):
        current = self.repo.active_branch
        new_branch = self.repo.create_head(branch_name)
        new_branch.checkout()
        return current
        
    def commit_changes(self, files: List[str], message: str):
        self.repo.index.add(files)
        self.repo.index.commit(message)
        
    def push_changes(self, branch_name: str):
        self.repo.remotes.origin.push(branch_name)
        
    def is_tracked(self, file_path: str) -> bool:
        """Check if a file is tracked by git"""
        relative_path = os.path.relpath(file_path, self.repo.working_tree_dir)
        return relative_path not in self.repo.untracked_files
        
    def add_file(self, file_path: str) -> None:
        """Add a single file to git tracking"""
        self.repo.index.add([file_path])
        
    def rollback_to_commit(self, commit_hash: str):
        self.repo.git.reset('--hard', commit_hash)

class CodeManager:
    def __init__(self, target_file: str):
        self.target_file = target_file
        self.logger = ModificationLog()
        self.safety = SafetyChecks()
        self.version_control = VersionControl()
        
    def _lock_file(self):
        os.chmod(self.target_file, 0o555)  # read and execute only
        
    def _unlock_file(self):
        os.chmod(self.target_file, 0o644)  # read and write
        
    def _create_temp_copy(self) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_file = f"{self.target_file}_{timestamp}_temp.py"
        shutil.copy2(self.target_file, temp_file)
        return temp_file
        
    def _create_backup(self) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"{self.target_file}_{timestamp}_backup.py"
        shutil.copy2(self.target_file, backup_file)
        return backup_file
        
    async def modify_code(self, modifications: List[Dict[str, str]]) -> bool:
        """
        Safely modify the target file with the given modifications.
        
        Args:
            modifications: List of dicts containing 'search' and 'replace' pairs
        """
        temp_file = self._create_temp_copy()
        backup_file = self._create_backup()
        branch_name = f"modification_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            # Create new branch for modifications
            original_branch = self.version_control.create_branch(branch_name)
            
            # Apply modifications to temp file
            with open(temp_file, 'r') as f:
                content = f.read()
                
            for mod in modifications:
                content = content.replace(mod['search'], mod['replace'])
                
            with open(temp_file, 'w') as f:
                f.write(content)
                
            # Verify syntax
            if not self.safety.verify_syntax(temp_file):
                raise SyntaxError("Modified code contains syntax errors")
                
            # Run tests
            if not await self.safety.run_tests(temp_file):
                raise Exception("Tests failed for modified code")
                
            # Calculate checksums
            original_checksum = self.safety.calculate_checksum(self.target_file)
                
            # Perform the actual modification
            self._unlock_file()
            shutil.copy2(temp_file, self.target_file)
            self._lock_file()
            
            # Verify checksum changed
            new_checksum = self.safety.calculate_checksum(self.target_file)
            if original_checksum == new_checksum:
                raise Exception("File was not modified")
                
            # Commit and push changes
            self.version_control.commit_changes(
                [self.target_file],
                f"Code modification {datetime.now().isoformat()}"
            )
            self.version_control.push_changes(branch_name)
            
            self.logger.log_modification(
                "CODE_MODIFICATION",
                f"Successfully modified {self.target_file}",
                True
            )
            
            # Cleanup
            os.remove(temp_file)
            return True
            
        except Exception as e:
            # Rollback
            self._unlock_file()
            shutil.copy2(backup_file, self.target_file)
            self._lock_file()
            
            self.logger.log_error("CODE_MODIFICATION", e)
            return False
            
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

