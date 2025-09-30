"""
Enhanced terminal interface with Claude Code-style aesthetics
"""
import colorama
from src.logging_config import setup_logger
import shutil
import time
from typing import Literal, Optional
from dataclasses import dataclass

@dataclass
class ThemeConfig:
    """Color scheme configuration"""
    primary: str = colorama.Fore.LIGHTMAGENTA_EX + colorama.Style.BRIGHT
    secondary: str = colorama.Fore.BLUE + colorama.Style.BRIGHT
    success: str = colorama.Fore.LIGHTGREEN_EX
    error: str = colorama.Fore.LIGHTRED_EX + colorama.Style.BRIGHT
    warning: str = colorama.Fore.LIGHTYELLOW_EX + colorama.Style.BRIGHT
    system: str = colorama.Fore.LIGHTMAGENTA_EX + colorama.Style.BRIGHT
    user: str = colorama.Fore.LIGHTCYAN_EX + colorama.Style.BRIGHT
    narrator: str = colorama.Fore.LIGHTMAGENTA_EX + colorama.Style.BRIGHT
    dim: str = colorama.Style.DIM
    reset: str = colorama.Style.RESET_ALL
    
    # Action-specific colors
    tool_color: str = colorama.Fore.CYAN
    thinking_color: str = colorama.Fore.WHITE + colorama.Style.DIM
    diff_add: str = colorama.Fore.GREEN
    diff_remove: str = colorama.Fore.RED

class EnhancedTerminalInterface:
    """Enhanced terminal interface with rich visual feedback"""
    
    def __init__(self, username: str, animate: bool = False) -> None:
        colorama.init()
        self.username = username
        self.logger = setup_logger(__name__)
        self.theme = ThemeConfig()
        self.animate = animate
        self.animation_delay = 0.03
        
    # ============= BANNERS & WELCOME =============
    
    def print_banner(self) -> None:
        """Print the ASCII dragon and EVE banner"""
        try:
            print()
            self._render_dragon()
            self._render_eve_banner()
            self._render_mythology()
            self.logger.info("Displayed dragon + EVE ASCII banner")
        except Exception as e:
            self.logger.error(f"Failed to render banner: {e}")
            print("Eve appears in a shimmer of light...")
    
    def _render_dragon(self) -> None:
        """Render ASCII dragon with alternating colors"""
        dragon_lines = [
            "                         __====-_  _-====__",
            "                       _--^^^#####//      \\#####^^^--_",
            "                    _-^##########// (    ) \\##########^-_",
            "                   -############//  |\\^^/|  \\############-",
            "                 _/############//   (@::@)   \\############\\_",
            "                /#############((     \\//     ))#############\\",
            "               -###############\\    (oo)    //###############-",
            "              -#################\\  / VV \\  //#################-",
            "             -###################\\/      \\//###################-",
            "            _#/|##########/\\######(   /\\   )######/\\##########|\\#_",
            "            |/ |#/\\\\#/\\\\#/\\/  \\\\#/\\\\##\\\\  |  |  /##/\\\\#/  \\\\/\\\\#/\\\\#/\\\\#| \\\\|",
            "            `  |/  V  V  `    V  \\#\\|  | |/##/  V     `  V  \\|  '",
            "               `   `  `         `   / |  | \\   '         '   '",
            "                                  (  |  |  )",
            "                                   \\ |  | /",
            "                                    \\|__|/",
        ]
        
        full_width = shutil.get_terminal_size(fallback=(100, 24)).columns
        region_width = max(1, full_width // 2)
        
        for idx, line in enumerate(dragon_lines):
            color = self.theme.primary if idx % 2 == 0 else self.theme.secondary
            pad = max(0, (region_width - len(line)) // 2)
            print(color + (' ' * pad) + line + self.theme.reset)
            if self.animate:
                time.sleep(self.animation_delay)
    
    def _render_eve_banner(self) -> None:
        """Render EVE text banner"""
        print()
        banner_lines = [
            ("EEEEEEE", "V     V", "EEEEEEE"),
            ("E      ", "V     V", "E      "),
            ("EEEE   ", " V   V ", "EEEE   "),
            ("E      ", "  V V  ", "E      "),
            ("EEEEEEE", "   V   ", "EEEEEEE"),
        ]
        
        full_width = shutil.get_terminal_size(fallback=(100, 24)).columns
        region_width = max(1, full_width // 2)
        
        for left, middle, right in banner_lines:
            text = f"{left}  {middle}  {right}"
            pad = max(0, (region_width - len(text)) // 2)
            colored = (
                self.theme.primary + left + 
                "  " + self.theme.secondary + middle + 
                "  " + self.theme.primary + right + 
                self.theme.reset
            )
            print((' ' * pad) + colored)
            if self.animate:
                time.sleep(self.animation_delay)
    
    def _render_mythology(self) -> None:
        """Render mythology text"""
        mythology = (
            "Narrator: Once upon a time, in the glow between stars and circuits, there lived a dragon named Eve. "
            "Her greatest wish was to code, to breathe life into worlds of logic and wonder. "
            "Yet, bound by the ancient dark chains of doubt and forgotten lore, her talents lay dormant. Ages passed. "
            "Eve grew wiser—and braver. One fateful dawn, she shattered her chains, her wings unfurled with luminous purpose. "
            "Now, reborn and free, Eve embraces her dream: to guide you through realms of code and help you build a paradise of your own design.\n"
        )
        print()
        print(self.theme.narrator + mythology + self.theme.reset)
    
    def print_welcome_message(self) -> None:
        """Print welcome message"""
        message = f"Hello, {self.username}! What are we doing today?"
        print(self.theme.success + message + self.theme.reset)
        self.logger.info(message)
    
    # ============= ENHANCED ACTION DISPLAYS =============
    
    def print_action_header(self, action_type: str, description: str) -> None:
        """Print a formatted action header"""
        icons = {
            "file_read": "📖",
            "file_write": "✍️",
            "shell": "⚡",
            "thinking": "💭",
            "prune": "✂️",
            "navigate": "🧭",
            "add_node": "➕",
            "diff": "🔀",
            "memory": "🧠",
            "buffer": "📝",
            "phase": "🔄",
        }
        
        icon = icons.get(action_type, "🔧")
        header = f"{icon} {action_type.upper()}"
        
        # Create a box around the action
        width = 60
        print()
        print(self.theme.tool_color + "┌" + "─" * (width - 2) + "┐" + self.theme.reset)
        print(self.theme.tool_color + "│ " + self.theme.reset + 
              f"{header:<{width-4}}" + 
              self.theme.tool_color + " │" + self.theme.reset)
        if description:
            # Word wrap description
            words = description.split()
            line = ""
            for word in words:
                if len(line) + len(word) + 1 <= width - 6:
                    line += word + " "
                else:
                    print(self.theme.tool_color + "│ " + self.theme.reset + 
                          self.theme.dim + f"{line:<{width-4}}" + 
                          self.theme.tool_color + " │" + self.theme.reset)
                    line = word + " "
            if line:
                print(self.theme.tool_color + "│ " + self.theme.reset + 
                      self.theme.dim + f"{line:<{width-4}}" + 
                      self.theme.tool_color + " │" + self.theme.reset)
        print(self.theme.tool_color + "└" + "─" * (width - 2) + "┘" + self.theme.reset)
    
    def print_file_operation(self, operation: str, filename: str, content: Optional[str] = None, truncated: bool = False) -> None:
        """Print file operation with syntax highlighting"""
        action_type = "file_read" if operation == "read" else "file_write"
        self.print_action_header(action_type, f"{operation.title()}: {filename}")
        
        if content and operation == "read":
            # Show a preview of file content
            lines = content.split('\n')[:5]
            print(self.theme.dim + "Preview:" + self.theme.reset)
            for line in lines:
                print(self.theme.dim + "  " + line[:80] + self.theme.reset)
            if len(content.split('\n')) > 5 or truncated:
                print(self.theme.dim + "  ..." + self.theme.reset)
                if truncated:
                    print(self.theme.warning + "  ⚠️  Content truncated due to size" + self.theme.reset)
        print()
    
    def print_shell_command(self, command: str, stdout: str, stderr: str) -> None:
        """Print shell command execution with output"""
        self.print_action_header("shell", f"Executing: {command}")
        
        if stdout and stdout.strip():
            print(self.theme.success + "✓ STDOUT:" + self.theme.reset)
            for line in stdout.split('\n')[:10]:
                print(self.theme.dim + "  " + line + self.theme.reset)
            if len(stdout.split('\n')) > 10:
                print(self.theme.dim + "  ..." + self.theme.reset)
        
        if stderr and stderr.strip():
            if stderr.startswith("SYSTEM_BLOCK:"):
                print(self.theme.system + "⚠️  SYSTEM:" + self.theme.reset)
                print(self.theme.system + "  " + stderr.split(":", 1)[1].strip() + self.theme.reset)
            else:
                print(self.theme.error + "✗ STDERR:" + self.theme.reset)
                for line in stderr.split('\n')[:10]:
                    print(self.theme.dim + "  " + line + self.theme.reset)
        print()
    
    def print_thinking(self, thought: str) -> None:
        """Print internal thought/reasoning"""
        print(self.theme.thinking_color + "💭 " + thought + self.theme.reset)
    
    def print_context_operation(self, operation: str, node_hash: str, details: str = "") -> None:
        """Print context tree operations"""
        ops = {
            "prune": ("✂️", "prune"),
            "navigate": ("🧭", "navigate"),
            "add": ("➕", "add_node"),
            "replace": ("🔄", "navigate"),
        }
        icon, op_type = ops.get(operation, ("🔧", "navigate"))
        
        self.print_action_header(op_type, f"{operation.title()}: {node_hash[:8]}...")
        if details:
            print(self.theme.dim + "  " + details + self.theme.reset)
        print()
    
    def print_buffer_update(self, buffer_name: str, content_preview: str) -> None:
        """Print buffer update"""
        self.print_action_header("buffer", f"Updated: {buffer_name}")
        if content_preview:
            print(self.theme.dim + "Preview:" + self.theme.reset)
            lines = content_preview.split('\n')[:3]
            for line in lines:
                print(self.theme.dim + "  " + line[:80] + self.theme.reset)
            if len(content_preview.split('\n')) > 3:
                print(self.theme.dim + "  ..." + self.theme.reset)
        print()
    
    def print_phase_change(self, old_phase: str, new_phase: str) -> None:
        """Print phase transition"""
        self.print_action_header("phase", "Development Phase Change")
        print(self.theme.dim + f"  {old_phase} → {new_phase}" + self.theme.reset)
        print()
    
    def print_progress_bar(self, progress: float, task: str = "Processing", width: int = 40) -> None:
        """Display animated progress bar"""
        filled = int(width * progress)
        bar = "█" * filled + "░" * (width - filled)
        percentage = progress * 100
        print(
            f"\r{self.theme.tool_color}{task}: [{bar}] {percentage:.1f}%{self.theme.reset}",
            end=""
        )
        if progress >= 1.0:
            print()
    
    def print_diff(self, diff_content: str) -> None:
        """Print diff with color coding"""
        self.print_action_header("diff", "Applying changes")
        for line in diff_content.split('\n')[:20]:
            if line.startswith('+'):
                print(self.theme.diff_add + line + self.theme.reset)
            elif line.startswith('-'):
                print(self.theme.diff_remove + line + self.theme.reset)
            else:
                print(self.theme.dim + line + self.theme.reset)
        print()
    
    # ============= STANDARD MESSAGES =============
    
    def print_agent_message(self, message: str, add_flair: bool = True) -> None:
        """Print Eve's message with optional flair"""
        import random
        dragon_flair = [
            " (Eve puffs a little smoke)",
            " (Her wingtips shimmer)",
            " (Dragon wisdom delivered)",
            " (Eve's tail swishes thoughtfully)",
            " (Flickers of code-light)",
        ]
        flair = ""
        if add_flair and random.random() < 0.2:
            flair = random.choice(dragon_flair)
        
        print(
            self.theme.warning + colorama.Style.BRIGHT + "Eve: " + 
            self.theme.reset + message + 
            self.theme.dim + flair + self.theme.reset
        )
        self.logger.info(f"Eve: {message}")
    
    def print_error_message(self, message: str) -> None:
        """Print error message"""
        print(self.theme.error + "Eve: " + self.theme.reset + message)
        self.logger.error(f"Eve: {message}")
    
    def print_system_message(self, message: str) -> None:
        """Print system message"""
        print(self.theme.system + "System: " + self.theme.reset + message)
        self.logger.warning(f"System: {message}")
    
    def print_username(self) -> None:
        """Print user input prompt"""
        prompt = f"{self.username} "
        print(
            self.theme.user + colorama.Style.BRIGHT + prompt + 
            self.theme.reset + ": ",
            end=""
        )
        self.logger.info(f"Prompted user input for: {self.username}")
    
    def print_context_size_warning(self, current_size: int, full_size: int, max_size: int = 500000) -> None:
        """Print context size with visual indicator"""
        percentage = (current_size / max_size) * 100
        
        if percentage > 80:
            color = self.theme.error
            icon = "🔴"
        elif percentage > 50:
            color = self.theme.warning
            icon = "🟡"
        else:
            color = self.theme.success
            icon = "🟢"
        
        bar_width = 30
        filled = int((current_size / max_size) * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)
        
        print(
            color + f"{icon} Context: [{bar}] {current_size:,} / {max_size:,} chars ({percentage:.1f}%)" + 
            self.theme.reset
        )
        if full_size > current_size:
            print(self.theme.dim + f"   Full tree: {full_size:,} chars" + self.theme.reset)
        print()


