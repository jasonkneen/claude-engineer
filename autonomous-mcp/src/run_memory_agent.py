import os
import sys
import signal
import subprocess  
import asyncio
import time
from pathlib import Path

# Configure paths
BASE_DIR = Path(__file__).parent.parent
MEMORY_SERVICE_DIR = BASE_DIR / "memory_service_temp"
VENV_PATH = MEMORY_SERVICE_DIR / "venv"

def start_memory_service():
    """Start the MCP memory service in the background"""
    activate_venv = f"source {VENV_PATH}/bin/activate"
    pythonpath = f"PYTHONPATH={MEMORY_SERVICE_DIR}/src"
    cmd = f"{activate_venv} && {pythonpath} python -m mcp_memory_service.server"
    
    process = subprocess.Popen(cmd, shell=True, preexec_fn=os.setsid)
    print(f"Started memory service (PID: {process.pid})")
    return process

async def start_memory_agent():
    """Start the memory agent with HTTP and Web interface"""
    from memory_agent import MemoryAgent
    agent = MemoryAgent()
    await agent.start()
    return agent

def shutdown(service_proc):
    """Gracefully shutdown all components"""
    if service_proc:
        os.killpg(os.getpgid(service_proc.pid), signal.SIGTERM)
        print("Stopped memory service")

async def main():
    service_proc = None
    try:
        # Start memory service
        service_proc = start_memory_service()
        await asyncio.sleep(2)  # Wait for service to initialize
        
        # Start memory agent
        agent = await start_memory_agent()
        
        # Keep running until interrupted
        print("\nMemory system running. Press Ctrl+C to stop.")
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        shutdown(service_proc)

if __name__ == "__main__":
    asyncio.run(main())
