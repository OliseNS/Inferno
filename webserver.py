import os
import sys
import threading
import time
import queue
import subprocess
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
from inferno_logging import setup_logging

setup_logging(_ROOT)

import cv2
import numpy as np
from flask import Flask, Response, render_template, request, jsonify, send_from_directory
from gtts import gTTS

import detection_system as dsm
from detection_system import init_detection_system, start_detection_system

# Initialize Flask app
app = Flask(__name__, static_folder="static", template_folder="templates")

# Initialize detection system (singleton in detection_system module)
detection_system = init_detection_system()

# Create a queue for TTS requests
tts_queue = queue.Queue()

# Function to process TTS requests from the queue
def process_tts_queue():
    voices_dir = os.path.join(os.getcwd(), 'voices')
    os.makedirs(voices_dir, exist_ok=True)  # Ensure the voices directory exists

    while True:
        text = tts_queue.get()
        if text is None:
            break

        try:
            print(f"[TTS] Speaking: {text}")
            # Use gTTS to synthesize audio
            tts = gTTS(text=text, lang='en')
            temp_mp3 = os.path.join(voices_dir, "temp_tts.mp3")
            tts.save(temp_mp3)

            # Play the audio file using mpg321
            subprocess.run(["mpg321", "-q", temp_mp3])

            # Remove the temporary audio file
            os.remove(temp_mp3)
        except Exception as e:
            print(f"[TTS Error] {str(e)}")
        finally:
            tts_queue.task_done()

# Start a background thread to process the TTS queue
tts_thread = threading.Thread(target=process_tts_queue, daemon=True)
tts_thread.start()

# Start detection system in a separate thread
detection_thread = None

connected_clients = 0

# Cached JPEG used when the detector has not produced a frame yet (must yield quickly
# so single-threaded dev servers are not blocked forever on /video_feed).
_PLACEHOLDER_JPEG: bytes | None = None


def _placeholder_jpeg() -> bytes:
    global _PLACEHOLDER_JPEG
    if _PLACEHOLDER_JPEG is None:
        img = np.zeros((240, 320, 3), dtype=np.uint8)
        cv2.putText(
            img,
            "Waiting for camera...",
            (24, 125),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (200, 200, 200),
            1,
            cv2.LINE_AA,
        )
        ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 72])
        _PLACEHOLDER_JPEG = buf.tobytes() if ok else b""
    return _PLACEHOLDER_JPEG


def _mjpeg_chunk(jpeg_bytes: bytes) -> bytes:
    return b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg_bytes + b"\r\n"


def _video_feed_url() -> str:
    """Built-in MJPEG from detection thread, or external URL when configured."""
    cam = (detection_system.config_manager.get_public_config()["system"].get("camera_url") or "").strip()
    return cam if cam else "/video_feed"


@app.route("/video_feed")
def video_feed():
    """MJPEG stream from the same frames the detector processes (with overlays)."""

    def generate():
        placeholder = _placeholder_jpeg()
        # First chunk must be sent immediately so the handler never blocks without yielding.
        yield _mjpeg_chunk(placeholder)
        none_rounds = 0
        while True:
            frame = detection_system.get_latest_frame()
            if frame is None:
                time.sleep(0.05)
                none_rounds += 1
                # Keep stream alive if camera is slow; avoid hammering the client.
                if none_rounds % 10 == 0:
                    yield _mjpeg_chunk(placeholder)
                continue
            none_rounds = 0
            ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 82])
            if not ok:
                continue
            yield _mjpeg_chunk(buf.tobytes())

    return Response(
        generate(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate", "Pragma": "no-cache"},
    )


@app.route("/")
def index():
    """Render the main dashboard: built-in /video_feed unless camera_url is set."""
    pub = detection_system.config_manager.get_public_config()
    camera_url = (pub["system"].get("camera_url") or "").strip()
    return render_template(
        "index.html",
        camera_url=camera_url,
        video_feed_url=_video_feed_url(),
    )

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration"""
    return jsonify(detection_system.config_manager.get_public_config())

@app.route('/api/config', methods=['POST'])
def update_config():
    try:
        data = request.json
        section = data.get('section')
        values = data.get('values')
        detection_system.config_manager.update_section(section, values)
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/status', methods=['GET'])
def get_status():
    try:
        status = detection_system.system_status
        return jsonify({"status": status}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/faces', methods=['GET'])
def get_faces():
    try:
        faces = detection_system.get_faces()
        return jsonify({"faces": faces}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/alarm/stop', methods=['POST'])
def stop_alarm():
    """Stop the alarm"""
    try:
        detection_system.stop_alarm()
        detection_system.system_status = "Normal"
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/telegram/test', methods=['POST'])
def test_telegram():
    """Send a test message to verify Telegram configuration"""
    try:
        success = detection_system.test_telegram()
        return jsonify({"success": success})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/tts', methods=['POST'])
def text_to_speech():
    """Convert text to speech using gTTS and return audio file"""
    try:
        data = request.json
        text = data.get('text', '')

        if not text:
            return jsonify({"success": False, "error": "No text provided"})

        # Generate audio file
        voices_dir = os.path.join(os.getcwd(), 'voices')
        os.makedirs(voices_dir, exist_ok=True)

        # Create unique filename
        timestamp = time.time()
        filename = f"tts_{int(timestamp)}.mp3"
        filepath = os.path.join(voices_dir, filename)

        # Generate speech using gTTS
        tts = gTTS(text=text, lang='en')
        tts.save(filepath)

        # Also play on server if available
        try:
            tts_queue.put(text)
        except:
            pass

        return jsonify({
            "success": True,
            "message": "Speech generated",
            "audio_url": f"/voices/{filename}"
        })
    except Exception as e:
        print(f"TTS Error: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    try:
        stats = detection_system.get_statistics()
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/detections', methods=['GET'])
def get_detections():
    try:
        detection_folder = os.path.join(os.getcwd(), 'detections')
        if not os.path.exists(detection_folder):
            os.makedirs(detection_folder, exist_ok=True)
            return jsonify({"detections": []}), 200

        detection_images = sorted(
            [img for img in os.listdir(detection_folder) if img.endswith(('.jpg', '.png'))],
            key=lambda x: os.path.getmtime(os.path.join(detection_folder, x)),
            reverse=True
        )

        return jsonify({"detections": detection_images}), 200
    except Exception as e:
        print(f"Error in get_detections: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/detections/<path:filename>')
def serve_detection(filename):
    """Serve detection images"""
    return send_from_directory('detections', filename)

@app.route('/faces/<path:filename>')
def serve_face(filename):
    """Serve face images"""
    return send_from_directory('faces', filename)

@app.route('/voices/<path:filename>')
def serve_voice(filename):
    """Serve TTS audio files"""
    return send_from_directory('voices', filename)

@app.route("/api/restart", methods=["POST"])
def restart_system():
    """Restart the detection pipeline in-process (Flask keeps running)."""
    global detection_thread, detection_system

    def _restart():
        global detection_thread, detection_system
        try:
            tts_queue.put("Detection subsystem restarting.")
        except Exception:
            pass
        try:
            if dsm.detection_system is not None:
                dsm.detection_system.running = False
            if detection_thread is not None and detection_thread.is_alive():
                detection_thread.join(timeout=25)
            dsm.detection_system = None
            detection_system = init_detection_system()
            detection_thread = threading.Thread(target=detection_system.run, daemon=True)
            detection_thread.start()
        except Exception as e:
            print(f"Restart Error: {e}")

    try:
        threading.Thread(target=_restart, daemon=True).start()
        return jsonify(
            {
                "success": True,
                "message": "Detection system is restarting. The page stays up; video may flicker briefly.",
            }
        )
    except Exception as e:
        print(f"Restart Error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

def start_web_server(host='0.0.0.0', port=8080):
    """Start the Flask web server"""
    global detection_thread

    if detection_thread is None or not detection_thread.is_alive():
        detection_thread = start_detection_system()
        time.sleep(2)
        tts_queue.put("System started successfully.")
        
        # Send Telegram welcome message after system is ready
        detection_system.telegram_service.send_welcome_message()

if __name__ == '__main__':
    os.makedirs('faces', exist_ok=True)
    os.makedirs('detections', exist_ok=True)
    print(f"Starting web server on http://0.0.0.0:8080")
    print(f"Detection system will run in the background")
    print(f"Press Ctrl+C to exit")

    start_web_server()
    # threaded=True: /video_feed is long-lived; without this the dev server can only
    # handle one request at a time and the dashboard never loads while the stream connects.
    app.run(host="0.0.0.0", port=8080, threaded=True, use_reloader=False)