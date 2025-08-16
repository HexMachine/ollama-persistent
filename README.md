# Persistent Ollama Chat

A Python application that maintains persistent chat sessions with Ollama models across multiple runs. The system retains chat history and system prompts in static files, allowing conversations to continue seamlessly between sessions.

## Features

- **Persistent Chat History**: All conversations are saved and loaded automatically
- **Flexible Model Selection**: Choose any available Ollama model for each session
- **System Prompt Management**: Set and edit system prompts that persist across sessions
- **Interactive Commands**: Built-in commands for managing chat history and settings
- **Colorized Output**: Easy-to-read colored terminal output
- **History Management**: Automatic history trimming and manual clearing options
- **Streaming Responses**: See AI responses as they generate in real-time
- **Enhanced Input**: Arrow key navigation and text editing (Unix/Linux/macOS)
- **Multiple Exit Options**: Use `/quit` or `/goodbye` to end sessions
- **Smart Word Wrapping**: Text breaks naturally at word boundaries, never splitting words
- **Responsive Layout**: Adapts to terminal width for optimal readability

## Installation

1. Make sure you have Ollama installed and running:
   ```bash
   # Install Ollama (if not already installed)
   curl -fsSL https://ollama.ai/install.sh | sh
   
   # Pull a model (example)
   ollama pull llama2
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the chat application:

```bash
python ollama_chat.py
```

### Interactive Commands

While in the chat, you can use these commands:

- `/help` - Show available commands
- `/system` - Edit the system prompt
- `/clear` - Clear all chat history
- `/summary` - Show chat history summary
- `/quit` - Exit the application
- `/goodbye` - End session with a farewell message

### Enhanced Features

- **Streaming Output**: Responses appear as the model generates them, not all at once
- **Cursor Navigation**: Use arrow keys to move through text before submitting (Unix/Linux/macOS)
- **Input History**: Use up/down arrows to navigate through previous commands

### File Structure

The application creates a `data/` directory with the following files:

- `chat_history.json` - Stores all chat messages with timestamps
- `system_prompt.txt` - Contains the system prompt for the AI
- `config.json` - Stores configuration including last used model

## Configuration

### System Prompt

Edit the system prompt by:
1. Using the `/system` command in the chat
2. Directly editing `data/system_prompt.txt`

### History Length

Modify `max_history_length` in `data/config.json` to change how many messages are retained.

### Default System Prompt

The default system prompt is: "You are a helpful AI assistant. You maintain context across conversations and remember previous discussions."

## How It Works

1. **Session Initialization**: 
   - Loads existing chat history and system prompt
   - Displays a summary of previous conversations
   - Allows model selection from available Ollama models

2. **Conversation Flow**:
   - Each user message is added to the persistent history
   - The complete context (system prompt + history + new message) is sent to Ollama
   - Assistant responses are saved to history
   - All data is immediately written to disk

3. **Persistence**:
   - Chat history is automatically saved after each message
   - System prompt changes are immediately persisted
   - Configuration updates are saved when models are selected

## Example Session

```
🤖 Persistent Ollama Chat
========================

=== Chat History Summary ===
Total messages: 12

Recent messages:
  User: What is machine learning?
  Assistant: Machine learning is a subset of artificial intelligence...
  User: Can you give me some examples?
  Assistant: Certainly! Here are some common examples...

Available models:
  1. llama2 (last used)
  2. codellama
  3. mistral

Select model (1-3) or press Enter for last used: 

Using model: llama2
System prompt loaded from: data/system_prompt.txt
Chat history loaded from: data/chat_history.json

Commands:
  /help    - Show this help
  /system  - Edit system prompt  
  /clear   - Clear chat history
  /summary - Show chat summary
  /quit    - Exit the chat

Start chatting! (Type your message and press Enter)
==================================================

You: Remember our previous discussion about machine learning?
