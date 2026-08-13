import keyboard
from fuzzywuzzy import process
import logging

# from t import print


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

key_mean = {
    "space": " ",
    "backspace": "\b \b",
    "enter": "\n",
    "up": "\033[1A",
    "down": "\033[1B",
    "left": "\033[1C",
    "right": "\033[1D",
}

# print("Enter prodID: ", end="", flush=True)

# prod_id = ""


def autocomplete(prompt: str, options: set[str]) -> str:
    print(prompt, end="", flush=True)
    choice_idx = 0
    reset = False
    selected_choice = ""
    while True:
        if keyboard.is_pressed("esc"):
            break
        if not selected_choice and not reset:
            choice_idx = 0
            reset = True
        choices = process.extract(selected_choice, choices=options)
        key = keyboard.read_event(True)
        # print(key)
        if key.event_type == "up":
            continue
        if keyboard.is_modifier(key.name):
            continue
        key_str = key_mean.get(key.name, key.name)
        if key_str == "esc":
            break
        if key_str == "\n":
            print(f"\033[{len(selected_choice)}D", end="")
            print(choices[choice_idx][0], end="")
            print(key_str, end="")
            selected_choice = choices[choice_idx][0]
            break
        if key.name in ["up", "down", "right", "left"]:
            if key.name == "down":
                choice_idx = (choice_idx + 1) % len(choices)
                print(f"\033[{len(selected_choice)}D", end="")
                print(
                    " " + Font.faint_font + choices[choice_idx][0], end="", flush=True
                )
                print(f"\033[{len(choices[choice_idx][0])}D", end="")
                print(Font.reset_font + selected_choice, end="", flush=True)
            continue
        if key.name in ["tab", "right"]:
            print(f"\033[{len(selected_choice)}D", end="")
            selected_choice = choices[choice_idx][0]
            # print(" " + Font.faint_font + choices[choice_idx][0], end="", flush=True)
            # print(f"\033[{len(choices[choice_idx][0])}D", end="")
            print(Font.reset_font + selected_choice, end="", flush=True)
            continue
        if key.name != "backspace":
            selected_choice += key_str.upper()
            print(f"\033[{len(selected_choice)}D", end="")
        else:
            reset = False
            print(f"\033[{len(selected_choice) + 1}D", end="")
            selected_choice = selected_choice[:-1]

        print(" " + Font.faint_font + choices[choice_idx][0], end="", flush=True)
        print(f"\033[{len(choices[choice_idx][0])}D", end="")
        print(Font.reset_font + selected_choice, end="", flush=True)
    return selected_choice


if __name__ == "__main__":
    options = {"CFEPWDR-HB", "CFEPWDR-PR", "APLM-MELKU"}
    selected = autocomplete("Enter prodID: ", options)
    print(f"Selected: {selected}")
