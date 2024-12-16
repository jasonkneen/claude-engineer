document.addEventListener('DOMContentLoaded', function() {
    const themeToggle = document.getElementById('theme-toggle');
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const chatMessages = document.getElementById('chat-messages');

    // Add at the beginning after imports
    function renderMarkdown(text) {
        // You'll need to include a markdown library like marked.js
        // This is a basic implementation
        const codeBlockRegex = /```(\w+)?\n([\s\S]*?)```/g;
        const inlineCodeRegex = /`([^`]+)`/g;
        
        // Replace code blocks
        text = text.replace(codeBlockRegex, (_, lang, code) => {
            return `<pre><code class="language-${lang || ''}">${code.trim()}</code></pre>`;
        });
        
        // Replace inline code
        text = text.replace(inlineCodeRegex, '<code>$1</code>');
        
        // Basic markdown for bold and italic
        text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        text = text.replace(/\*(.+?)\*/g, '<em>$1</em>');
        
        // Convert URLs to links
        text = text.replace(/https?:\/\/[^\s)]+/g, '<a href="$&" target="_blank">$&</a>');
        
        // Convert newlines to <br>
        text = text.replace(/\n/g, '<br>');
        
        return text;
    }

    // Theme toggle
    themeToggle.addEventListener('click', function() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', newTheme);
        
        // Update theme icon
        const themeIcon = themeToggle.querySelector('.theme-icon');
        themeIcon.textContent = newTheme === 'dark' ? '🌙' : '☀️';
        
        // Send theme preference to server
        fetch('/dark-mode', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ enabled: newTheme === 'dark' })
        });
    });

    // Auto-resize textarea
    messageInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = this.scrollHeight + 'px';
    });

    // Send message
    function sendMessage(text) {
        if (!text.trim()) return;

        // Add user message to chat
        addMessageToChat('user', text);

        // Clear input
        messageInput.value = '';
        messageInput.style.height = 'auto';

        // Send to server
        fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: text })
        })
        .then(response => response.json())
        .then(data => {
            if (data.response) {
                addMessageToChat('assistant', data.response);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            addMessageToChat('assistant', 'Sorry, there was an error processing your message.');
        });
    }

    function addMessageToChat(role, content) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', role);
        messageDiv.innerHTML = renderMarkdown(content);
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Send message on button click or Enter (without shift)
    sendButton.addEventListener('click', () => sendMessage(messageInput.value));
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage(messageInput.value);
        }
    });

    // Add agent list functionality
    const agentList = document.querySelector('.agent-list');
    
    const agents = [
        { id: 'default', name: 'Claude Engineer', icon: '🛠️' },
        { id: 'assistant', name: 'General Assistant', icon: '💡' },
        { id: 'code', name: 'Code Specialist', icon: '💻' }
    ];

    function initializeAgentList() {
        agents.forEach(agent => {
            const agentItem = document.createElement('div');
            agentItem.className = 'agent-item';
            agentItem.dataset.agentId = agent.id;
            if (agent.id === 'default') agentItem.classList.add('active');

            agentItem.innerHTML = `
                <div class="agent-icon">${agent.icon}</div>
                <div class="agent-name">${agent.name}</div>
            `;

            agentItem.addEventListener('click', () => {
                document.querySelectorAll('.agent-item').forEach(item => {
                    item.classList.remove('active');
                });
                agentItem.classList.add('active');
                // Add agent switching logic here if needed
            });

            agentList.appendChild(agentItem);
        });
    }

    initializeAgentList();
});
