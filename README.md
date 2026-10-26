# 🔥 Inferno

Real-time fire, smoke, gas and person detection on a Raspberry Pi, with a web
dashboard, a local siren, and Telegram alerts that carry evidence.

Built for the case a smoke detector can't cover: you want to *see* what is
happening, get told about it wherever you are, and not be woken up by steam from
the shower.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Flask](https://img.shields.io/badge/Flask-3.0+-orange)
![Model](https://img.shields.io/badge/YOLO11-NCNN-red)

---

## What it does

- **Fire and smoke detection** with a YOLO11 model, exported to NCNN and run
  locally at 224×224.
- **Gas detection** from an MQ-2 sensor on the Pi's GPIO — treated as *evidence*,
  not as a trigger (see [docs/ALARM_LOGIC.md](docs/ALARM_LOGIC.md)).
- **Face and motion detection** with MediaPipe and MOG2, for presence context.
- **Local siren** that sounds even when the network is down.
- **Telegram alerts** with the detection frame attached, sent from a worker
  thread so a slow API never stalls the camera.
- **Web dashboard** — live MJPEG feed with overlays, per-detector toggles,
  detection gallery, uptime and frame stats, text-to-speech.
- **Everything local.** No cloud inference, no accounts.

## The alarm is the interesting part

Most hobby fire detectors fail by crying wolf, not by missing a fire. The rules
here are:

1. Fire or smoke must persist for `alarm_threshold` consecutive ticks before
   anything sounds — one frame is not evidence.
2. The gas sensor needs a *longer* window and reports itself as a gas event, not
   as fire. Cooking, deodorant and sensor burn-in all trip an MQ-2.
3. Once the alarm is on, a worsening situation (smoke → fire, fire → gas) sends a
   new alert; it never re-sends one already sent.
4. The alarm clears only after several consecutive clean ticks, so a dropped
   frame doesn't produce a stop-start siren.

All of that lives in [`alarm_logic.py`](alarm_logic.py), free of hardware and
network imports, and is unit tested in [`tests/`](tests/). Details and the full
threshold table: [docs/ALARM_LOGIC.md](docs/ALARM_LOGIC.md).

---

## Quick start

```bash
git clone https://github.com/OliseNS/Inferno.git
cd Inferno

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

# Optional — Telegram alerts
cp .env.example .env      # then fill in the two values

python webserver.py       # dashboard on http://localhost:8080
```

Detection only, no dashboard:

```bash
python detection_system.py
```

The YOLO11 NCNN model is committed under `models/`, so there is no export step
and no torch download.

### Requirements

Python 3.10+, a USB or IP camera, and Linux/macOS/Windows for the dashboard.
For the full build: a **Raspberry Pi 4 (4 GB+)** with Raspberry Pi OS 64-bit, an
MQ-2 sensor on GPIO 17, and a speaker.

| | |
|---|---|
| RAM | 2 GB minimum, 4 GB recommended |
| Disk | ~200 MB (model is 43 MB) |
| Camera | USB webcam, Pi Camera, or an MJPEG/RTSP URL |

---

## Configuration

Non-secret settings live in `settings.json`; secrets live only in `.env`. The
dashboard writes both for you when you save the config form.

```json
{
  "detection": { "fire": true, "smoke": true, "motion": true, "face": true },
  "telegram":  { "enabled": false, "cooldown": 30 },
  "system": {
    "camera_index": 0,
    "camera_url": "",
    "model_path": "models/fire_smoke_yolo11_ncnn_model",
    "detection_interval": 0.5,
    "face_save_interval": 1.0,
    "alarm_threshold": 3,
    "max_saved_faces": 50,
    "max_saved_detections": 200,
    "show_bounding_boxes": true
  }
}
```

| Key | Meaning |
|---|---|
| `detection.*` | Enable each detector independently |
| `telegram.enabled` | Master switch for outbound alerts |
| `telegram.cooldown` | Minimum seconds between two alerts of the same type |
| `camera_url` | MJPEG/RTSP URL, or a numeric string for a device index; takes precedence over `camera_index` |
| `detection_interval` | Seconds between detection ticks (0.5 = twice a second) |
| `alarm_threshold` | Consecutive positive ticks before fire/smoke raises the alarm |
| `max_saved_faces` / `max_saved_detections` | How many evidence images to keep on disk |
| `show_bounding_boxes` | Draw overlays on the stream (and therefore on saved evidence) |

### Secrets

| Variable | Where to get it |
|---|---|
| `TELEGRAM_BOT_TOKEN` | [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHAT_ID` | [@userinfobot](https://t.me/userinfobot) |

`.env` is gitignored. Never paste a token into an issue.

---

## HTTP API

The dashboard is a thin client over these:

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Dashboard |
| GET | `/video_feed` | MJPEG stream with overlays |
| GET | `/api/status` | System status and last detection timestamps |
| GET / POST | `/api/config` | Read or update settings (POST writes `.env` for secrets) |
| GET | `/api/statistics` | Uptime and frames processed |
| GET | `/api/faces`, `/api/detections` | Evidence galleries |
| POST | `/api/alarm/stop` | Silence the siren |
| POST | `/api/telegram/test` | Send a test message |
| POST | `/api/tts` | Speak a phrase on the host |
| POST | `/api/restart` | Restart the detection loop |

## Raspberry Pi notes

```bash
sudo usermod -a -G video $USER     # camera access
sudo usermod -a -G gpio  $USER     # MQ-2 on GPIO 17
sudo reboot
```

The MQ-2 needs ~24 h of burn-in before its readings are worth trusting, and it is
sensitive to temperature and humidity — that is exactly why it is used to
corroborate the camera rather than to raise the alarm by itself.

Sound playback uses `aplay`, so install `alsa-utils` if `alarm.wav` is silent.

## Troubleshooting

- **No detections** — check the toggles in the dashboard, the model path, and
  `tail -f logs/inferno.log`.
- **Camera missing on the Pi** — the stream URL form (`camera_url`) is more
  reliable than the index for a Pi Camera over `libcamera`; try the MJPEG URL.
- **Telegram silent** — verify both `.env` values, that the bot isn't blocked, and
  that the per-type cooldown hasn't swallowed the message. The dashboard's test
  button ignores cooldown.
- **Pi throttling after ten minutes** — lower the frame size, raise
  `detection_interval`, or disable face detection (the most expensive detector).

---

## Project layout

| Path | Purpose |
|---|---|
| `detection_system.py` | Camera, detectors, MQ-2, alarm wiring, notification worker |
| `alarm_logic.py` | Pure alarm decision logic (tested, no hardware imports) |
| `webserver.py` | Flask app, API, MJPEG stream |
| `inferno_logging.py` | Tee console output to `logs/inferno.log` |
| `templates/`, `static/` | Dashboard |
| `models/fire_smoke_yolo11_ncnn_model/` | YOLO11 NCNN export (folder name must end `_ncnn_model`) |
| `scripts/ncnn_smoke_test.py` | Offline check that the NCNN export loads |
| `streaming_server/` | Standalone MJPEG server, no detection (port 5000) |
| `tests/` | Unit tests |
| `docs/` | [Architecture](docs/ARCHITECTURE.md), [alarm logic](docs/ALARM_LOGIC.md) |

## Development

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -q
```

The tests need no camera, no GPIO and no model: `alarm_logic.py` is deliberately
importable on any machine.

## Honest limitations

- The detector was fine-tuned on a modest fire/smoke dataset; treat it as a
  corroborating sensor, not a certified detector. It is not a replacement for a
  smoke alarm and is not life-safety rated.
- False-positive and false-negative rates have not been measured against a
  labelled test set yet. Numbers beat adjectives — that measurement is the next
  piece of work.
- The Telegram path is best-effort: if the network is down the local siren still
  sounds, and alerts are dropped rather than queued indefinitely.

## License

No license file yet — contact the author before reuse.
