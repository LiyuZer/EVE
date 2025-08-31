from src.eve_ide_app.cooldown import CooldownGate
import time


def test_cooldown_gate_basic():
    cd = CooldownGate(seconds=0.1)
    assert cd.should_attempt() is True

    cd.trip(message="boom")
    assert cd.in_cooldown() is True
    assert cd.should_attempt() is False
    assert cd.last_error == "boom"

    time.sleep(0.12)
    assert cd.in_cooldown() is False
    assert cd.should_attempt() is True


def test_cooldown_gate_multiple_trips_updates_message_and_window():
    cd = CooldownGate(seconds=0.05)
    cd.trip(message="first")
    assert cd.in_cooldown() is True
    assert cd.last_error == "first"

    # Trip again before the first cooldown ends
    time.sleep(0.02)
    cd.trip(message="second")
    assert cd.last_error == "second"
    assert cd.in_cooldown() is True

    time.sleep(0.06)
    assert cd.in_cooldown() is False
    assert cd.should_attempt() is True
