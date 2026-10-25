from types import SimpleNamespace
from typing import Callable


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


def play_sound(frequency, duration):
    buzzer.note(frequency, duration)


def show_display(text):
    display.clear()
    display.print_str(text[:4].upper())
    display.show()


def set_context_gauge(percentage):
    bounded_percentage = max(0.0, min(100.0, percentage))
    num_lit = int(round((bounded_percentage / 100.0) * 7))
    rainbow.clear()
    for index in range(num_lit):
        color = (
            (0, 255, 0) if index < 3 else ((255, 180, 0) if index < 5 else (255, 0, 0))
        )
        rainbow.set_pixel(index, *color, brightness=0.08)
    rainbow.show()
    print(f"[VIRTUAL HAT] Context: {bounded_percentage:.1f}% ({num_lit}/7 LEDs)")


def pulse_rainbow(success=True):
    color = (0, 255, 0) if success else (255, 0, 0)
    rainbow.set_all(*color)
    rainbow.show()
    play_sound(880 if success else 220, 0.04 if success else 0.25)
    if success:
        play_sound(1760, 0.08)
    rainbow.clear()
    rainbow.show()


def reset_hardware():
    lights.clear()
    rainbow.clear()
    rainbow.show()
    display.clear()
    display.show()


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


def run(on_quit: Callable[[], bool]):
    print("[VIRTUAL HAT] Press A, B, or C to send a button; Q to stop the host.")
    buttons = {"A": touch.A, "B": touch.B, "C": touch.C}
    while True:
        try:
            selection = input("Virtual HAT [A/B/C/Q]: ").strip().upper()
        except EOFError:
            return
        if selection == "Q":
            if on_quit():
                print("[VIRTUAL HAT] Host shutdown requested.")
            else:
                print("[VIRTUAL HAT] Could not contact the host.")
            return
        button = buttons.get(selection)
        if button is None:
            print("Choose A, B, C, or Q.")
            continue
        button.press_button()
