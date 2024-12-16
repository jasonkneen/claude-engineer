let currentImageData = null;
let currentMediaType = null;

// Initialize dark mode from localStorage
const darkMode = localStorage.getItem('darkMode') === 'true';
document.documentElement.classList.toggle('dark', darkMode);

// Dark mode toggle
document.getElementById('dark-mode-toggle').addEventListener('click', () => {
    document.documentElement.classList.toggle('dark');
    localStorage.setItem('darkMode', document.documentElement.classList.contains('dark'));
});

// Auto-resize textarea
const textarea = document.getElementById('message-input');
textarea.addEventListener('input', function() {
    this.style.height = '28px';
    this.style.height = (this.scrollHeight) + 'px';
});

function appendMessage(content, isUser = false) {
    const messagesDiv = document.getElementById('chat-messages');
    const messageWrapper = document.createElement('div');
    messageWrapper.className = 'message-wrapper';

    const messageDiv = document.createElement('div');
    messageDiv.className = 'flex items-start space-x-4 space-y-1';

    // Avatar
    const avatarDiv = document.createElement('div');
    if (isUser) {
        avatarDiv.className = 'w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center text-gray-600 font-bold text-xs';
        avatarDiv.textContent = 'You';
    } else {
        avatarDiv.className = 'w-8 h-8 rounded-full ai-avatar flex items-center justify-center text-white font-bold text-xs';
        avatarDiv.textContent = 'CE';
    }

    // Message content
    const contentDiv = document.createElement('div');
    contentDiv.className = 'flex-1';

    const innerDiv = document.createElement('div');
    innerDiv.className = 'prose prose-slate max-w-none';

    if (!isUser && content) {
        try {
            innerDiv.innerHTML = marked.parse(content);
        } catch (e) {
            console.error('Error parsing markdown:', e);
            innerDiv.textContent = content;
        }
    } else {
        innerDiv.textContent = content || '';
    }

    contentDiv.appendChild(innerDiv);
    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(contentDiv);
    messageWrapper.appendChild(messageDiv);
    messagesDiv.appendChild(messageWrapper);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// Event Listeners
document.getElementById('upload-btn').addEventListener('click', () => {
    document.getElementById('file-input').click();
});

document.getElementById('file-input').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (file) {
        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            
            if (data.success) {
                currentImageData = data.image_data;
                currentMediaType = data.media_type;
                document.getElementById('preview-img').src = `data:${data.media_type};base64,${data.image_data}`;
                document.getElementById('image-preview').classList.remove('hidden');
            } else {
                console.error('Error uploading image:', data.error); // Pae85
                appendMessage(`Error: ${data.error}`); // Pae85
            }
        } catch (error) {
            console.error('Error uploading image:', error); // Pae85
            appendMessage('Error: Failed to upload image'); // Pae85
        }
    }
});

document.getElementById('remove-image').addEventListener('click', () => {
    currentImageData = null;
    document.getElementById('image-preview').classList.add('hidden');
    document.getElementById('file-input').value = '';
});

function appendThinkingIndicator() {
    const messagesDiv = document.getElementById('chat-messages');
    const messageWrapper = document.createElement('div');
    messageWrapper.className = 'message-wrapper thinking-message';

    const messageDiv = document.createElement('div');
    messageDiv.className = 'flex items-start space-x-4';

    // AI Avatar
    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'w-8 h-8 rounded-full ai-avatar flex items-center justify-center text-white font-bold text-sm';
    avatarDiv.textContent = 'CE';

    // Thinking content
    const contentDiv = document.createElement('div');
    contentDiv.className = 'flex-1';

    const thinkingDiv = document.createElement('div');
    thinkingDiv.className = 'thinking';
    thinkingDiv.innerHTML = '<div style="margin-top: 6px; margin-bottom: 4px;">Thinking<span class="thinking-dots"><span>.</span><span>.</span><span>.</span></span></div>';

    contentDiv.appendChild(thinkingDiv);
    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(contentDiv);
    messageWrapper.appendChild(messageDiv);
    messagesDiv.appendChild(messageWrapper);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;

    return messageWrapper;
}

// Add command+enter handler
document.getElementById('message-input').addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
        e.preventDefault();
        document.getElementById('chat-form').dispatchEvent(new Event('submit'));
    }
});

// Add this function near the top of your file
function updateTokenUsage(usedTokens, maxTokens) {
    const percentage = (usedTokens / maxTokens) * 100;
    const tokenBar = document.getElementById('token-bar');
    const tokensUsed = document.getElementById('tokens-used');
    const tokenPercentage = document.getElementById('token-percentage');

    // Update the numbers
    tokensUsed.textContent = usedTokens.toLocaleString();
    tokenPercentage.textContent = `${percentage.toFixed(1)}%`;

    // Update the bar
    tokenBar.style.width = `${percentage}%`;

    // Update colors based on usage
    tokenBar.classList.remove('warning', 'danger');
    if (percentage > 90) {
        tokenBar.classList.add('danger');
    } else if (percentage > 75) {
        tokenBar.classList.add('warning');
    }
}

// Update the chat form submit handler
document.getElementById('chat-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const messageInput = document.getElementById('message-input');
    const message = messageInput.value.trim();

    if (!message && !currentImageData) return;

    // Append user message (and image if present)
    appendMessage(message, true);
    if (currentImageData) {
        // Optionally show the image in the chat
        const imagePreview = document.createElement('img');
        imagePreview.src = `data:image/jpeg;base64,${currentImageData}`;
        imagePreview.className = 'max-h-48 rounded-lg mt-2';
        document.querySelector('.message-wrapper:last-child .prose').appendChild(imagePreview);
    }

    // Clear input and reset height
    messageInput.value = '';
    resetTextarea();

    try {
        // Add thinking indicator
        const thinkingMessage = appendThinkingIndicator();

        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                image: currentImageData  // This will be null if no image is selected
            })
        });

        const data = await response.json();

        // Update token usage if provided in response
        if (data.token_usage) {
            updateTokenUsage(data.token_usage.total_tokens, data.token_usage.max_tokens);
        }

        // Remove thinking indicator
        if (thinkingMessage) {
            thinkingMessage.remove();
        }

        // Show tool usage if present
        if (data.tool_name) {
            appendToolUsage(data.tool_name);
        }

        // Show response if we have one
        if (data && data.response) {
            appendMessage(data.response);
        } else {
            appendMessage('Error: No response received');
        }

        // Clear image after sending
        currentImageData = null;
        document.getElementById('image-preview').classList.add('hidden');
        document.getElementById('file-input').value = '';

    } catch (error) {
        console.error('Error sending message:', error); // P77c8
        document.querySelector('.thinking-message')?.remove();
        appendMessage('Error: Failed to send message'); // P77c8
    }
});

function resetTextarea() {
    const textarea = document.getElementById('message-input');
    textarea.style.height = '28px';
}

document.getElementById('chat-form').addEventListener('reset', () => {
    resetTextarea();
});

// Add function to show tool usage
function appendToolUsage(toolName) {
    const messagesDiv = document.getElementById('chat-messages');
    const messageWrapper = document.createElement('div');
    messageWrapper.className = 'message-wrapper';

    const messageDiv = document.createElement('div');
    messageDiv.className = 'flex items-start space-x-4';

    // AI Avatar
    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'w-8 h-8 rounded-full ai-avatar flex items-center justify-center text-white font-bold text-sm';
    avatarDiv.textContent = 'CE';

    // Tool usage content
    const contentDiv = document.createElement('div');
    contentDiv.className = 'flex-1';

    const toolDiv = document.createElement('div');
    toolDiv.className = 'tool-usage';
    toolDiv.textContent = `Using tool: ${toolName}`;

    contentDiv.appendChild(toolDiv);
    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(contentDiv);
    messageWrapper.appendChild(messageDiv);
    messagesDiv.appendChild(messageWrapper);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// Add function to show agent information
function appendAgentInfo(agentData) {
    // Get template
    const template = document.getElementById('agent-card-template');
    const card = template.content.cloneNode(true);

    // Set agent name and role
    card.querySelector('h3').textContent = agentData.name;

    // Set status badge
    const statusBadge = card.querySelector('.px-2');
    statusBadge.textContent = agentData.status;
    statusBadge.classList.add(
        agentData.status === 'Active' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
    );

    // Set role
    card.querySelector('p').textContent = `Role: ${agentData.role}`;

    // Set current task
    card.querySelector('.task-display').textContent = agentData.current_task || 'No active task';

    // Set progress bar and percentage
    const progressBar = card.querySelector('.progress-bar');
    const progressPercentage = card.querySelector('.progress-percentage');
    progressBar.style.width = `${agentData.progress}%`;
    progressPercentage.textContent = `${agentData.progress}%`;

    // Set runtime
    const runtimeDisplay = card.querySelector('.runtime-display');
    if (agentData.start_time) {
        const runtime = Math.floor((Date.now() - new Date(agentData.start_time)) / 1000);
        runtimeDisplay.textContent = `${runtime}s`;
    }

    // Update task history
    const taskHistoryDiv = card.querySelector('.task-history');
    if (agentData.task_history && agentData.task_history.length > 0) {
        agentData.task_history.slice(-3).forEach(task => {
            const taskEl = document.createElement('div');
            taskEl.className = 'flex items-center space-x-1';
            taskEl.innerHTML = `
                <span class="w-2 h-2 rounded-full ${task.completed ? 'bg-green-400' : 'bg-gray-300'}"></span>
                <span>${task.name}</span>
            `;
            taskHistoryDiv.appendChild(taskEl);
        });
    } else {
        taskHistoryDiv.innerHTML = '<div class="text-gray-400">No previous tasks</div>';
    }

    // Add to agent list
    document.getElementById('agent-list').appendChild(card);
}

function updateAgentStatus() {
    fetch('/agent_status')
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch agent status');
            }
            return response.json();
        })
        .then(data => {
            if (data.agents && Array.isArray(data.agents)) {
                // Clear existing agent list
                const agentList = document.getElementById('agent-list');
                agentList.innerHTML = '';

                // Add new agent cards
                data.agents.forEach(agent => {
                    appendAgentInfo(agent);
                });
            }
        })
        .catch(error => {
            console.error('Error fetching agent status:', error);
        });
}

// Start periodic agent status updates when the page loads
document.addEventListener('DOMContentLoaded', () => {
    // Initial agent status update
    updateAgentStatus();

    // Set up periodic updates
    const statusInterval = setInterval(updateAgentStatus, 5000);

    // Clean up interval when page is unloaded
    window.addEventListener('unload', () => {
        clearInterval(statusInterval);
    });
});

window.addEventListener('load', async () => {
    try {
        // Reset the conversation when page loads
        const response = await fetch('/reset', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            console.error('Failed to reset conversation');
        }

        // Clear any existing messages except the first one
        const messagesDiv = document.getElementById('chat-messages');
        const messages = messagesDiv.getElementsByClassName('message-wrapper');
        while (messages.length > 1) {
            messages[1].remove();
        }

        // Reset any other state
        currentImageData = null;
        document.getElementById('image-preview')?.classList.add('hidden');
        document.getElementById('file-input').value = '';
        document.getElementById('message-input').value = '';
        resetTextarea();

        // Reset token usage display
        updateTokenUsage(0, 200000);
    } catch (error) {
        console.error('Error resetting conversation:', error);
    }
}); 