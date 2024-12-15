from quart import Quart, render_template, request, jsonify, url_for
from ce3 import Assistant
from tools.agent_base import AgentBaseTool, AgentRole
from tools.voice_tool import VoiceTool, VoiceRole
from tools.base import BaseTool
import os
import time
from werkzeug.utils import secure_filename
import base64
from config import Config
import importlib
import inspect
from typing import List, Type
import asyncio

app = Quart(__name__, static_folder='static')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize globals
assistant = None
dark_mode = False
agent_config = {}

@app.before_serving
async def startup():
    """Initialize assistant and tools before serving."""
    global assistant, tools
    assistant = await Assistant()
    tools = await load_tools()
    for tool_name, tool in tools.items():
        assistant.tools.append(tool)

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
    global agent_config
    if request.method == 'POST':
        data = await request.get_json()
        agent_config.update(data)
    return jsonify(agent_config)

# Initialize tools
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
                    # Skip if already processed or not a tool class
                    if (not inspect.isclass(obj) or
                        obj.__module__ != f'tools.{module_name}' or
                        not name.endswith('Tool') or
                        obj in processed_classes):
                        continue

                    # Skip abstract base classes
                    if inspect.isabstract(obj):
                        continue

                    processed_classes.add(obj)
                    tool_name = name.lower()
                    agent_id = f"{tool_name}_{timestamp}"

                    try:
                        # Initialize based on class hierarchy
                        if AgentBaseTool in obj.__mro__[1:]:  # Check if AgentBaseTool is in the inheritance chain
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

                        elif VoiceTool in obj.__mro__[1:]:  # Check if VoiceTool is in the inheritance chain
                            tool = obj(agent_id=agent_id, role=VoiceRole.VOICE_CONTROL, name=f"Voice_{name}")
                            await tool.initialize()

                        elif BaseTool in obj.__mro__[1:]:  # Direct BaseTool subclasses
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



@app.route('/chat', methods=['POST'])
async def chat():
    try:
        data = await request.get_json()
        message = data.get('message', '')
        image_data = data.get('image')  # Get the base64 image data

        # Prepare the message content
        if image_data:
            # Create a message with both text and image in correct order
            message_content = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",  # We should detect this from the image
                        "data": image_data.split(',')[1] if ',' in image_data else image_data  # Remove data URL prefix if present
                    }
                }
            ]

            # Only add text message if there is actual text
            if message.strip():
                message_content.append({
                    "type": "text",
                    "text": message
                })
        else:
            # Text-only message
            message_content = message

        # Handle the chat message with the appropriate content
        response = await assistant.chat(message_content)

        # Get token usage from assistant
        token_usage = {
            'total_tokens': assistant.total_tokens_used,
            'max_tokens': Config.MAX_CONVERSATION_TOKENS
        }

        # Get the last used tool from the conversation history
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
        return jsonify({
            'response': f"Error: {str(e)}",
            'thinking': False,
            'tool_name': None,
            'token_usage': None
        }), 200  # Return 200 even for errors to handle them gracefully in frontend

@app.route('/upload', methods=['POST'])
async def upload_file():
    if 'file' not in await request.files:
        return jsonify({'error': 'No file part'}), 400

    file = (await request.files)['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        await file.save(filepath)

        # Get the actual media type
        media_type = file.content_type or 'image/jpeg'  # Default to jpeg if not detected

        # Convert image to base64
        with open(filepath, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')

        # Clean up the file
        os.remove(filepath)

        return jsonify({
            'success': True,
            'image_data': encoded_string,
            'media_type': media_type
        })

    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/reset', methods=['POST'])
async def reset():
    # Reset the assistant's conversation history
    assistant.reset()
    return jsonify({'status': 'success'})

@app.route('/agent-status', methods=['GET'])
async def agent_status():
    """Get status of all agents."""
    try:
        agent_statuses = []
        for tool in tools.values():  # Use tools dict instead of assistant.tools
            if isinstance(tool, AgentBaseTool):
                state = tool.get_state()
                agent_statuses.append({
                    'id': tool.agent_id,
                    'name': tool.name,
                    'role': tool.role.value,
                    'status': 'Active' if not state.is_paused else 'Paused',
                    'current_task': state.current_task,
                    'progress': state.progress,
                    'task_history': state.task_history
                })
        return jsonify({'agents': agent_statuses})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/speak', methods=['POST'])
async def speak():
    """Text-to-speech endpoint."""
    try:
        data = await request.get_json()
        text = data.get('text', '')
        if not text:
            return jsonify({'error': 'No text provided'}), 400

        voice_tool = VoiceTool(agent_id="tts_agent", role=VoiceRole.TTS, name="TTS Agent")
        await voice_tool.speak(text)
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/transcribe', methods=['POST'])
async def transcribe():
    """Speech-to-text endpoint."""
    if 'audio' not in await request.files:
        return jsonify({'error': 'No audio file provided'}), 400

    audio_file = (await request.files)['audio']
    if audio_file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if audio_file:
        filename = secure_filename(audio_file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        await audio_file.save(filepath)

        try:
            voice_tool = VoiceTool(agent_id="stt_agent", role=VoiceRole.STT, name="STT Agent")
            text = await voice_tool.transcribe(filepath)

            # Clean up the audio file
            os.remove(filepath)

            return jsonify({
                'success': True,
                'text': text
            })
        except Exception as e:
            # Clean up on error
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({'error': str(e)}), 500

    return jsonify({'error': 'Invalid audio file'}), 400

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

        # Validate steps
        steps = data['steps']
        if not isinstance(steps, list) or not steps:
            return jsonify({'error': 'Steps must be a non-empty list'}), 400

        for step in steps:
            if not isinstance(step, dict) or 'type' not in step or 'content' not in step:
                return jsonify({'error': 'Invalid step format'}), 400

        # Create flow ID
        flow_id = f"flow_{int(time.time())}"

        return jsonify({
            'flow_id': flow_id,
            'status': 'created',
            'message': f"Created flow: {data['name']}"
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, port=5000, host='0.0.0.0')       