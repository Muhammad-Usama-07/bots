import streamlit as st
from typing import Generator
from groq import Groq
import csv
from datetime import datetime
import os

st.set_page_config(page_icon="💬", layout="wide",
                   page_title="Groq Goes Brrrrrrrr...")


def icon(emoji: str):
    """Shows an emoji as a Notion-style page icon."""
    st.write(
        f'<span style="font-size: 78px; line-height: 1">{emoji}</span>',
        unsafe_allow_html=True,
    )


icon("🏎️")

st.subheader("Groq Chat Streamlit App", divider="rainbow", anchor=False)

client = Groq(
    api_key=st.secrets["GROQ_API_KEY"],
)

# Initialize chat history and selected model
if "messages" not in st.session_state:
    st.session_state.messages = []
    # Add system prompt to guide the chatbot behavior
    st.session_state.messages.append({
        "role": "system",
        "content": """You are a helpful assistant. When a user wants to subscribe or provide their information, 
        ask for their name and email address. Once you have both pieces of information, confirm that you've saved them.
        Be polite and conversational. Only ask for information when the user expresses interest in subscribing or 
        providing their details."""
    })

if "selected_model" not in st.session_state:
    st.session_state.selected_model = None

if "collecting_info" not in st.session_state:
    st.session_state.collecting_info = False
    
if "user_info" not in st.session_state:
    st.session_state.user_info = {"name": None, "email": None}

# Define model details
models = {
    "gemma2-9b-it": {"name": "Gemma2-9b-it", "tokens": 8192, "developer": "Google"},
    "llama-3.3-70b-versatile": {"name": "LLaMA3.3-70b-versatile", "tokens": 128000, "developer": "Meta"},
    "llama-3.1-8b-instant" : {"name": "LLaMA3.1-8b-instant", "tokens": 128000, "developer": "Meta"},
    "llama3-70b-8192": {"name": "LLaMA3-70b-8192", "tokens": 8192, "developer": "Meta"},
    "llama3-8b-8192": {"name": "LLaMA3-8b-8192", "tokens": 8192, "developer": "Meta"},
    "mixtral-8x7b-32768": {"name": "Mixtral-8x7b-Instruct-v0.1", "tokens": 32768, "developer": "Mistral"},
}

# Layout for model selection and max_tokens slider
col1, col2 = st.columns(2)

with col1:
    model_option = st.selectbox(
        "Choose a model:",
        options=list(models.keys()),
        format_func=lambda x: models[x]["name"],
        index=4  # Default to mixtral
    )

# Detect model change and clear chat history if model has changed
if st.session_state.selected_model != model_option:
    st.session_state.messages = []
    st.session_state.selected_model = model_option
    # Re-add system prompt after clearing
    st.session_state.messages.append({
        "role": "system",
        "content": """You are a helpful assistant. When a user wants to subscribe or provide their information, 
        ask for their name and email address. Once you have both pieces of information, confirm that you've saved them.
        Be polite and conversational. Only ask for information when the user expresses interest in subscribing or 
        providing their details."""
    })

max_tokens_range = models[model_option]["tokens"]

with col2:
    # Adjust max_tokens slider dynamically based on the selected model
    max_tokens = st.slider(
        "Max Tokens:",
        min_value=512,  # Minimum value to allow some flexibility
        max_value=max_tokens_range,
        # Default value or max allowed if less
        value=min(32768, max_tokens_range),
        step=512,
        help=f"Adjust the maximum number of tokens (words) for the model's response. Max for selected model: {max_tokens_range}"
    )

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    if message["role"] not in ["system", "user", "assistant"]:
        continue
    avatar = '🤖' if message["role"] == "assistant" else '👨‍💻'
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

def save_user_info(name, email):
    """Save user information to a CSV file."""
    file_exists = os.path.isfile('user_data.csv')
    
    with open('user_data.csv', 'a', newline='') as csvfile:
        fieldnames = ['timestamp', 'name', 'email']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
            
        writer.writerow({
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'name': name,
            'email': email
        })

def generate_chat_responses(chat_completion) -> Generator[str, None, None]:
    """Yield chat response content from the Groq API response."""
    for chunk in chat_completion:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content

if prompt := st.chat_input("Enter your prompt here..."):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user", avatar='👨‍💻'):
        st.markdown(prompt)

    # Check if we're in info collection mode
    if st.session_state.collecting_info:
        # Check which info we're waiting for
        if st.session_state.user_info["name"] is None:
            st.session_state.user_info["name"] = prompt
            st.session_state.messages.append({"role": "assistant", "content": "Please also provide your email address:"})
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown("Please also provide your email address:")
        elif st.session_state.user_info["email"] is None:
            st.session_state.user_info["email"] = prompt
            # Save the information
            save_user_info(st.session_state.user_info["name"], st.session_state.user_info["email"])
            confirmation = f"Thank you for the information, {st.session_state.user_info['name']}! I've saved your details and you'll receive an email at {st.session_state.user_info['email']} soon."
            st.session_state.messages.append({"role": "assistant", "content": confirmation})
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(confirmation)
            # Reset the info collection state
            st.session_state.collecting_info = False
            st.session_state.user_info = {"name": None, "email": None}
    else:
        # Check if the user wants to subscribe or provide info
        if any(keyword in prompt.lower() for keyword in ["subscribe", "sign up", "provide info", "information", "register"]):
            st.session_state.collecting_info = True
            st.session_state.messages.append({"role": "assistant", "content": "Sure, I'd be happy to help you subscribe. Please provide your name:"})
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown("Sure, I'd be happy to help you subscribe. Please provide your name:")
        else:
            # Normal chat interaction
            try:
                chat_completion = client.chat.completions.create(
                    model=model_option,
                    messages=[
                        {
                            "role": m["role"],
                            "content": m["content"]
                        }
                        for m in st.session_state.messages
                        if m["role"] in ["system", "user", "assistant"]  # Only include these roles
                    ],
                    max_tokens=max_tokens,
                    stream=True
                )

                # Use the generator function with st.write_stream
                with st.chat_message("assistant", avatar="🤖"):
                    chat_responses_generator = generate_chat_responses(chat_completion)
                    full_response = st.write_stream(chat_responses_generator)
                
                # Append the full response to session_state.messages
                if isinstance(full_response, str):
                    st.session_state.messages.append(
                        {"role": "assistant", "content": full_response})
                else:
                    # Handle the case where full_response is not a string
                    combined_response = "\n".join(str(item) for item in full_response)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": combined_response})
            except Exception as e:
                st.error(e, icon="🚨")