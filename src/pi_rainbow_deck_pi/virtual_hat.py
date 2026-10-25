from types import SimpleNamespace


class VirtualButton:
    def __init__(self):
        self.callback = None

    def press(self):
        def register(callback):
            self.callback = callback
            return callback

        return register

    def press_button(self):
        if self.callback is not None:
            self.callback("virtual")


def _light(name):
    return SimpleNamespace(
        on=lambda: print(f"[VIRTUAL HAT] {name} light on"),
        off=lambda: print(f"[VIRTUAL HAT] {name} light off"),
    )


def _show_display(text):
    print(f"[VIRTUAL HAT] Display: {text[:4].upper()}")


def _show_rainbow():
    print("[VIRTUAL HAT] Rainbow LEDs updated")


def _play_sound(frequency, duration):
    print(f"[VIRTUAL HAT] Beep: {frequency} Hz for {duration:.2f}s")


touch = SimpleNamespace(A=VirtualButton(), B=VirtualButton(), C=VirtualButton())
lights = SimpleNamespace(
    red=_light("red"),
    green=_light("green"),
    blue=_light("blue"),
    clear=lambda: print("[VIRTUAL HAT] Button lights cleared"),
)
buzzer = SimpleNamespace(note=_play_sound)
display = SimpleNamespace(
    clear=lambda: None,
    print_str=_show_display,
    show=lambda: None,
)
rainbow = SimpleNamespace(
    clear=lambda: None,
    set_pixel=lambda *args, **kwargs: None,
    set_all=lambda *args, **kwargs: None,
    show=_show_rainbow,
)


def run():
    print("[VIRTUAL HAT] Press A, B, or C to send a button; Q to quit.")
    buttons = {"A": touch.A, "B": touch.B, "C": touch.C}
    while True:
        try:
            selection = input("Virtual HAT [A/B/C/Q]: ").strip().upper()
        except EOFError:
            return
        if selection == "Q":
            return
        button = buttons.get(selection)
        if button is None:
            print("Choose A, B, C, or Q.")
            continue
        button.press_button()
