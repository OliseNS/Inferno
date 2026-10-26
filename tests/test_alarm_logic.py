"""Unit tests for the alarm decision logic.

These run without OpenCV, YOLO, GPIO or Telegram: the whole point of
``alarm_logic`` being a separate module is that the safety-critical branching is
testable on a laptop or in CI.

    python -m pytest tests/ -q
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alarm_logic import (  # noqa: E402
    EVENT_FIRE,
    EVENT_FIRE_SMOKE,
    EVENT_GAS,
    EVENT_SMOKE,
    LEVEL_ALARM,
    LEVEL_NORMAL,
    LEVEL_WATCH,
    AlarmConfig,
    AlarmStateMachine,
    format_alert,
)

TICK = 0.5


def tick(sm, fire=False, smoke=False, gas=False, n=1):
    result = None
    for _ in range(n):
        result = sm.update(fire=fire, smoke=smoke, gas=gas)
    return result


def test_single_frame_of_fire_does_not_alarm():
    sm = AlarmStateMachine(AlarmConfig(fire_threshold=3))
    d = tick(sm, fire=True)
    assert d.level == LEVEL_WATCH
    assert d.alarm_on is False
    assert d.event is None


def test_sustained_fire_reaches_alarm_and_emits_once():
    sm = AlarmStateMachine(AlarmConfig(fire_threshold=3))
    first = tick(sm, fire=True, n=3)
    assert first.alarm_on is True
    assert first.level == LEVEL_ALARM
    assert first.event == EVENT_FIRE

    again = tick(sm, fire=True, n=5)
    assert again.alarm_on is True
    assert again.event is None  # no repeat spam


def test_gas_alone_needs_longer_and_reports_as_gas_not_fire():
    sm = AlarmStateMachine(AlarmConfig(gas_threshold=5))
    pending = tick(sm, gas=True, n=4)
    assert pending.alarm_on is False
    assert pending.status != "Fire Detected"

    d = tick(sm, gas=True, n=1)
    assert d.alarm_on is True
    assert d.event == EVENT_GAS
    assert "Fire" not in d.status


def test_brief_gas_blip_never_alarms():
    """The MQ-2 trips on cooking and alcohol; a 1 s blip must stay quiet."""
    sm = AlarmStateMachine(AlarmConfig(gas_threshold=5))
    tick(sm, gas=True, n=2)
    d = tick(sm, n=10)
    assert d.alarm_on is False
    assert d.level == LEVEL_NORMAL


def test_escalation_smoke_then_fire_emits_a_second_event():
    sm = AlarmStateMachine(AlarmConfig(fire_threshold=2, smoke_threshold=2))
    d1 = tick(sm, smoke=True, n=2)
    assert d1.event == EVENT_SMOKE
    assert d1.alarm_on is True

    d2 = tick(sm, fire=True, smoke=True, n=2)
    assert d2.alarm_on is True
    assert d2.event == EVENT_FIRE_SMOKE  # worse situation, new alert


def test_alarm_holds_through_a_single_clean_tick():
    sm = AlarmStateMachine(AlarmConfig(fire_threshold=2, clear_ticks=4))
    tick(sm, fire=True, n=2)
    assert sm.alarm_on is True

    d = tick(sm, n=1)  # one dropped/false-negative frame
    assert d.alarm_on is True


def test_alarm_clears_only_after_clear_ticks():
    sm = AlarmStateMachine(AlarmConfig(fire_threshold=2, clear_ticks=4))
    tick(sm, fire=True, n=2)
    for i in range(3):
        d = tick(sm, n=1)
        assert d.alarm_on is True, f"cleared too early on tick {i}"
    d = tick(sm, n=1)
    assert d.alarm_on is False
    assert d.level == LEVEL_NORMAL
    assert d.status == "Normal"


def test_events_rearm_after_the_alarm_clears():
    sm = AlarmStateMachine(AlarmConfig(fire_threshold=2, clear_ticks=2))
    first = tick(sm, fire=True, n=2)
    assert first.event == EVENT_FIRE
    tick(sm, n=2)  # clear
    second = tick(sm, fire=True, n=2)
    assert second.event == EVENT_FIRE  # a new fire is a new alert


def test_counters_decay_instead_of_resetting():
    """A flickering detection should still accumulate persistence."""
    sm = AlarmStateMachine(AlarmConfig(fire_threshold=3))
    tick(sm, fire=True)
    tick(sm, fire=False)
    tick(sm, fire=True)
    d = tick(sm, fire=True)
    # counts: 1 -> 0 -> 1 -> 2, still not at 3
    assert d.alarm_on is False


def test_gas_and_fire_together_alarm_immediately_when_both_confirmed():
    sm = AlarmStateMachine(AlarmConfig(fire_threshold=2, gas_threshold=2))
    d = tick(sm, fire=True, gas=True, n=2)
    assert d.alarm_on is True
    assert d.fire_confirmed and d.gas_confirmed
    assert d.event == EVENT_FIRE


def test_decision_is_pure_about_disabled_sensors():
    """A sensor that is off is reported as clear and never alarms on its own."""
    sm = AlarmStateMachine(AlarmConfig(gas_threshold=1))
    d = tick(sm, n=5)
    assert d.event is None
    assert d.level == LEVEL_NORMAL


def test_reset_clears_everything():
    sm = AlarmStateMachine(AlarmConfig(fire_threshold=2))
    tick(sm, fire=True, n=2)
    assert sm.alarm_on is True
    sm.reset()
    assert sm.alarm_on is False
    assert sm.counters.fire == 0
    assert tick(sm, n=1).level == LEVEL_NORMAL


@pytest.mark.parametrize(
    "event,expect_in",
    [
        (EVENT_FIRE, "FIRE"),
        (EVENT_SMOKE, "SMOKE"),
        (EVENT_FIRE_SMOKE, "FIRE AND SMOKE"),
        (EVENT_GAS, "GAS"),
    ],
)
def test_alert_text_names_the_event_and_the_gas_state(event, expect_in):
    text = format_alert(event, "12:00:00", "http://firepi.local:8080/", confirmed_by_gas=True)
    assert expect_in in text
    assert "gas sensor: yes" in text
    assert "http://firepi.local:8080/" in text
