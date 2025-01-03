import requests
import streamlit as st

st.title("Chat Completions Agent")

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []

# Available models
MODELS = [
    "gpt-4-0125-preview",  # GPT-4 Turbo
    "gpt-4",
    "gpt-3.5-turbo"
]

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Chat input
if prompt := st.chat_input():
    # Display user message
    with st.chat_message("user"):
        st.write(prompt)
    
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Get bot response
    with st.spinner("Thinking..."):
        try:
            response = requests.post(
                "http://localhost:8000/v1/chat/completions",
                json={
                    "messages": st.session_state.messages,
                    "temperature": st.session_state.get('temperature', 0.7),
                    "model": st.session_state.get('model', "gpt-4-0125-preview")
                }
            )
            response_data = response.json()
            assistant_message = response_data["choices"][0]["message"]
        except Exception as e:
            st.error(f"Error: {str(e)}")
            assistant_message = {"role": "assistant", "content": f"Error: {str(e)}"}
    
    # Display assistant response
    with st.chat_message("assistant"):
        st.write(assistant_message["content"])
    
    # Add assistant response to history
    st.session_state.messages.append(assistant_message)

# Sidebar controls
with st.sidebar:
    st.header("Settings")
    
    # Model selection
    selected_model = st.selectbox(
        "Model",
        MODELS,
        index=0
    )
    st.session_state.model = selected_model
    
    # Temperature control
    temperature = st.slider("Temperature", 0.0, 1.0, 0.7)
    st.session_state.temperature = temperature
    
    # Clear chat button
    if st.button("Clear Chat"):
        st.session_state.messages = []