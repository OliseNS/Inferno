# Changelog

Notable changes, newest first. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/).

## [1.1.0] — 2026-10-26

### Fixed — alarm correctness
- **The gas sensor no longer raises the alarm on its own.** Previously a single
  low reading on the MQ-2 D0 pin set `alarm_triggered` and sent a Telegram alert,
  which meant cooking or deodorant spray could wake the house. Gas now needs its
  own persistence window (`gas_threshold`) and is reported as a gas event, never
  as fire.
- **Fire and smoke are confirmed against the same tick's gas reading** instead of
  ignoring it, so the alert caption can say whether the air corroborated the
  camera.
- **The alarm no longer latches.** `alarm_triggered` used to swallow every later
  detection until all sensors went quiet, so smoke that turned into a real fire
  produced exactly one message. The state machine now emits a *new* alert when
  the situation worsens (smoke → fire, fire → gas) and never repeats one already
  sent.
- **Clearing needs consecutive quiet ticks** (`clear_ticks`) rather than a single
  frame, so a dropped frame cannot produce a stop-start siren.

### Fixed — responsiveness and disk
- **Telegram sends no longer block the detection loop.** Alerts (fire, smoke,
  gas, motion, face) go through a bounded `notify_queue` drained by a worker
  thread. Previously `asyncio.run_until_complete()` ran inline on the detection
  thread and stalled frame capture for the duration of each HTTP call.
- **`detections/` is pruned while running**, down to `system.max_saved_detections`
  (default 200). Before, images accumulated until the process restarted, which
  fills an SD card during a sustained event.

### Added
- `alarm_logic.py` — the alarm decision logic as a hardware-free module.
- `tests/test_alarm_logic.py` — 16 tests covering single-frame, persistence,
  gas-only, escalation, hysteresis and re-arming behaviour.
- `docs/ARCHITECTURE.md` and `docs/ALARM_LOGIC.md`.
- `requirements-dev.txt` (pytest) and `requirements-train.txt` (torch + ncnn, only
  for re-exporting or retraining the model), so the runtime install is smaller.
- `pyproject.toml` with pytest and ruff configuration.
- `system.max_saved_detections` in `settings.json`.

### Changed
- README rewritten for reviewers: what it does, how the alarm decides, quick
  start, config table, API table, and an explicit limitations section.
- `FIXES.md` folded into this changelog.
- `__pycache__/gtts.cpython-312.pyc` removed from version control.

## [1.0.0]

### Fixed
- Bounding boxes never drew: the label-drawing block was indented into the
  `else` branch of `if show_boxes:`.
- NCNN model folder renamed to `fire_smoke_yolo11_ncnn_model`; Ultralytics
  requires the `_ncnn_model` suffix.
- Telegram credentials moved to `.env`; `settings.json` holds non-secrets only.
