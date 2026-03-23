# Inferno (Blazetection)

Real-time fire, smoke, motion, and face detection with a web dashboard, Telegram alerts, and optional Raspberry Pi hardware (camera, MQ2, alarm).

**Secrets never go in JSON.** Telegram credentials live in a **`.env`** file. **`settings.json`** only contains non-sensitive options (detection toggles, intervals, camera URL, model path).

---

## Quick start

```bash
git clone https://github.com/OliseNS/Inferno.git
cd Inferno
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env: set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID if you use Telegram
```

Run the full stack (dashboard + detection):

```bash
python webserver.py
```

Open `http://<host>:8080/`. Headless detection only:

```bash
python detection_system.py
```

On first run, if `settings.json` is missing, defaults are created. Adjust detection toggles and `system.model_path` in **`settings.json`** (safe to commit). Enable Telegram in the dashboard or set `telegram.enabled` in **`settings.json`** after **`TELEGRAM_*`** are set in **`.env`**.

---

## Repository layout

| Path | Purpose |
|------|---------|
| `webserver.py` | Flask app: dashboard, API, background detection |
| `detection_system.py` | Camera, YOLO, MediaPipe, motion, Telegram, alarm |
| `settings.json` | Non-secret runtime options (committed template; copy from `settings.example.json` if needed) |
| `.env` | **Secrets only** — `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` (create from `.env.example`, never commit) |
| `models/fire_smoke_yolov8_ncnn_model/` | YOLOv8 NCNN export for fire/smoke (folder name must end with `_ncnn_model` for Ultralytics) |
| `static/`, `templates/` | Dashboard assets |
| `streaming_server/` | Optional MJPEG server (`server.py`, port 5000) |
| `scripts/ncnn_smoke_test.py` | Optional NCNN check (requires `ncnn` + `torch`) |

`system.model_path` in `settings.json` points at the YOLO export (default: `models/fire_smoke_yolov8_ncnn_model`). NCNN exports must live in a directory whose name ends with `_ncnn_model`. Override with another folder or `.pt` path.

---

## Environment variables

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Telegram bot token from [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHAT_ID` | Destination chat or group ID |

The dashboard can append/update these in `.env` when you save token/chat ID (non-empty fields only).

---

## Features

- Fire, smoke, motion, face detection (YOLO + MediaPipe + motion heuristic)  
- Web dashboard with toggles, TTS, Telegram test, alarm stop  
- Telegram alerts (credentials from `.env` only)  
- Local alarm audio (`alarm.wav`)  
- Optional MQ2 on Raspberry Pi (`gpiozero`)  

---

## Requirements

- Python 3.10+  
- Webcam or OpenCV-compatible stream  
- Raspberry Pi optional  

---

## Author

**OliseNS** — [GitHub](https://github.com/OliseNS)

---

## License

No license file is included yet; contact the author for usage terms.
