import base64
import os

from flask import Flask, jsonify, render_template, request, url_for
from flask.json import JSONEncoder
from werkzeug.utils import secure_filename

from ce3 import Assistant
from config import Config

# Custom JSON encoder to handle TextBlock objects
class CustomJSONEncoder(JSONEncoder):
    def default(self, obj):
        try:
            # Convert TextBlock objects to their string representation
            if hasattr(obj, 'text'):
                return str(obj.text)
            if hasattr(obj, '__dict__'):
                return obj.__dict__
            return str(obj)
        except Exception:
            return str(obj)

app = Flask(__name__, static_folder='static')
app.json_encoder = CustomJSONEncoder
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize the assistant
assistant = Assistant()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message', '')
    image_data = data.get('image')  # Get the base64 image data
    # Get media type from request or extract from data URL
    media_type = data.get('currentMediaType')
    if not media_type and image_data and ',' in image_data and ':' in image_data.split(',')[0]:
        media_type = image_data.split(',')[0].split(':')[1].split(';')[0]
    media_type = media_type or 'image/jpeg'  # Fallback if still not found
    
    # Prepare the message content
    if image_data:
        # Extract base64 data and media type from data URL
        if ',' in image_data:
            _, image_data = image_data.split(',', 1)
        
        # Create a message with both text and image in correct order
        message_content = []
        
        # Add image first
        message_content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": image_data
            }
        })
        
        # Add text if present
        if message.strip():
            message_content.append({
                "type": "text",
                "text": message
            })
    else:
        # Text-only message
        message_content = [{"type": "text", "text": message}] if message.strip() else []
    
    try:
        # Handle the chat message with the appropriate content
        response = assistant.chat(message_content)
        
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
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
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
def reset():
    # Reset the assistant's conversation history
    assistant.reset()
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(debug=False)
