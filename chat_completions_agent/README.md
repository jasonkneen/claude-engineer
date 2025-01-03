# Chat Completions Agent

A multi-protocol chat completions agent supporting HTTP, WebSocket, and STDIO interfaces, with a Streamlit web UI.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the server:
   - HTTP/WebSocket mode: `python server/server.py`
   - STDIO mode: `python server/server.py --stdio`

3. Run the web interface:
   ```bash
   streamlit run web/streamlit_app.py
   ```

## Usage

### HTTP API
POST to `/v1/chat/completions`:
```json
{
    "messages": [{"role": "user", "content": "Hello"}],
    "temperature": 0.7
}
```

### WebSocket
Connect to `/ws` and send similar JSON messages.

### STDIO
Write JSON messages to stdin, one per line.

### Web Interface
Access the Streamlit interface at http://localhost:8501