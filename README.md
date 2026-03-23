# Inferno (Blazetection)

Real-time fire, smoke, motion, and face detection with a web dashboard, Telegram alerts, and optional Raspberry Pi hardware (camera, MQ2, alarm). This repository is structured so reviewers can find the model, configuration, and entry points quickly.

---

## Quick start

```bash
git clone https://github.com/OliseNS/Inferno.git
cd Inferno
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

1. Copy `config.example.json` to `config.json` and set `telegram` / `camera_url` as needed (or use the dashboard after launch).
2. Run the full stack (dashboard + detection):

```bash
python webserver.py
```

Open `http://<host>:8080/`. Detection-only (no web UI):

```bash
python detection_system.py
```

---

## Repository layout

| Path | Purpose |
|------|---------|
| `webserver.py` | Flask app: dashboard, API, starts detection in a background thread |
| `detection_system.py` | Camera, YOLO, MediaPipe face mesh, motion, Telegram, alarm |
| `config.json` / `config.example.json` | Runtime settings (copy example → `config.json` for local secrets) |
| `models/yolov8-fire-smoke-ncnn/` | Ultralytics YOLOv8 **NCNN export** for fire/smoke (`model.ncnn.param`, `model.ncnn.bin`, `metadata.yaml`) |
| `static/`, `templates/` | Dashboard assets |
| `streaming_server/` | Optional MJPEG helper (`server.py` on port 5000) — point `camera_url` at it if needed |
| `scripts/ncnn_smoke_test.py` | Optional NCNN sanity check (requires `ncnn` + `torch`; not used in production) |

The detection pipeline loads the model via [Ultralytics](https://docs.ultralytics.com/) using `system.model_path` in `config.json` (default: `models/yolov8-fire-smoke-ncnn`). You can point it at another exported folder or a `.pt` file.

---

## Features

- **Fire, smoke, motion, face** — YOLO + MediaPipe face mesh + motion heuristic  
- **Web dashboard** — live stats, toggles, TTS, Telegram test, alarm stop  
- **Telegram** — alerts and images (configure token + chat ID in config or UI)  
- **Alarm** — local audio (`alarm.wav`) on repeated critical detections  
- **MQ2** — optional GPIO smoke/gas input on Raspberry Pi  

---

## Requirements

- Python 3.10+ recommended  
- Webcam or IP / MJPEG stream compatible with OpenCV  
- Raspberry Pi optional (GPIO, `gpiozero` for MQ2)  

---

## Configuration

- **`system.model_path`** — YOLO weights (NCNN export directory or `.pt`).  
- **`system.camera_index`** — Local camera when `camera_url` is empty.  
- **`system.camera_url`** — HTTP MJPEG or stream URL (e.g. from `streaming_server/server.py`).  
- **`telegram.*`** — Bot token and chat ID; keep these out of public forks (use `config.example.json` as a template).  

---

## Author

**OliseNS** — [GitHub](https://github.com/OliseNS)

---

## License

No license file is included yet; contact the author for usage terms.
