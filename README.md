# 🔥 Inferno (Blazetection)

Real-time fire, smoke, motion, and face detection system with a beautiful web dashboard, Telegram alerts, and optional Raspberry Pi hardware support (camera, MQ2 gas sensor, audio alarm).

![Dashboard Preview](https://img.shields.io/badge/Status-Active-brightgreen) ![Python](https://img.shields.io/badge/Python-3.10+-blue) ![Flask](https://img.shields.io/badge/Flask-3.0+-orange)

**🔐 Security First:** Telegram credentials live in a **`.env`** file (never committed). **`settings.json`** only contains non-sensitive options.

---

## ✨ Features

- 🔥 **Fire Detection** - YOLO11 model trained for fire detection
- 💨 **Smoke Detection** - Visual smoke detection with YOLO11
- 👤 **Face Detection** - MediaPipe-powered face detection and tracking
- 🏃 **Motion Detection** - OpenCV-based motion tracking
- 🌐 **Web Dashboard** - Beautiful, modern real-time dashboard
- 📱 **Telegram Alerts** - Instant notifications with images
- 🔊 **Text-to-Speech** - Browser-based audio playback using gTTS
- 🎯 **Bounding Box Toggle** - Show/hide detection overlays
- 📦 **Easy Setup** - Clone and run in minutes

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10 or higher**
- **Webcam or IP camera** (MJPEG/RTSP stream)
- **Chromium-based browser** (Chrome, Edge, Brave) - **Recommended for best compatibility**
  - ⚠️ **Firefox may have issues with video streaming and audio playback**

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/OliseNS/Inferno.git
cd Inferno

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables (for Telegram - optional)
cp .env.example .env
# Edit .env with your favorite text editor:
nano .env  # or vim, code, etc.
# Add your TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID
```

### Running the System

```bash
# Run the full system (web dashboard + detection)
python webserver.py
```

Open your **Chromium-based browser** and navigate to:
- **Local:** `http://localhost:8080`
- **Network:** `http://<your-ip>:8080`

### Headless Mode (Optional)

Run detection only without the web interface:

```bash
python detection_system.py
```

---

## Repository layout

| Path | Purpose |
|------|---------|
| `webserver.py` | Flask app: dashboard, API, background detection |
| `detection_system.py` | Camera, YOLO, MediaPipe, motion, Telegram, alarm |
| `settings.json` | Non-secret runtime options (committed template; copy from `settings.example.json` if needed) |
| `.env` | **Secrets only** — `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` (create from `.env.example`, never commit) |
| `models/fire_smoke_yolo11_ncnn_model/` | YOLO11 NCNN export for fire/smoke (folder name must end with `_ncnn_model` for Ultralytics) |
| `static/`, `templates/` | Dashboard assets |
| `streaming_server/` | Optional MJPEG server (`server.py`, port 5000) |
| `scripts/ncnn_smoke_test.py` | Optional NCNN check (requires `ncnn` + `torch`) |

`system.model_path` in `settings.json` points at the YOLO export (default: `models/fire_smoke_yolo11_ncnn_model`). NCNN exports must live in a directory whose name ends with `_ncnn_model`. Override with another folder or `.pt` path.

---

## Environment variables

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Telegram bot token from [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHAT_ID` | Destination chat or group ID |

The dashboard can append/update these in `.env` when you save token/chat ID (non-empty fields only).

---

## 📋 System Requirements

### Minimum Requirements
- **OS:** Linux, macOS, or Windows 10/11
- **Python:** 3.10 or higher
- **RAM:** 2GB minimum (4GB recommended)
- **Storage:** 500MB for dependencies + model files
- **Camera:** USB webcam or IP camera (MJPEG/RTSP stream)

### Recommended for Raspberry Pi
- **Model:** Raspberry Pi 4 (4GB RAM or higher)
- **OS:** Raspberry Pi OS (64-bit recommended)
- **Camera:** Pi Camera Module or USB webcam
- **Optional:** MQ2 gas sensor, audio speaker for alarm

---

## 🎯 Configuration

### First Run

On first run, `settings.json` is automatically created with default values. You can modify it directly or use the web dashboard.

### Camera Setup

**Option 1: Built-in Camera (default)**
```json
{
  "system": {
    "camera_url": "",
    "camera_index": 0
  }
}
```

**Option 2: IP Camera Stream**
```json
{
  "system": {
    "camera_url": "http://192.168.1.100:8081/video"
  }
}
```

**Option 3: Camera by Index**
```json
{
  "system": {
    "camera_url": "1"
  }
}
```

### Telegram Setup (Optional)

1. Create a bot with [@BotFather](https://t.me/BotFather)
2. Get your chat ID from [@userinfobot](https://t.me/userinfobot)
3. Add to `.env`:

```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

4. Enable in dashboard or `settings.json`:

```json
{
  "telegram": {
    "enabled": true,
    "cooldown": 30
  }
}
```

---

## 🎨 Dashboard Features

### Detection Controls
- Toggle fire, smoke, motion, and face detection on/off
- Show/hide bounding boxes on video feed
- Adjust detection sensitivity in settings

### Real-Time Monitoring
- Live camera feed with detection overlays
- System status indicator (Normal/Fire/Smoke/Motion/Face)
- Frame counter and system uptime
- Recent face gallery
- Detection image gallery

### Text-to-Speech
- Type any message and hear it through your browser
- TTS history with click-to-replay
- Uses Google Text-to-Speech (gTTS)

### Telegram Integration
- Test connection with one click
- View credentials status
- Adjust notification cooldown
- Automatic alerts with detection images

---

## 🛠️ Troubleshooting

### Video Feed Not Loading

**Problem:** Black screen or "Waiting for camera..."

**Solutions:**
1. Check camera connection: `ls /dev/video*` (Linux)
2. Try different camera index in settings (0, 1, 2, etc.)
3. Ensure no other application is using the camera
4. For IP cameras, verify the stream URL is accessible

### Audio/TTS Not Working

**Problem:** No sound when using TTS

**Solutions:**
1. **Use a Chromium-based browser** (Chrome, Edge, Brave)
2. Check browser audio permissions
3. Ensure speakers/headphones are connected and volume is up
4. Try clicking the play button in the browser if autoplay is blocked

### Firefox Compatibility Issues

**Problem:** Video stuttering or TTS not playing

**Solution:** Firefox has known issues with MJPEG streams and audio playback. **Please use Chrome, Edge, or Brave** for the best experience.

### Detection Not Working

**Problem:** No detections appearing

**Solutions:**
1. Check if detection types are enabled in dashboard
2. Verify model path in `settings.json` points to correct YOLO model
3. Ensure proper lighting for fire/smoke detection
4. Check console logs for errors: `tail -f logs/inferno.log`

### Telegram Alerts Not Sending

**Problem:** Test message fails

**Solutions:**
1. Verify token and chat ID in `.env` are correct
2. Check bot is not blocked
3. Ensure internet connection is stable
4. Check Telegram is enabled in settings
5. Verify cooldown period hasn't been triggered

### Raspberry Pi Performance Issues

**Problem:** Slow frame rate or system lag

**Solutions:**
1. Reduce video resolution in camera settings
2. Increase `detection_interval` in settings (e.g., 1.0 seconds)
3. Disable face detection if not needed (most CPU-intensive)
4. Use NCNN model for better performance
5. Ensure Pi has adequate cooling

### Permission Errors

**Problem:** "Permission denied" when accessing camera or GPIO

**Solutions:**
```bash
# Add user to video group (Linux)
sudo usermod -a -G video $USER

# For GPIO on Raspberry Pi
sudo usermod -a -G gpio $USER

# Reboot after changes
sudo reboot
```

## 📊 Logs

All console output (stdout/stderr) is automatically logged to **`logs/inferno.log`**. The `logs/` directory is created automatically.

```bash
# View live logs
tail -f logs/inferno.log

# Search for errors
grep "ERROR" logs/inferno.log
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📝 Tips for Best Results

### Fire Detection
- Ensure good lighting conditions
- Position camera to have clear view of monitored areas
- Test with different angles for optimal detection

### Face Detection
- Adequate lighting is crucial for face detection
- Faces should be reasonably front-facing
- Works best at 1-3 meters distance

### Motion Detection
- Minimize background movement (curtains, fans)
- Adjust `min_area` in code if getting too many false positives
- Works better with static camera mount

### System Performance
- Start with fewer detection types enabled
- Gradually enable more as needed
- Monitor system resources (CPU, RAM)
- On Raspberry Pi, consider using lower resolution camera

---

## 🌟 Project Highlights

- **Modern UI:** Beautiful gradient design with smooth animations
- **Real-time Processing:** Low-latency detection with optimized frame processing
- **Flexible Configuration:** Everything configurable via JSON or web UI
- **Privacy-First:** All processing happens locally, no cloud dependencies
- **Production Ready:** Logging, error handling, and graceful degradation
- **Extensible:** Easy to add new detection types or notification channels

---

## 📞 Support

If you encounter any issues or have questions:

1. Check the [Troubleshooting](#-troubleshooting) section
2. Review logs in `logs/inferno.log`
3. Open an issue on [GitHub](https://github.com/OliseNS/Inferno/issues)

---

## 👨‍💻 Author

**OliseNS** — [GitHub](https://github.com/OliseNS)

Built with ❤️ using Python, Flask, OpenCV, YOLO11, and MediaPipe.

---

## 📄 License

No license file is included yet; contact the author for usage terms.

---

## ⚡ Quick Command Reference

```bash
# Start system
python webserver.py

# Check logs
tail -f logs/inferno.log

# Update dependencies
pip install -r requirements.txt --upgrade

# Reset configuration
rm settings.json  # Will be recreated with defaults

# Clear old detections
rm -rf faces/* detections/* voices/*
```

---

**⭐ If you find this project useful, please consider giving it a star on GitHub!**
