import pytest


def test_play_sound_calls_buzzer_and_swallows_hardware_failure(pi_modules):
    _, hardware, hat = pi_modules
    hardware.play_sound(440, 0.25)
    hat.buzzer.note.assert_called_once_with(440, 0.25)

    hat.buzzer.note.side_effect = OSError("buzzer unavailable")
    hardware.play_sound(440, 0.25)


def test_show_display_clears_and_shows_uppercase_four_character_text(pi_modules):
    _, hardware, hat = pi_modules
    hardware.show_display("safe-mode")

    hat.display.clear.assert_called_once_with()
    hat.display.print_str.assert_called_once_with("SAFE")
    hat.display.show.assert_called_once_with()


@pytest.mark.parametrize(
    ("percentage", "expected_lights", "expected_colors"),
    [
        (0, 0, []),
        (50, 4, [(0, 255, 0), (0, 255, 0), (0, 255, 0), (255, 180, 0)]),
        (
            100,
            7,
            [
                (0, 255, 0),
                (0, 255, 0),
                (0, 255, 0),
                (255, 180, 0),
                (255, 180, 0),
                (255, 0, 0),
                (255, 0, 0),
            ],
        ),
        (-20, 0, []),
        (
            120,
            7,
            [
                (0, 255, 0),
                (0, 255, 0),
                (0, 255, 0),
                (255, 180, 0),
                (255, 180, 0),
                (255, 0, 0),
                (255, 0, 0),
            ],
        ),
    ],
)
def test_set_context_gauge_clamps_percentage_and_sets_pixels(
    pi_modules, percentage, expected_lights, expected_colors
):
    _, hardware, hat = pi_modules
    hardware.set_context_gauge(percentage)

    assert hat.rainbow.clear.call_count == 1
    assert hat.rainbow.set_pixel.call_count == expected_lights
    actual_colors = [
        (args[1], args[2], args[3]) for args, _ in hat.rainbow.set_pixel.call_args_list
    ]
    assert actual_colors == expected_colors
    for index, ((pixel, *_), kwargs) in enumerate(hat.rainbow.set_pixel.call_args_list):
        assert pixel == index
        assert kwargs == {"brightness": 0.08}
    hat.rainbow.show.assert_called_once_with()


@pytest.mark.parametrize(
    ("success", "expected_color", "expected_sounds"),
    [
        (True, (0, 255, 0), [(880, 0.04), (1760, 0.08)]),
        (False, (255, 0, 0), [(220, 0.25)]),
    ],
)
def test_pulse_rainbow_signals_result_and_resets_display(
    pi_modules, monkeypatch, success, expected_color, expected_sounds
):
    _, hardware, hat = pi_modules
    sounds = []
    delays = []
    monkeypatch.setattr(hardware, "play_sound", lambda *args: sounds.append(args))
    monkeypatch.setattr(hardware.time, "sleep", lambda delay: delays.append(delay))

    hardware.pulse_rainbow(success)

    hat.rainbow.set_all.assert_called_once_with(*expected_color)
    assert sounds == expected_sounds
    assert delays == ([0.02, 0.1] if success else [0.1])
    assert hat.rainbow.clear.call_count == 1
    assert hat.rainbow.show.call_count == 2


def test_reset_hardware_clears_lights_rainbow_and_display(pi_modules):
    _, hardware, hat = pi_modules
    hardware.reset_hardware()

    hat.lights.clear.assert_called_once_with()
    hat.rainbow.clear.assert_called_once_with()
    hat.rainbow.show.assert_called_once_with()
    hat.display.clear.assert_called_once_with()
    hat.display.show.assert_called_once_with()
