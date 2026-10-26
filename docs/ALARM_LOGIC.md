# Alarm logic

The rules that decide whether a building gets woken up live in `alarm_logic.py`,
with no OpenCV, YOLO, GPIO or Telegram imports. That is deliberate: it is the
part most likely to be wrong, and it is the part you can actually test.

```
detection_system.py                alarm_logic.py
──────────────────                 ──────────────
camera frame  ──► YOLO11 ──┐
                           ├──► AlarmStateMachine.update() ──► Decision
MQ-2 D0 pin   ──► gas hit ─┘
```

`DetectionSystem.update_alarm_state()` feeds one tick per processed frame and
translates the returned `Decision` into a siren, a status string and a queued
Telegram message.

## The four rules

**1. Persistence before panic.** A single frame of "fire" is usually a lamp, a
reflection or a mis-detection. Fire and smoke only reach alarm level after
`alarm_threshold` consecutive positive ticks (default 3, one tick per
`detection_interval`). The counters decay by one rather than resetting, so a
flickering detection still accumulates.

**2. The gas sensor confirms, it does not cry wolf.** The MQ-2 D0 pin goes low
for cooking, deodorant, alcohol vapour, and its own burn-in. Gas therefore needs
a longer window than vision (`gas_threshold`, default `max(2, alarm_threshold)`)
and is reported as its own event — *"SUSTAINED GAS DETECTED … no fire seen yet"*
— never as a fire. A gas reading is evidence about the air, not proof of flames.

**3. Escalation is allowed, repetition is not.** Once the alarm is sounding, the
state machine keeps emitting *new* events when the situation gets worse
(smoke → fire, fire → fire + gas) so the operator is told, but never re-sends an
event it has already sent. Events re-arm only after the alarm clears. This
replaces an earlier boolean latch that swallowed every later detection until
everything went quiet — meaning a smoke alarm that turned into a real fire sent
one message.

**4. Clearing needs quiet, not a gap.** The alarm stops only after
`clear_ticks` consecutive clean ticks (default `max(2, alarm_threshold)`), so a
dropped frame does not produce a stop/start siren loop.

## Thresholds

| Setting | Meaning | Default |
|---|---|---|
| `system.alarm_threshold` | consecutive ticks of fire/smoke before alarm | `3` |
| `gas_threshold` | consecutive ticks of gas before alarm | `max(2, alarm_threshold)` |
| `clear_ticks` | consecutive clean ticks before the alarm clears | `max(2, alarm_threshold)` |

Only `alarm_threshold` is exposed in `settings.json`; the other two derived from
it so a user who tunes one number gets sensible behaviour everywhere. Editing
`settings.json` and saving from the dashboard re-applies them live via
`on_config_update()`.

## Status values

`Normal`, `Watch` (fire/smoke seen but not yet confirmed), `Gas Watch`,
`Fire Detected`, `Smoke Detected`, `Fire & Smoke Detected`, `Gas Detected`.
The dashboard's status pill reads these directly.

## Notification delivery

Alerts are never sent inline on the detection thread. `_queue_alert()` puts a
`(event, image_path, confirmed_by_gas)` tuple on `notify_queue` and returns
immediately; `_notification_worker()` drains it and calls Telegram. A slow or
unreachable Telegram API therefore costs a queued message, not dropped frames.
The queue is bounded at 32 — if Telegram is down for a long time, new alerts are
dropped with a console warning rather than growing memory without bound.

Cooldowns are still enforced per event type inside `TelegramService`, using the
event name (`fire`, `smoke`, `fire_smoke`, `gas`, `motion`, `face`) as the key.

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -q
```

`tests/test_alarm_logic.py` covers: a single fire frame does not alarm; sustained
fire alarms once and does not repeat; a 1-second gas blip never alarms; gas alone
never reports as fire; smoke → fire sends a second, different alert; the alarm
holds through one clean tick and clears only after `clear_ticks`; events re-arm
after clearing; gas + fire together alarm on the first confirmed tick.
