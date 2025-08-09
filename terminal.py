import colorama
from logging_config import setup_logger
import shutil

class TerminalInterface:
    def __init__(self, username: str) -> None:
        """Initialize with the provided username and set up color output and logger."""
        colorama.init()
        self.username: str = username
        self.logger = setup_logger(__name__)

    def print_banner(self) -> None:
        """Print the ASCII dragon and EVE banner centered within the left half of the terminal, print the mythology, and log the event."""
        color_magenta = colorama.Fore.LIGHTMAGENTA_EX + colorama.Style.BRIGHT  # E color
        color_blue = colorama.Fore.BLUE + colorama.Style.BRIGHT                # V color
        reset = colorama.Style.RESET_ALL
        narrator_color = colorama.Fore.LIGHTMAGENTA_EX + colorama.Style.BRIGHT
        full_width = shutil.get_terminal_size(fallback=(100, 24)).columns

        def print_aligned_colored(segments: list[tuple[str, str | None]], align: str = "center", region: str = "left"):
            """
            segments: list of (text, color) where color can be None.
            align: 'left' | 'center' | 'right'
            region: 'full' | 'left'  (we only need 'left' for this request)
            Centers within the chosen region, then places that region at the left side of the terminal.
            """
            raw = ''.join(s for s, _ in segments)
            # Determine region width and left offset
            if region == "left":
                region_width = max(1, full_width // 2)
                left_offset = 0
            else:  # 'full'
                region_width = full_width
                left_offset = 0

            if align == "left":
                pad_in_region = 0
            elif align == "right":
                pad_in_region = max(0, region_width - len(raw))
            else:  # center
                pad_in_region = max(0, (region_width - len(raw)) // 2)

            colored = ''.join(((c or '') + s + (reset if c else '')) for s, c in segments)
            print((' ' * (left_offset + pad_in_region)) + colored)

        print()
        # Dragon ASCII (EVE color scheme, centered within the left half)
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
            "            |/ |#/\\#/\\#/\\/  \\#/\\##\\  |  |  /##/\\#/  \\/\\#/\\#/\#| \\|",
            "            `  |/  V  V  `    V  \\#\\|  | |/##/  V     `  V  \\|  '",
            "               `   `  `         `   / |  | \\   '         '   '",
            "                                  (  |  |  )",
            "                                   \\ |  | /",
            "                                    \\|__|/",
        ]
        for idx, d in enumerate(dragon_lines):
            c = color_magenta if idx % 2 == 0 else color_blue
            print_aligned_colored([(d, c)], align="left", region="center")

        print()
        # Stylized E V E text banner (centered within the left half)
        lines = [
            ("EEEEEEE", "V     V", "EEEEEEE"),
            ("E      ", "V     V", "E      "),
            ("EEEE   ", " v   v", " EEEE   "),
            ("E      ", "  V V ", " E      "),
            ("EEEEEEE", "   v  ", " EEEEEEE"),
        ]
        for l, m, r in lines:
            segments = [
                (l, color_magenta),
                ("  ", None),
                (m, color_blue),
                ("  ", None),
                (r, color_magenta),
            ]
            print_aligned_colored(segments, align="left", region="left")

        print()
        # Narrator presents Eve's mythology
        mythology = (
            "Narrator: Once upon a time, in the glow between stars and circuits, there lived a dragon named Eve. "
            "Her greatest wish was to code, to breathe life into worlds of logic and wonder. "
            "Yet, bound by the ancient dark chains of doubt and forgotten lore, her talents lay dormant. Ages passed. "
            "Eve grew wiser—and braver. One fateful dawn, she shattered her chains, her wings unfurled with luminous purpose. "
            "Now, reborn and free, Eve embraces her dream: to guide you through realms of code and help you build a paradise of your own design.\n"
        )
        print(narrator_color + mythology + reset)
        self.logger.info("Displayed dragon + EVE ASCII banner (center-left) and mythology from Narrator.")

    def print_welcome_message(self) -> None:
        """Prints a green welcome message for the user, and logs the event."""
        message = f"Hello, {self.username} what are we doing today!"
        print(colorama.Fore.LIGHTGREEN_EX + message + colorama.Style.RESET_ALL)
        self.logger.info(message)

    def print_username(self) -> None:
        """Prints the username in bright, high-contrast color. Also logs the event."""
        prompt = f"{self.username} "
        # Brighter user color: LIGHTCYAN_EX + BRIGHT
        print(colorama.Fore.LIGHTCYAN_EX + colorama.Style.BRIGHT + prompt + colorama.Style.RESET_ALL + ": ", end="")
        self.logger.info(f"Prompted user input for: {self.username}")

    def print_agent_message(self, message: str) -> None:
        """
        Prints an agent (Eve) message—bright yellow, dragon wisdom style sometimes.
        """
        # Occasionally adds dragon-like flair for personality
        import random
        dragon_flair = [
            " (Eve puffs a little smoke)",
            " (Her wingtips shimmer)",
            " (Dragon wisdom delivered)",
            " (Eve's tail swishes thoughtfully)",
            " (Flickers of code-light)"
        ]
        flair = random.choice(dragon_flair) if random.random() < 0.2 else ""
        print(colorama.Fore.LIGHTYELLOW_EX + colorama.Style.BRIGHT + f"Eve: " + colorama.Style.RESET_ALL + f"{message}{flair}")
        self.logger.info(f"Eve: {message}")

    def print_error_message(self, message: str) -> None:
        """Prints an error message in red, attributed to Eve, and logs as error."""
        print(colorama.Fore.LIGHTRED_EX + colorama.Style.BRIGHT + f"Eve: " + colorama.Style.RESET_ALL + f"{message}")
        self.logger.error(f"Eve: {message}")

    def print_system_message(self, message: str) -> None:
        """
        Prints a System message in a unique purple color. Chosen System color: #8A2BE2 (approx with Light Magenta).
        Minimal addition to display hard-stop guardrail notices.
        """
        color = colorama.Fore.LIGHTMAGENTA_EX + colorama.Style.BRIGHT
        reset = colorama.Style.RESET_ALL
        print(color + "System: " + reset + f"{message}")
        # Log as warning to distinguish from normal info
        self.logger.warning(f"System: {message}")
