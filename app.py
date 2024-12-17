from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from ce3 import Assistant
from tools.agent_base import AgentBaseTool, AgentRole
from tools.voice_tool import VoiceTool, VoiceRole
from tools.base import BaseTool
from tools.agents.specialized_agents import FrontendAgent, BackendAgent, DatabaseAgent
from tools.agents.base_conversation_agent import BaseConversationAgent
from tools.agents.orchestrator_agent import OrchestratorAgent
import os
import time
from werkzeug.utils import secure_filename
import base64
from config import Config
import importlib
import inspect
from typing import List, Type
import asyncio
import logging

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure upload settings
UPLOAD_FOLDER = 'uploads'
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize globals
assistant = None
dark_mode = False
agent_config = {}

@app.on_event("startup")
async def startup():
    """Initialize assistant and tools before serving."""
    global assistant
    try:
        config = Config()
        config.test_mode = True  # Enable test mode for development
        assistant = await Assistant(config)  # Now properly awaitable
        app.assistant = assistant  # Make assistant available in app context
        tools = await load_tools()
        for tool in tools.values():
            assistant.tools.append(tool)
    except Exception as e:
        logging.error(f"Error during startup: {str(e)}")
        raise

@app.route('/')
async def home():
    """Render main application page."""
    return await render_template('index.html', dark_mode=dark_mode)

@app.route('/dark-mode', methods=['GET', 'POST'])
async def toggle_dark_mode():
    """Handle dark mode toggle."""
    global dark_mode
    if request.method == 'POST':
        data = await request.get_json()
        dark_mode = data.get('enabled', False)
    return jsonify({'enabled': dark_mode})

@app.route('/agent-config', methods=['GET', 'POST'])
async def handle_agent_config():
    """Handle agent configuration."""
    try:
        if request.method == 'POST':
            data = await request.get_json()
            agent_config.update(data)
        return jsonify({'agents': agent_config})
    except Exception as e:
        logging.error(f"Error in agent-config endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/update-agent-config', methods=['POST'])
async def update_agent_config():
    """Update agent configuration."""
    try:
        data = await request.get_json()
        agent_config.update(data)
        return jsonify({
            'status': 'updated',
            'config': agent_config
        })
    except Exception as e:
        logging.error(f"Error updating agent config: {str(e)}")
        return jsonify({'error': str(e)}), 500

async def load_tools():
    """Load and initialize all tools from the tools directory."""
    tools_dir = os.path.join(os.path.dirname(__file__), 'tools')
    tools = {}
    timestamp = int(time.time())
    processed_classes = set()  # Track processed classes to avoid duplicates

    for filename in os.listdir(tools_dir):
        if filename.endswith('.py') and not filename.startswith('__'):
            module_name = filename[:-3]
            try:
                module = importlib.import_module(f'tools.{module_name}')
                for name, obj in inspect.getmembers(module):
                    if (not inspect.isclass(obj) or
                        obj.__module__ != f'tools.{module_name}' or
                        not name.endswith('Tool') or
                        obj in processed_classes):
                        continue

                    if inspect.isabstract(obj):
                        continue

                    processed_classes.add(obj)
                    tool_name = name.lower()
                    agent_id = f"{tool_name}_{timestamp}"

                    try:
                        if AgentBaseTool in obj.__mro__[1:]:
                            role_map = {
                                'AgentManagerTool': AgentRole.ORCHESTRATOR,
                                'TestAgentTool': AgentRole.TEST,
                                'ContextManagerTool': AgentRole.CONTEXT,
                                'TaskAgentTool': AgentRole.TASK,
                                'ConversationAgentTool': AgentRole.CONVERSATION,
                                'FrontendAgentTool': AgentRole.FRONTEND,
                                'BackendAgentTool': AgentRole.BACKEND,
                                'DatabaseAgentTool': AgentRole.DATABASE
                            }
                            role = role_map.get(name, AgentRole.CUSTOM)
                            tool = obj(agent_id=agent_id, role=role, name=name)
                            await tool.initialize()

                        elif VoiceTool in obj.__mro__[1:]:
                            tool = obj(agent_id=agent_id, role=VoiceRole.VOICE_CONTROL, name=f"Voice_{name}")
                            await tool.initialize()

                        elif BaseTool in obj.__mro__[1:]:
                            tool = obj(name=name)
                            await tool.initialize()

                        else:
                            continue

                        if tool:
                            tools[tool_name] = tool
                            print(f'Loaded tool: {name}')

                    except Exception as e:
                        print(f'Error initializing tool {name}: {str(e)}')

            except Exception as e:
                print(f'Error loading module {module_name}: {str(e)}')

    return tools

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Handle WebSocket connections for real-time chat."""
    try:
        await websocket.accept()
        while True:
            try:
                # Receive and parse message
                data = await websocket.receive_json()
                message = data.get('message', '')
                voice_enabled = data.get('voice', False)

                # Process message
                response = await assistant.chat(message)

                # Generate voice response if requested
                audio_data = None
                if voice_enabled and response:
                    try:
                        voice_tool = next((tool for tool in assistant.tools if isinstance(tool, VoiceTool)), None)
                        if voice_tool:
                            audio_data = await voice_tool.text_to_speech(str(response))
                    except Exception as e:
                        logging.error(f"Voice generation error: {str(e)}")

                # Send response
                await websocket.send_json({
                    'response': response,
                    'audio': audio_data,
                    'thinking': False,
                    'timestamp': datetime.datetime.now().isoformat()
                })

            except WebSocketDisconnect:
                logging.info("WebSocket client disconnected")
                break
            except Exception as e:
                logging.error(f"Error processing message: {str(e)}")
                await websocket.send_json({
                    'error': str(e),
                    'timestamp': datetime.datetime.now().isoformat()
                })
    except Exception as e:
        logging.error(f"WebSocket connection error: {str(e)}")

@app.post("/chat")
async def chat(message: dict):
    """Legacy HTTP endpoint for chat."""
    try:
        message_text = message.get('message', '')
        image_data = data.get('image')  # Get the base64 image data

        if image_data:
            message_content = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": image_data.split(',')[1] if ',' in image_data else image_data
                    }
                }
            ]

            if message.strip():
                message_content.append({
                    "type": "text",
                    "text": message
                })
        else:
            message_content = message

        response = await assistant.chat(message_content)

        token_usage = {
            'total_tokens': assistant.total_tokens_used,
            'max_tokens': Config.MAX_CONVERSATION_TOKENS
        }

        tool_name = None
        if assistant.conversation_history:
            for msg in reversed(assistant.conversation_history):
                if msg.get('role') == 'assistant' and msg.get('content'):
                    content = msg['content']
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get('type') == 'tool_use':
                                tool_name = block.get('name')
                                break
                    if tool_name:
                        break

        return jsonify({
            'response': response,
            'thinking': False,
            'tool_name': tool_name,
            'token_usage': token_usage
        })

    except Exception as e:
        logging.error(f"Exception in chat route: {str(e)}")
        return jsonify({
            'response': f"Error: {str(e)}",
            'thinking': False,
            'tool_name': None,
            'token_usage': None
        }), 200

@app.route('/upload', methods=['POST'])
async def upload_file():
    try:
        if 'file' not in await request.files:
            return jsonify({'error': 'No file part'}), 400
    
        file = (await request.files)['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
    
        if file and file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            await file.save(filepath)
    
            media_type = file.content_type or 'image/jpeg'
    
            with open(filepath, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    
            os.remove(filepath)
    
            return jsonify({
                'success': True,
                'image_data': encoded_string,
                'media_type': media_type
            })
    
        return jsonify({'error': 'Invalid file type'}), 400
    except Exception as e:
        logging.error(f"Exception in upload_file route: {str(e)}")
        return jsonify({'error': f"Error: {str(e)}"}), 500

@app.route('/reset', methods=['POST'])
async def reset():
    assistant.reset()
    return jsonify({'status': 'success'})

@app.route('/agent-status', methods=['GET'])
async def agent_status():
    """Get agent status information."""
    try:
        if not app.assistant or not app.assistant.tools:
            return jsonify({'error': 'Assistant not initialized'}), 500

        status = {
            'agents': [],
            'voice_enabled': False
        }

        for tool in app.assistant.tools:
            if hasattr(tool, 'get_state'):
                try:
                    tool_state = await tool.get_state()
                    agent_status = {
                        'id': getattr(tool, 'agent_id', tool.__class__.__name__),
                        'name': getattr(tool, 'name', tool.__class__.__name__),
                        'role': getattr(tool, 'role', None).value if hasattr(tool, 'role') and getattr(tool, 'role', None) else None,
                        'status': 'Active' if not tool_state.get('is_paused', False) else 'Paused',
                        'current_task': tool_state.get('current_task'),
                        'progress': tool_state.get('progress'),
                        'task_history': tool_state.get('task_history', [])
                    }
                    status['agents'].append(agent_status)
                except Exception as e:
                    logging.error(f"Error getting state for tool {tool.__class__.__name__}: {str(e)}")

            if hasattr(tool, 'role') and getattr(tool, 'role', None) == VoiceRole.VOICE_CONTROL:
                status['voice_enabled'] = True

        return jsonify(status)
    except Exception as e:
        logging.error(f"Error in agent-status endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/speak', methods=['POST'])
async def speak():
    """Handle text-to-speech requests."""
    try:
        if not app.assistant or not app.assistant.tools:
            return jsonify({'error': 'Assistant not initialized'}), 500

        data = await request.get_json()
        text = data.get('text')
        if not text:
            return jsonify({'error': 'No text provided'}), 400

        voice_tool = next((tool for tool in app.assistant.tools if hasattr(tool, 'role') and getattr(tool, 'role', None) == VoiceRole.VOICE_CONTROL), None)
        if not voice_tool:
            return jsonify({'error': 'Voice tool not available'}), 500

        try:
            audio_path = await voice_tool.speak(text)
            return jsonify({
                'status': 'success',
                'audio_path': audio_path
            })
        except Exception as e:
            logging.error(f"Error generating speech: {str(e)}")
            return jsonify({'error': f'Speech generation failed: {str(e)}'}), 500

    except Exception as e:
        logging.error(f"Error in speak endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/transcribe', methods=['POST'])
async def transcribe():
    """Handle speech-to-text requests."""
    try:
        if not app.assistant or not app.assistant.tools:
            return jsonify({'error': 'Assistant not initialized'}), 500

        files = await request.files
        if 'audio' not in files:
            return jsonify({'error': 'No audio file provided'}), 400

        audio_file = files['audio']
        if not audio_file.filename:
            return jsonify({'error': 'Invalid audio file'}), 400

        temp_path = os.path.join(os.path.dirname(__file__), 'static', 'uploads', f'temp_{int(time.time())}.wav')
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        await audio_file.save(temp_path)

        voice_tool = next((tool for tool in app.assistant.tools if hasattr(tool, 'role') and getattr(tool, 'role', None) == VoiceRole.VOICE_CONTROL), None)
        if not voice_tool:
            os.remove(temp_path)
            return jsonify({'error': 'Voice tool not available'}), 500

        try:
            text = await voice_tool.transcribe(temp_path)
            os.remove(temp_path)
            return jsonify({'text': text})
        except Exception as e:
            os.remove(temp_path)
            logging.error(f"Error transcribing audio: {str(e)}")
            return jsonify({'error': f'Transcription failed: {str(e)}'}), 500

    except Exception as e:
        logging.error(f"Error in transcribe endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/create-flow', methods=['POST'])
async def create_flow():
    """Create a new agent workflow."""
    try:
        data = await request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        required_fields = ['name', 'description', 'steps']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400

        steps = data['steps']
        if not isinstance(steps, list) or not steps:
            return jsonify({'error': 'Steps must be a non-empty list'}), 400

        for step in steps:
            if not isinstance(step, dict) or 'type' not in step or 'content' not in step:
                return jsonify({'error': 'Invalid step format'}), 400

        flow_id = f"flow_{int(time.time())}"

        return jsonify({
            'flow_id': flow_id,
            'status': 'created',
            'message': f"Created flow: {data['name']}"
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, port=6606, host='localhost')
