"""Alarm decision logic for Inferno.

This module is deliberately free of OpenCV, YOLO, GPIO and Telegram imports so
the behaviour that actually decides whether a building gets woken up can be
unit tested on any machine (see ``tests/test_alarm_logic.py``).

Design rules
------------
1. **Persistence before panic.** A single frame of "fire" is usually a
   reflection, a lamp or a mis-detection. Fire and smoke only reach alarm level
   after ``fire_threshold`` consecutive positive ticks.
2. **The gas sensor confirms, it does not cry wolf.** The MQ-2 D0 pin goes low
   for cooking, deodorant, alcohol and its own burn-in. Gas therefore needs its
   own, longer persistence window (``gas_threshold`` ticks) and is reported as
   its own event ("gas leak"), never as a fire.
3. **Escalation is allowed, repetition is not.** Once the alarm is sounding the
   decision logic keeps emitting *new* events when the situation gets worse
   (smoke -> fire, fire -> fire + gas) so the operator gets told, but it never
   re-sends the same event. That is what the old ``alarm_triggered`` latch got
   wrong: it swallowed every later detection until everything went quiet.
4. **Clearing needs quiet, not a gap.** The alarm only stops after
   ``clear_ticks`` consecutive clean ticks, so a single dropped frame does not
   produce a stop/start siren loop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# Event names also act as the Telegram cooldown keys.
EVENT_FIRE = "fire"
EVENT_SMOKE = "smoke"
EVENT_FIRE_SMOKE = "fire_smoke"
EVENT_GAS = "gas"
EVENT_FACE = "face"
EVENT_MOTION = "motion"

LEVEL_NORMAL = 0
LEVEL_WATCH = 1
LEVEL_ALARM = 2


@dataclass
class AlarmConfig:
    """Thresholds for the decision logic.

    ``fire_threshold`` mirrors the existing ``system.alarm_threshold`` setting so
    users who already tuned their config keep the same behaviour.
    """

    fire_threshold: int = 3       # consecutive ticks of fire before alarm
    smoke_threshold: int = 3      # consecutive ticks of smoke before alarm
    gas_threshold: int = 4        # consecutive ticks of gas before alarm
    clear_ticks: int = 4          # consecutive clean ticks before reset

    def __post_init__(self) -> None:
        self.fire_threshold = max(1, int(self.fire_threshold))
        self.smoke_threshold = max(1, int(self.smoke_threshold))
        self.gas_threshold = max(1, int(self.gas_threshold))
        self.clear_ticks = max(1, int(self.clear_ticks))


@dataclass(frozen=True)
class Decision:
    """The outcome of one detection tick."""

    level: int
    status: str
    alarm_on: bool
    event: Optional[str] = None       # notification to send now, or None
    changed: bool = False             # level or alarm_on changed this tick
    reason: str = ""
    fire_confirmed: bool = False
    smoke_confirmed: bool = False
    gas_confirmed: bool = False

    @property
    def alarm_type(self) -> str:
        return self.status


@dataclass
class AlarmCounters:
    """Exposed for tests and for the /api/status payload."""

    fire: int = 0
    smoke: int = 0
    gas: int = 0
    clear: int = 0


class AlarmStateMachine:
    """Consecutive-tick state machine that decides alarm level and events."""

    def __init__(self, config: Optional[AlarmConfig] = None):
        self.config = config or AlarmConfig()
        self.counters = AlarmCounters()
        self._alarm_on = False
        self._level = LEVEL_NORMAL
        self._status = "Normal"
        self._sent: set[str] = set()

    # -- helpers ---------------------------------------------------------
    def _bump(self, value: int, seen: bool) -> int:
        return value + 1 if seen else max(0, value - 1)

    def reset(self) -> None:
        """Drop all state, as if freshly started."""
        self.counters = AlarmCounters()
        self._alarm_on = False
        self._level = LEVEL_NORMAL
        self._status = "Normal"
        self._sent.clear()

    @property
    def alarm_on(self) -> bool:
        return self._alarm_on

    @property
    def level(self) -> int:
        return self._level

    @property
    def status(self) -> str:
        return self._status

    # -- the decision ----------------------------------------------------
    def update(self, *, fire: bool, smoke: bool, gas: bool) -> Decision:
        """Consume one tick of sensor readings and return what to do."""
        cfg = self.config
        c = self.counters

        c.fire = self._bump(c.fire, fire)
        c.smoke = self._bump(c.smoke, smoke)
        c.gas = self._bump(c.gas, gas)

        fire_hit = c.fire >= cfg.fire_threshold
        smoke_hit = c.smoke >= cfg.smoke_threshold
        gas_hit = c.gas >= cfg.gas_threshold

        nothing = not (fire or smoke or gas)
        c.clear = c.clear + 1 if nothing else 0

        # Decide the alarm, with hysteresis on clearing.
        was_alarm = self._alarm_on
        if fire_hit or smoke_hit or gas_hit:
            self._alarm_on = True
        elif was_alarm and c.clear >= cfg.clear_ticks:
            self._alarm_on = False

        if fire_hit and smoke_hit:
            status = "Fire & Smoke Detected"
        elif fire_hit:
            status = "Fire Detected"
        elif smoke_hit:
            status = "Smoke Detected"
        elif gas_hit:
            status = "Gas Detected"
        elif fire or smoke:
            status = "Watch"
        elif gas:
            status = "Gas Watch"
        elif self._alarm_on:
            status = self._status  # hold the last alarm while waiting to clear
        else:
            status = "Normal"

        if self._alarm_on:
            level = LEVEL_ALARM
        elif fire or smoke or gas:
            level = LEVEL_WATCH
        else:
            level = LEVEL_NORMAL

        event = None
        if self._alarm_on:
            # Ordered from worst to mildest; emit the worst one not yet sent.
            candidates = []
            if fire_hit and smoke_hit:
                candidates.append(EVENT_FIRE_SMOKE)
            if fire_hit:
                candidates.append(EVENT_FIRE)
            if smoke_hit:
                candidates.append(EVENT_SMOKE)
            if gas_hit:
                candidates.append(EVENT_GAS)
            for name in candidates:
                if name not in self._sent:
                    event = name
                    break

        changed = (level != self._level) or (self._alarm_on != was_alarm)
        self._level = level
        self._status = status
        if event:
            self._sent.add(event)
        if not self._alarm_on and c.clear >= cfg.clear_ticks:
            self._sent.clear()

        return Decision(
            level=level,
            status=status,
            alarm_on=self._alarm_on,
            event=event,
            changed=changed,
            reason=self._reason(fire, smoke, gas, fire_hit, smoke_hit, gas_hit),
            fire_confirmed=fire_hit,
            smoke_confirmed=smoke_hit,
            gas_confirmed=gas_hit,
        )

    @staticmethod
    def _reason(fire, smoke, gas, fire_hit, smoke_hit, gas_hit) -> str:
        parts = []
        for name, seen, hit in (
            ("fire", fire, fire_hit),
            ("smoke", smoke, smoke_hit),
            ("gas", gas, gas_hit),
        ):
            if seen:
                parts.append(f"{name} (confirmed)" if hit else f"{name} (pending)")
        return ", ".join(parts) if parts else "clear"


def format_alert(event: str, timestamp: str, stream_url: str, confirmed_by_gas: bool) -> str:
    """Build the Telegram caption for an event."""
    gas = "yes" if confirmed_by_gas else "no"
    if event == EVENT_FIRE:
        return f"🔥 FIRE DETECTED at {timestamp} — gas sensor: {gas}. Live: {stream_url}"
    if event == EVENT_SMOKE:
        return f"💨 SMOKE DETECTED at {timestamp} — gas sensor: {gas}. Live: {stream_url}"
    if event == EVENT_FIRE_SMOKE:
        return f"🔥💨 FIRE AND SMOKE DETECTED at {timestamp} — gas sensor: {gas}. Live: {stream_url}"
    if event == EVENT_GAS:
        return f"⚠️ SUSTAINED GAS DETECTED at {timestamp} — gas sensor: {gas}, no fire seen yet. Live: {stream_url}"
    return f"{event.upper()} detected at {timestamp}. Live: {stream_url}"
