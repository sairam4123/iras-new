from contextlib import contextmanager
from fuzzywuzzy import process
import logging
import sys

if sys.platform == "win32":
    import msvcrt
else:
    import select
    import termios
    import tty


class Font:
    reset_font = "\033[0m"
    bold_font = "\033[1m"
    faint_font = "\033[2m"
    italics_font = "\033[3m"
    underline_font = "\033[4m"
    slow_blink_font = "\033[5m"
    rapid_blink_font = "\033[6m"
    invert_font = "\033[7m"
    hide_font = "\033[8m"
    strike_font = "\033[9m"


logging.getLogger("root").setLevel(level=logging.ERROR)

# Escape sequences sent by the terminal (after "\x1b[") / by Windows (after "\xe0")
ansi_keys = {"A": "up", "B": "down", "C": "right", "D": "left"}
win_keys = {"H": "up", "P": "down", "M": "right", "K": "left"}

key_mean = {
    "\r": "enter",
    "\n": "enter",
    "\t": "tab",
    "\x7f": "backspace",
    "\x08": "backspace",
    "\x1b": "esc",
}


@contextmanager
def terminal_keys():
    """Read keys from this terminal one at a time, without echo."""
    if sys.platform == "win32":
        yield
        return
    fd = sys.stdin.fileno()
    old_attrs = termios.tcgetattr(fd)
    try:
        # cbreak keeps Ctrl+C working, unlike raw mode
        tty.setcbreak(fd)
        yield
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_attrs)


def read_key() -> str:
    if sys.platform == "win32":
        ch = msvcrt.getwch()
        if ch in ("\x00", "\xe0"):
            return win_keys.get(msvcrt.getwch(), "")
        if ch == "\x03":
            raise KeyboardInterrupt
        return key_mean.get(ch, ch)

    ch = sys.stdin.read(1)
    if ch == "\x1b":
        # a lone Esc has nothing following it; arrow keys send "\x1b[A" etc.
        if not select.select([sys.stdin], [], [], 0.05)[0]:
            return "esc"
        seq = sys.stdin.read(2)
        return ansi_keys.get(seq[1:], "") if seq.startswith("[") else ""
    return key_mean.get(ch, ch)


def render(prompt: str, selected_choice: str, suggestion: str) -> None:
    if suggestion.upper().startswith(selected_choice):
        hint = suggestion[len(selected_choice) :]
    else:
        hint = f"  ({suggestion})"
    print(
        f"\r\033[K{prompt}{selected_choice}{Font.faint_font}{hint}{Font.reset_font}",
        end="",
    )
    if hint:
        print(f"\033[{len(hint)}D", end="")
    print(end="", flush=True)


def autocomplete(prompt: str, options: set[str]) -> str:
    choice_idx = 0
    selected_choice = ""
    choices = process.extract(selected_choice, choices=options)
    render(prompt, selected_choice, choices[choice_idx][0])
    with terminal_keys():
        while True:
            key = read_key()
            if key == "esc":
                break
            if key == "enter":
                selected_choice = choices[choice_idx][0]
                render(prompt, selected_choice, selected_choice)
                break
            if key in ["up", "down"]:
                step = 1 if key == "down" else -1
                choice_idx = (choice_idx + step) % len(choices)
                render(prompt, selected_choice, choices[choice_idx][0])
                continue
            if key in ["tab", "right"]:
                selected_choice = choices[choice_idx][0]
            elif key == "backspace":
                selected_choice = selected_choice[:-1]
            elif len(key) == 1 and key.isprintable():
                selected_choice += key.upper()
            else:
                continue
            choice_idx = 0
            choices = process.extract(selected_choice, choices=options)
            render(prompt, selected_choice, choices[choice_idx][0])
    print()
    return selected_choice


if __name__ == "__main__":
    options = {"CFEPWDR-HB", "CFEPWDR-PR", "APLM-MELKU"}
    selected = autocomplete("Enter prodID: ", options)
    print(f"Selected: {selected}")
