import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from anthropic import AsyncAnthropic, HUMAN_PROMPT, AI_PROMPT

from config import Config


class ContextManager:
    """Manages context data capture, AI summarization, and storage."""
    
    def __init__(self):
        self.context_dir = Config.CONTEXT_DIR
        self.archive_dir = Config.CONTEXT_ARCHIVE_DIR
        self.client = AsyncAnthropic(api_key=Config.ANTHROPIC_API_KEY)
        self._ensure_directories()
        
    def _ensure_directories(self):
        """Ensures required directories exist and are hidden."""
        for directory in [self.context_dir, self.archive_dir]:
            if not directory.exists():
                directory.mkdir(parents=True)
        
        # Update .gitignore to hide context directories
        gitignore_path = Config.BASE_DIR / '.gitignore'
        entries = {'.context/', '.context_archive/'}
        
        if gitignore_path.exists():
            with open(gitignore_path, 'r') as f:
                current = set(f.read().splitlines())
            entries.update(current)
        
        with open(gitignore_path, 'w') as f:
            f.write('\n'.join(sorted(entries)) + '\n')
    
    async def generate_summary(self, context: str) -> str:
        """Generates an AI summary of the context using Claude."""
        try:
            message = await self.client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=Config.CONTEXT_SUMMARY_MAX_TOKENS,
                temperature=Config.CONTEXT_SUMMARY_TEMPERATURE,
                messages=[{
                    "role": "user",
                    "content": Config.CONTEXT_SUMMARY_PROMPT.format(context=context)
                }]
            )
            if message and hasattr(message, 'content'):
                return message.content[0].text
            return ""
        except Exception as e:
            print(f"Error generating summary: {e}")
            return ""

    def cleanup_old_contexts(self) -> None:
        """Archives old context entries when threshold is reached."""
        if not Config.CONTEXT_ARCHIVE_ENABLED:
            return
            
        context_files = sorted(self.context_dir.glob('context_*.json'))
        if len(context_files) >= Config.CONTEXT_CLEANUP_THRESHOLD:
            # Move oldest files to archive
            files_to_archive = context_files[:-Config.MAX_CONTEXT_ENTRIES]
            for file_path in files_to_archive:
                archive_path = self.archive_dir / file_path.name
                shutil.move(str(file_path), str(archive_path))

    async def capture_context(self, context_data: str) -> Dict:
        """
        Captures and stores context data with optional summary.
        
        Args:
            context_data: The full context to store
            summary: Optional AI-generated summary of the context
            
        Returns:
            Dict containing the stored context metadata
        """
        # Check if context meets minimum size requirement
        if len(context_data) < Config.MIN_CONTEXT_SIZE_FOR_SUMMARY:
            return {}
            
        timestamp = datetime.utcnow().isoformat()
        
        # Generate AI summary
        summary = await self.generate_summary(context_data)
        
        context_entry = {
            'timestamp': timestamp,
            'summary': summary,
            'full_context': context_data,
            'tokens_used': len(context_data.split())
        }
        
        # Store context
        filename = f'context_{timestamp}.json'
        filepath = self.context_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(context_entry, f, indent=2)
        
        # Cleanup old contexts if needed
        self.cleanup_old_contexts()
        
        return context_entry
    
    def get_latest_context(self, include_full: bool = False) -> Optional[Dict]:
        """Retrieves the most recent context entry."""
        try:
            context_files = sorted(self.context_dir.glob('context_*.json'))
            if not context_files:
                return None
                
            latest_file = context_files[-1]
            with open(latest_file) as f:
                data = json.load(f)
                if not include_full:
                    data.pop('full_context', None)
                return data
        except Exception:
            return None
    
    def get_all_summaries(self, include_archived: bool = False) -> List[Dict]:
        """Retrieves all context summaries ordered by timestamp."""
        summaries = []
        try:
            # Get current summaries
            for context_file in sorted(self.context_dir.glob('context_*.json')):
                with open(context_file) as f:
                    data = json.load(f)
                    if data.get('summary'):
                        summaries.append({
                            'timestamp': data['timestamp'],
                            'summary': data['summary']
                        })
            
            # Get archived summaries if requested
            if include_archived and Config.CONTEXT_ARCHIVE_ENABLED:
                for context_file in sorted(self.archive_dir.glob('context_*.json')):
                    with open(context_file) as f:
                        data = json.load(f)
                        if data.get('summary'):
                            summaries.append({
                                'timestamp': data['timestamp'],
                                'summary': data['summary']
                            })
        except Exception:
            pass
        return summaries
