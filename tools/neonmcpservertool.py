from tools.base import BaseTool
import os
import git
import subprocess
import json
import shutil
from pathlib import Path

class NeonMcpServerTool(BaseTool):
    name = "neonmcpservertool"
    description = '''
    Tool for setting up and managing a Neon MCP server implementation.
    Handles repository setup, configuration, transport protocols, environment setup,
    testing capabilities, and security features for Neon database MCP servers.
    '''
    input_schema = {
        "type": "object",
        "properties": {
            "repo_url": {
                "type": "string",
                "default": "https://github.com/neondatabase/mcp-server-neon"
            },
            "install_path": {
                "type": "string",
                "description": "Installation directory path"
            },
            "db_config": {
                "type": "object",
                "properties": {
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                    "user": {"type": "string"},
                    "password": {"type": "string"}
                }
            },
            "transport": {
                "type": "string",
                "enum": ["sse", "websocket", "both"],
                "default": "both"
            },
            "dev_mode": {
                "type": "boolean",
                "default": False
            }
        },
        "required": ["install_path", "db_config"]
    }

    def execute(self, **kwargs) -> str:
        try:
            install_path = Path(kwargs["install_path"])
            db_config = kwargs["db_config"]
            repo_url = kwargs.get("repo_url", "https://github.com/neondatabase/mcp-server-neon")
            transport = kwargs.get("transport", "both")
            dev_mode = kwargs.get("dev_mode", False)

            # Create installation directory
            install_path.mkdir(parents=True, exist_ok=True)

            # Clone repository
            if not (install_path / ".git").exists():
                git.Repo.clone_from(repo_url, install_path)

            # Setup virtual environment
            venv_path = install_path / "venv"
            if not venv_path.exists():
                subprocess.run(["python", "-m", "venv", str(venv_path)], check=True)

            # Install dependencies
            pip_path = venv_path / "bin" / "pip"
            subprocess.run([str(pip_path), "install", "-r", str(install_path / "requirements.txt")], check=True)

            # Create configuration
            config = {
                "database": db_config,
                "server": {
                    "host": "0.0.0.0",
                    "port": 8080,
                    "transport": transport,
                    "debug": dev_mode
                },
                "security": {
                    "enable_auth": True,
                    "jwt_secret": os.urandom(32).hex(),
                    "allowed_origins": ["*"]
                }
            }

            # Write configuration file
            config_path = install_path / "config.json"
            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)

            # Setup test environment if dev_mode is enabled
            if dev_mode:
                test_requirements = install_path / "test-requirements.txt"
                if test_requirements.exists():
                    subprocess.run([str(pip_path), "install", "-r", str(test_requirements)], check=True)

            return f"Neon MCP server successfully set up at {install_path}"

        except git.GitCommandError as e:
            raise Exception(f"Git repository clone failed: {str(e)}")
        except subprocess.CalledProcessError as e:
            raise Exception(f"Environment setup failed: {str(e)}")
        except json.JSONDecodeError as e:
            raise Exception(f"Configuration creation failed: {str(e)}")
        except Exception as e:
            raise Exception(f"Setup failed: {str(e)}")