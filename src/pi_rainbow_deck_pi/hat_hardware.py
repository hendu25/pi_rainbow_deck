import time

import rainbowhat as rh


def play_sound(freq: int, duration: float):
    try:
        rh.buzzer.note(freq, duration)
    except Exception:
        pass


def show_display(text: str):
    rh.display.clear()
    rh.display.print_str(text[:4].upper())
    rh.display.show()


def set_context_gauge(percentage: float):
    rh.rainbow.clear()
    num_lit = int(round((max(0.0, min(100.0, percentage)) / 100.0) * 7))
    for i in range(num_lit):
        r, g, b = (0, 255, 0) if i < 3 else ((255, 180, 0) if i < 5 else (255, 0, 0))
        rh.rainbow.set_pixel(i, r, g, b, brightness=0.08)
    rh.rainbow.show()


def pulse_rainbow(success=True):
    color = (0, 255, 0) if success else (255, 0, 0)
    rh.rainbow.set_all(*color)
    rh.rainbow.show()
    if success:
        play_sound(880, 0.04)
        time.sleep(0.02)
        play_sound(1760, 0.08)
    else:
        play_sound(220, 0.25)
    time.sleep(0.1)
    rh.rainbow.clear()
    rh.rainbow.show()


def reset_hardware():
    rh.lights.clear()
    rh.rainbow.clear()
    rh.rainbow.show()
    rh.display.clear()
    rh.display.show()
