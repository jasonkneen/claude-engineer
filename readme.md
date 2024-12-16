# Claude Engineer

A self-improving assistant framework with tool creation capabilities and multi-agent orchestration.

## Features

- Multi-agent system with autonomous capabilities
- Dynamic tool creation and management
- Voice interaction with TTS and STT support
- Real-time agent status monitoring
- Context-aware task management

## Development

This project uses Python with Flask for the backend and a modern web interface for interaction.

### Setup

1. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the development server:pip install -r requirements-test.txt
```bash
python app.py
```

## Testing

Run the test suite with coverage reporting:
```bash
python -m pytest tests/
```

[pytest]
addopts = --cov=ce3 --cov-report=term-missing --asyncio-mode=strict
