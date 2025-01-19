import logging
from typing import List, Dict, Optional
import time
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime

def format_size(size_bytes: float) -> str:
    """Format bytes into human readable size (KB, MB, GB)."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f}TB"

def format_rate(bytes_per_sec: float) -> str:
    """Format bytes/sec into human readable rate."""
    return f"{format_size(bytes_per_sec)}/s"

# ANSI escape codes
RESET = "\033[0m"

# Simple foreground colors for log levels
DEBUG_STYLE = "\033[90m"  # dark gray
ERROR_STYLE = "\033[31m"  # red
WARN_STYLE = "\033[33m"   # yellow
INFO_STYLE = "\033[36m"   # cyan
PANEL_BORDER = "\033[38;5;240m"  # gray

@dataclass
class MessageBuffer:
    """Buffer to collect and group messages by their type."""
    messages: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))
    current_type: str = None

    def add(self, msg_type: str, message: str):
        """Add a message to the buffer."""
        self.messages[msg_type].append(message)
        self.current_type = msg_type

    def flush(self) -> str:
        """Output all buffered messages grouped by type in panels."""
        output = []
        for msg_type, msgs in self.messages.items():
            if not msgs:
                continue
            
            # Create the header based on message type
            style = globals().get(f"{msg_type}_STYLE", "")
            header = f"{style}{msg_type}{RESET}"
            
            # Format all messages of this type
            formatted_msgs = []
            for msg in msgs:
                formatted_msgs.append(f"{style}{msg}{RESET}")
            
            panel = format_panel("\n".join(formatted_msgs), header=header)
            output.append(panel)
        
        # Clear the buffer
        self.messages.clear()
        self.current_type = None
        
        return "\n\n".join(output)

# Global message buffer
buffer = MessageBuffer()

def debug(msg: str):
    """Add a debug message to the buffer."""
    buffer.add("DEBUG", msg)

def info(msg: str):
    """Add an info message to the buffer."""
    buffer.add("INFO", msg)

def error(msg: str):
    """Add an error message to the buffer."""
    buffer.add("ERROR", msg)

def warn(msg: str):
    """Add a warning message to the buffer."""
    buffer.add("WARN", msg)

def flush() -> str:
    """Flush all buffered messages."""
    return buffer.flush()

def format_panel(text: str, header: str = None, fit_content: bool = False):
    """Create a box around the text using Unicode box-drawing characters"""
    """Create a box around the text using Unicode box-drawing characters"""
    lines = text.split('\n')
    max_length = max(len(line) for line in lines)
    if fit_content:
        # Don't pad to terminal width for progress bars
        padding = 2
    else:
        # Get terminal width and pad appropriately
        import shutil
        term_width = shutil.get_terminal_size().columns
        padding = max(2, min(term_width - max_length - 4, 20))
    
    if header:
        top = f"{PANEL_BORDER}┌─── {header} {'─' * (max_length - len(header))}┐{RESET}"
    else:
        top = f"{PANEL_BORDER}┌{'─' * (max_length + 2)}┐{RESET}"
    bottom = f"{PANEL_BORDER}└{'─' * (max_length + 2)}┘{RESET}"

    middle = []
    for line in lines:
        padding = ' ' * (max_length - len(line))
        middle.append(f"{PANEL_BORDER}│ {line}{padding} │{RESET}")
        
    return '\n'.join([top] + middle + [bottom])

class ColorFormatter(logging.Formatter):
    def format(self, record):
        # Format the message first
        message = super().format(record)
        # Then apply our color formatting
        return format_log(f"{record.levelname}: {record.getMessage()}")

def format_log(text, use_panel=False, indent=2):
    """Format log messages by coloring level prefix and optionally wrap in a panel"""
    formatted_text = text
    if text.startswith("DEBUG:"):
        formatted_text = f"{DEBUG_STYLE}DEBUG:{RESET} {text[6:]}"
    elif text.startswith("ERROR:"):
        formatted_text = f"{ERROR_STYLE}ERROR:{RESET} {text[6:]}"
    elif text.startswith("WARN:"):
        formatted_text = f"{WARN_STYLE}WARN:{RESET} {text[5:]}"
    elif text.startswith("INFO:"):
        formatted_text = f"{INFO_STYLE}INFO:{RESET} {text[5:]}"
        
    if use_panel:
        return format_panel(formatted_text)
    else:
        return " " * indent + formatted_text

if __name__ == "__main__":
    # Demo the different styles
    print("Message Grouping Demo:")
    print("-" * 50)
    
    # Add some debug messages
    debug("Loading configuration file")
    debug("Initializing database connection")
    
    # Add an error message
    error("Failed to connect to database")
    
    # Add some warnings
    warn("Cache size exceeding recommended limit")
    warn("Performance may be degraded")
    
    # Add some info messages
    info("System started successfully")
    info("Listening on port 8080")
    
    # Flush and display all messages
    print(flush())
    
    print("\nBuffering Demo:")
    print("-" * 50)
    
    # Add mixed message types
    debug("Starting up...")
    error("Configuration file not found")
    error("Using default configuration")
    debug("Initialized default settings")
    
    # Flush and display all messages
    print(flush())

@dataclass
class ProgressBar:
    """Displays a progress bar with optional size and rate information."""
    total: Optional[int] = None
    width: int = 30
    description: str = ""
    _start_time: float = field(default_factory=time.time)
    _last_update: float = field(default_factory=time.time)
    _current: int = 0
    
    def update(self, current: int) -> str:
        """Update progress and return formatted progress bar."""
        self._current = current
        now = time.time()
        
        # Calculate progress percentage and create the bar
        if self.total:
            fraction = min(1.0, current / self.total)
            filled_width = int(self.width * fraction)
            bar = "█" * filled_width + "░" * (self.width - filled_width)
            
            # Calculate transfer rate
            elapsed = now - self._start_time
            if elapsed > 0:
                rate = current / elapsed
                rate_str = format_rate(rate)
            else:
                rate_str = "N/A"
            
            # Format progress string
            progress = f"{format_size(current)}/{format_size(self.total)} {rate_str}"
        else:
            # Indeterminate progress
            pos = current % (self.width * 2)
            if pos > self.width:
                pos = self.width * 2 - pos
            bar = (" " * pos) + "█" * 3 + (" " * (self.width - pos - 3))
            progress = format_size(current)
        
        return format_panel(
            f"{self.description:<20} [{bar}] {progress}",
            fit_content=True
        )

    def done(self) -> str:
        """Mark progress as complete."""
        if self.total:
            self._current = self.total
        return self.update(self._current)
