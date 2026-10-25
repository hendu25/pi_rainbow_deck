import sys
import time
import subprocess

IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform.startswith("win")

if IS_WIN:
    try:
        import pyautogui
    except ImportError:
        print("[ERROR] On Windows, run: pip install pyautogui")
        sys.exit(1)

def execute_action(action_id: str):
    """Executes native OS keystrokes for the given action ID."""
    print(f"[ACTION TRIGGERED]: {action_id}")

    if IS_MAC:
        mac_actions = {
            "APPROVE": [('keystroke "y"', 0), ('key code 36', 0)],
            "COMPACT": [('keystroke "/compact"', 0), ('key code 36', 0)],
            "DIFF": [('keystroke "/diff"', 0), ('key code 36', 0)],
            "COST": [('keystroke "/cost"', 0), ('key code 36', 0)],
            "TASKS": [('keystroke "/tasks"', 0), ('key code 36', 0)],
            "REWIND": [('key code 53', 0.05), ('key code 53', 0)],
            "ABORT": [('key down control', 0), ('keystroke "c"', 0), ('key up control', 0)]
        }
        for cmd, delay in mac_actions.get(action_id, []):
            subprocess.run(["osascript", "-e", f'tell application "System Events" to {cmd}'])
            if delay:
                time.sleep(delay)

    elif IS_WIN:
        win_actions = {
            "APPROVE": lambda: (pyautogui.typewrite('y'), pyautogui.press('enter')),
            "COMPACT": lambda: (pyautogui.typewrite('/compact'), pyautogui.press('enter')),
            "DIFF": lambda: (pyautogui.typewrite('/diff'), pyautogui.press('enter')),
            "COST": lambda: (pyautogui.typewrite('/cost'), pyautogui.press('enter')),
            "TASKS": lambda: (pyautogui.typewrite('/tasks'), pyautogui.press('enter')),
            "REWIND": lambda: (pyautogui.press('esc'), pyautogui.press('esc')),
            "ABORT": lambda: pyautogui.hotkey('ctrl', 'c')
        }
        handler = win_actions.get(action_id)
        if handler:
            handler()