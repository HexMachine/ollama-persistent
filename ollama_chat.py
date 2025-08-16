import json
import os
import sys
import shutil
from datetime import datetime
from typing import List, Dict, Optional
import ollama
from colorama import init, Fore, Style

# Try to import readline for better input handling (Unix/Linux/macOS)
try:
    import readline
    # Configure readline to minimize display issues
    readline.parse_and_bind("set horizontal-scroll-mode on")  # Prevent line wrapping in readline
    readline.parse_and_bind("set show-all-if-ambiguous on")
    # Limit history to prevent excessive memory usage with very long lines
    readline.set_history_length(50)
    READLINE_AVAILABLE = True
except ImportError:
    # Windows fallback
    try:
        import pyreadline as readline
        readline.parse_and_bind("set horizontal-scroll-mode on")
        readline.set_history_length(50)
        READLINE_AVAILABLE = True
    except ImportError:
        READLINE_AVAILABLE = False
        pass

# Initialize colorama for cross-platform colored output
init(autoreset=True)


class PersistentOllamaChat:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.chat_history_file = os.path.join(data_dir, "chat_history.json")
        self.system_prompt_file = os.path.join(data_dir, "system_prompt.txt")
        self.config_file = os.path.join(data_dir, "config.json")
        
        # Get terminal width for proper text wrapping
        self.terminal_width = shutil.get_terminal_size().columns
        
        # Ensure data directory exists
        os.makedirs(data_dir, exist_ok=True)
        
        # Initialize files if they don't exist
        self._initialize_files()
        
        # Load configuration
        self.config = self._load_config()
        
        # Load system prompt and chat history
        self.system_prompt = self._load_system_prompt()
        self.chat_history = self._load_chat_history()
        
        # Configure readline if available
        if READLINE_AVAILABLE:
            self._configure_readline()
    
    def _configure_readline(self):
        """Configure readline for better input handling."""
        try:
            # Set up history
            readline.set_history_length(1000)
            
            # Configure readline to handle long lines better
            readline.parse_and_bind('set horizontal-scroll-mode off')
            readline.parse_and_bind('set editing-mode emacs')
            
            # Note: Removed key bindings that caused syntax warnings
            # Default readline bindings work fine for our purposes
            
        except Exception as e:
            # If readline configuration fails, we'll continue without it
            pass
    
    def _print_wrapped_response(self, text: str, color: str = Fore.WHITE):
        """Print response text."""
        # Print line by line to maintain color formatting
        lines = text.split('\n')
        for line in lines:
            print(f"{color}{line}")
    
    def _format_input_preview(self, text: str, max_preview: int = 80) -> str:
        """Format input preview with word wrapping awareness."""
        if len(text) <= max_preview:
            return text
        
        # Find a good breaking point (space) before max_preview
        break_point = max_preview
        for i in range(max_preview - 20, max_preview):
            if i < len(text) and text[i] == ' ':
                break_point = i
                break
        
        preview = text[:break_point].rstrip()
        return f"{preview}..."
    
    def _multiline_input(self) -> str:
        """Handle multi-line input to avoid readline display issues."""
        print(f"\n{Fore.CYAN}Multi-line input mode:")
        print(f"{Fore.YELLOW}• Type your message across multiple lines")
        print(f"{Fore.YELLOW}• Press Ctrl+D (or Ctrl+Z on Windows) when finished")
        print(f"{Fore.YELLOW}• Or type 'END' on a line by itself")
        print(f"{Fore.CYAN}{'─' * 40}")
        
        lines = []
        try:
            while True:
                try:
                    line = input()
                    if line.strip() == 'END':
                        break
                    lines.append(line)
                except EOFError:
                    break
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Multi-line input cancelled")
            return ""
        
        result = '\n'.join(lines).strip()
        print(f"{Fore.CYAN}{'─' * 40}")
        print(f"{Fore.GREEN}Multi-line input captured ({len(result)} characters)")
        return result

    def _read_file_input(self) -> str:
        """Read content from a file to use as input."""
        print(f"\n{Fore.CYAN}File input mode:")
        print(f"{Fore.YELLOW}Enter the path to a text file to use as input:")
        
        try:
            # Get file path from user
            file_path = input(f"{Fore.WHITE}File path: ").strip()
            
            if not file_path:
                print(f"{Fore.YELLOW}No file path provided.")
                return ""
            
            # Expand user path (~ becomes home directory)
            file_path = os.path.expanduser(file_path)
            
            # Check if file exists
            if not os.path.exists(file_path):
                print(f"{Fore.RED}Error: File '{file_path}' does not exist.")
                return ""
            
            # Check if it's a file (not a directory)
            if not os.path.isfile(file_path):
                print(f"{Fore.RED}Error: '{file_path}' is not a file.")
                return ""
            
            # Read the file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            if not content:
                print(f"{Fore.YELLOW}Warning: File '{file_path}' is empty.")
                return ""
            
            print(f"{Fore.GREEN}File content loaded ({len(content)} characters)")
            print(f"{Fore.CYAN}Preview: {content[:100]}{'...' if len(content) > 100 else ''}")
            
            return content
            
        except UnicodeDecodeError:
            print(f"{Fore.RED}Error: Could not read file as text (encoding issue).")
            return ""
        except PermissionError:
            print(f"{Fore.RED}Error: Permission denied reading file '{file_path}'.")
            return ""
        except Exception as e:
            print(f"{Fore.RED}Error reading file: {e}")
            return ""

    def _clean_input(self, text: str) -> str:
        """Clean input text of control sequences and artifacts."""
        import re
        
        if not text:
            return ""
        
        # Remove ANSI escape sequences (like arrow key codes)
        # This covers: \x1b[A, \x1b[B, \x1b[C, \x1b[D and similar
        ansi_pattern = r'\x1b\[[0-9;]*[a-zA-Z]'
        cleaned = re.sub(ansi_pattern, '', text)
        
        # Remove control sequences that appear as text (from readline issues)
        # This covers: ^[[A, ^[[B, ^[[C, ^[[D and similar
        control_pattern = r'\^?\[\[[0-9;]*[a-zA-Z]'
        cleaned = re.sub(control_pattern, '', cleaned)
        
        # Remove other problematic control characters
        cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', cleaned)
        
        # Clean up multiple spaces and normalize whitespace
        cleaned = ' '.join(cleaned.split())
        
        return cleaned.strip()

    def _reset_terminal_display(self):
        """Reset terminal display to clear any artifacts."""
        try:
            # Clear current line completely
            print(f"\r\x1b[K", end='')
            # Move up one line and clear if needed
            print(f"\x1b[1A\x1b[K", end='')
            # Move back down
            print(f"\x1b[1B", end='')
            sys.stdout.flush()
        except:
            # Fallback - just clear with spaces
            print(f"\r{' ' * self.terminal_width}\r", end='')
            sys.stdout.flush()

    def _safe_input(self, prompt: str) -> str:
        """Safe input method that handles multi-line display issues."""
        try:
            # Put the prompt on its own line to avoid readline display offset issues
            print(f"{Fore.BLUE}You:")
            
            try:
                # Use a simple prompt for the actual input line
                user_input = input()
                    
            except (EOFError, KeyboardInterrupt):
                # Re-raise these to be handled by the main loop
                raise
            except Exception as e:
                print(f"{Fore.YELLOW}Input error: {e}")
                return ""
            
            # Clean the input aggressively to remove any artifacts
            user_input = self._clean_input(user_input)
            
            return user_input.strip()
                
        except (EOFError, KeyboardInterrupt):
            raise
        except Exception as e:
            # If there's any input issue, fall back to basic input
            try:
                user_input = input(f"{Fore.BLUE}You (fallback): ").strip()
                return self._clean_input(user_input)
            except:
                return ""
        
    def _initialize_files(self):
        """Initialize default files if they don't exist."""
        if not os.path.exists(self.system_prompt_file):
            default_system_prompt = "You are a helpful AI assistant. You maintain context across conversations and remember previous discussions."
            with open(self.system_prompt_file, 'w', encoding='utf-8') as f:
                f.write(default_system_prompt)
        
        if not os.path.exists(self.chat_history_file):
            with open(self.chat_history_file, 'w', encoding='utf-8') as f:
                json.dump([], f, indent=2)
                
        if not os.path.exists(self.config_file):
            default_config = {
                "last_model": "",
                "max_history_length": 100,
                "created_at": datetime.now().isoformat()
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2)
    
    def _load_config(self) -> Dict:
        """Load configuration from file."""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"last_model": "", "max_history_length": 100}
    
    def _save_config(self):
        """Save configuration to file."""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2)
    
    def _load_system_prompt(self) -> str:
        """Load system prompt from file."""
        try:
            with open(self.system_prompt_file, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            return "You are a helpful AI assistant."
    
    def _save_system_prompt(self, prompt: str):
        """Save system prompt to file."""
        with open(self.system_prompt_file, 'w', encoding='utf-8') as f:
            f.write(prompt)
    
    def _load_chat_history(self) -> List[Dict]:
        """Load chat history from file."""
        try:
            with open(self.chat_history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
                # Limit history length
                max_length = self.config.get('max_history_length', 100)
                if len(history) > max_length:
                    history = history[-max_length:]
                    self._save_chat_history(history)
                return history
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def _save_chat_history(self, history: List[Dict] = None):
        """Save chat history to file."""
        if history is None:
            history = self.chat_history
        
        with open(self.chat_history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    
    def _add_to_history(self, role: str, content: str):
        """Add a message to chat history."""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        self.chat_history.append(message)
        
        # Trim history if too long
        max_length = self.config.get('max_history_length', 100)
        if len(self.chat_history) > max_length:
            self.chat_history = self.chat_history[-max_length:]
        
        self._save_chat_history()
    
    def get_available_models(self) -> List[str]:
        """Get list of available Ollama models."""
        try:
            response = ollama.list()
            # Handle different response formats
            if isinstance(response, dict) and 'models' in response:
                return [model['name'] for model in response['models']]
            elif isinstance(response, list):
                # If response is directly a list of models
                return [model['name'] if isinstance(model, dict) else str(model) for model in response]
            else:
                # Fallback: use CLI to get models
                import subprocess
                result = subprocess.run(['ollama', 'list'], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')[1:]  # Skip header
                    models = []
                    for line in lines:
                        if line.strip():
                            model_name = line.split()[0]  # First column is the model name
                            models.append(model_name)
                    return models
                return []
        except Exception as e:
            print(f"{Fore.RED}Error fetching models via API, trying CLI: {e}")
            try:
                # Fallback to CLI
                import subprocess
                result = subprocess.run(['ollama', 'list'], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')[1:]  # Skip header
                    models = []
                    for line in lines:
                        if line.strip():
                            model_name = line.split()[0]  # First column is the model name
                            models.append(model_name)
                    return models
            except Exception as cli_e:
                print(f"{Fore.RED}Error fetching models via CLI: {cli_e}")
            return []
    
    def select_model(self) -> str:
        """Allow user to select a model."""
        models = self.get_available_models()
        
        if not models:
            print(f"{Fore.RED}No Ollama models found. Please install a model first using 'ollama pull <model_name>'")
            return ""
        
        print(f"\n{Fore.CYAN}Available models:")
        for i, model in enumerate(models, 1):
            marker = f"{Fore.GREEN}(last used)" if model == self.config.get('last_model') else ""
            print(f"  {i}. {model} {marker}")
        
        while True:
            try:
                choice = input(f"\n{Fore.YELLOW}Select model (1-{len(models)}) or press Enter for last used: ").strip()
                
                if not choice and self.config.get('last_model'):
                    return self.config['last_model']
                elif not choice:
                    print(f"{Fore.RED}No previous model found. Please select a model.")
                    continue
                
                index = int(choice) - 1
                if 0 <= index < len(models):
                    selected_model = models[index]
                    self.config['last_model'] = selected_model
                    self._save_config()
                    return selected_model
                else:
                    print(f"{Fore.RED}Invalid selection. Please choose 1-{len(models)}")
            except ValueError:
                print(f"{Fore.RED}Invalid input. Please enter a number.")
    
    def _prepare_messages_for_ollama(self) -> List[Dict]:
        """Prepare messages for Ollama API including system prompt and history."""
        messages = []
        
        # Add system prompt
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        
        # Add chat history (excluding system messages to avoid duplication)
        for msg in self.chat_history:
            if msg["role"] != "system":
                messages.append({"role": msg["role"], "content": msg["content"]})
        
        return messages
    
    def chat_with_model(self, model_name: str, user_input: str) -> str:
        """Send a message to the model and get response with streaming."""
        try:
            # Add user message to history
            self._add_to_history("user", user_input)
            
            # Prepare messages for API
            messages = self._prepare_messages_for_ollama()
            messages.append({"role": "user", "content": user_input})
            
            # Get streaming response from Ollama
            print(f"{Fore.GREEN}Assistant:")
            
            assistant_response = ""
            
            # Use streaming to show response as it generates
            stream = ollama.chat(
                model=model_name,
                messages=messages,
                stream=True
            )
            
            for chunk in stream:
                if 'message' in chunk and 'content' in chunk['message']:
                    content = chunk['message']['content']
                    assistant_response += content
                    print(f"{Fore.WHITE}{content}", end="", flush=True)
            
            print()  # Ensure we end with a newline
            
            # Add assistant response to history
            self._add_to_history("assistant", assistant_response)
            
            return assistant_response
            
        except Exception as e:
            error_msg = f"Error communicating with model: {e}"
            print(f"\n{Fore.RED}{error_msg}")
            return error_msg
    
    def display_chat_summary(self):
        """Display a summary of the chat history."""
        if not self.chat_history:
            print(f"{Fore.YELLOW}No previous chat history found.")
            return
        
        print(f"\n{Fore.CYAN}=== Chat History Summary ===")
        print(f"{Fore.GREEN}Total messages: {len(self.chat_history)}")
        
        # Show last few messages
        recent_messages = self.chat_history[-5:] if len(self.chat_history) > 5 else self.chat_history
        
        print(f"\n{Fore.CYAN}Recent messages:")
        for msg in recent_messages:
            role_color = Fore.BLUE if msg["role"] == "user" else Fore.GREEN
            timestamp = msg.get("timestamp", "Unknown time")
            
            # Use word-aware preview for content
            content_preview = self._format_input_preview(msg["content"], 100)
            
            # Display the preview
            role_label = f"{msg['role'].capitalize()}:"
            
            print(f"  {role_color}{role_label} {Fore.WHITE}{content_preview}")
        
        if len(self.chat_history) > 5:
            print(f"  {Fore.YELLOW}... and {len(self.chat_history) - 5} more messages")
    
    def edit_system_prompt(self):
        """Allow user to edit the system prompt."""
        print(f"\n{Fore.CYAN}Current system prompt:")
        print(f"{Fore.WHITE}{self.system_prompt}")
        
        print(f"\n{Fore.YELLOW}Enter new system prompt (or press Enter to keep current):")
        new_prompt = input().strip()
        
        if new_prompt:
            self.system_prompt = new_prompt
            self._save_system_prompt(new_prompt)
            print(f"{Fore.GREEN}System prompt updated!")
        else:
            print(f"{Fore.YELLOW}System prompt unchanged.")
    
    def clear_history(self):
        """Clear chat history after confirmation."""
        confirm = input(f"{Fore.YELLOW}Are you sure you want to clear all chat history? (yes/no): ").strip().lower()
        
        if confirm == 'yes':
            self.chat_history = []
            self._save_chat_history()
            print(f"{Fore.GREEN}Chat history cleared!")
        else:
            print(f"{Fore.YELLOW}Chat history preserved.")
    
    def run(self):
        """Main chat loop."""
        print(f"{Fore.CYAN}🤖 Persistent Ollama Chat")
        print(f"{Fore.CYAN}========================")
        
        # Display chat summary
        self.display_chat_summary()
        
        # Select model
        model_name = self.select_model()
        if not model_name:
            return
        
        print(f"\n{Fore.GREEN}Using model: {model_name}")
        print(f"{Fore.GREEN}System prompt loaded from: {self.system_prompt_file}")
        print(f"{Fore.GREEN}Chat history loaded from: {self.chat_history_file}")
        
        if READLINE_AVAILABLE:
            print(f"{Fore.CYAN}✅ Enhanced input mode: Arrow keys enabled (optimized for long text)")
            print(f"{Fore.YELLOW}💡 Note: For very long inputs, use /multiline or /file to avoid display issues")
        else:
            print(f"{Fore.YELLOW}⚠️  Basic input mode: Arrow key navigation not available")
        
        print(f"\n{Fore.YELLOW}Commands:")
        print(f"  /help     - Show this help")
        print(f"  /system   - Edit system prompt")
        print(f"  /clear    - Clear chat history")
        print(f"  /summary  - Show chat summary")
        print(f"  /multiline- Enter multi-line input mode")
        print(f"  /file     - Read input from a text file")
        print(f"  /quit     - Exit the chat")
        print(f"  /goodbye  - End session with farewell")
        print(f"\n{Fore.CYAN}Start chatting! (Type your message and press Enter)")
        print("=" * 50)
        
        while True:
            try:
                # Use safe input method to handle multi-line display issues
                user_input = self._safe_input(f"\n{Fore.BLUE}You: ")
                
                # Skip empty input
                if not user_input:
                    # Clear any display artifacts from empty input
                    print(f"\r{' ' * self.terminal_width}\r", end='', flush=True)
                    continue
                
                # Additional validation for problematic input
                if len(user_input.strip()) == 0:
                    continue
                
                # Handle commands
                if user_input.lower() in ['/quit', '/goodbye']:
                    if user_input.lower() == '/goodbye':
                        print(f"{Fore.MAGENTA}Goodbye! Thank you for chatting. Your conversation history has been preserved for next time. 👋")
                    else:
                        print(f"{Fore.GREEN}Goodbye! Your chat history has been saved.")
                    break
                elif user_input.lower() == '/help':
                    print(f"\n{Fore.YELLOW}Commands:")
                    print(f"  /help     - Show this help")
                    print(f"  /system   - Edit system prompt")
                    print(f"  /clear    - Clear chat history")
                    print(f"  /summary  - Show chat summary")
                    print(f"  /multiline- Enter multi-line input mode")
                    print(f"  /file     - Read input from a text file")
                    print(f"  /quit     - Exit the chat")
                    print(f"  /goodbye  - End session with farewell")
                    continue
                elif user_input.lower() == '/multiline':
                    multiline_input = self._multiline_input()
                    if multiline_input:
                        user_input = multiline_input
                    else:
                        continue
                elif user_input.lower() == '/file':
                    file_input = self._read_file_input()
                    if file_input:
                        user_input = file_input
                    else:
                        continue
                elif user_input.lower() == '/system':
                    self.edit_system_prompt()
                    continue
                elif user_input.lower() == '/clear':
                    self.clear_history()
                    continue
                elif user_input.lower() == '/summary':
                    self.display_chat_summary()
                    continue
                
                # Get response from model with streaming
                self.chat_with_model(model_name, user_input)
                
            except KeyboardInterrupt:
                print(f"\n{Fore.GREEN}Chat interrupted. Your history has been saved. Goodbye!")
                break
            except EOFError:
                print(f"\n{Fore.GREEN}Chat ended. Your history has been saved. Goodbye!")
                break


def main():
    """Main entry point."""
    try:
        chat = PersistentOllamaChat()
        chat.run()
    except Exception as e:
        print(f"{Fore.RED}An error occurred: {e}")


if __name__ == "__main__":
    main()
