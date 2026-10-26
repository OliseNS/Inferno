# Architecture

Two processes' worth of work in one Python process: a capture/detect loop and a
Flask app that serves the dashboard and the MJPEG stream. They share one
`DetectionSystem` instance and one frame buffer guarded by a lock.

```
                    ┌─────────────────────────────────────────┐
  USB / IP cam ────►│ Camera.read_frame()                     │
                    │        │                                │
                    │        ▼                                │
                    │ resize → 224×224                        │
                    │        │                                │
                    │        ├──► YOLO11 (NCNN) fire/smoke ────┤
                    │        ├──► MediaPipe face              │
                    │        ├──► MOG2 motion                 │
                    │        └──► MQ-2 D0 pin                 │
                    │                 │                       │
                    │                 ▼                       │
                    │        AlarmStateMachine.update()        │
                    │                 │                       │
                    │        ┌────────┴────────┐              │
                    │        ▼                 ▼              │
                    │  siren (aplay)   notify_queue ──► worker ──► Telegram
                    │                                          │
                    │  latest_frame (lock)                     │
                    └────────────┬─────────────────────────────┘
                                 ▼
                        Flask /video_feed (MJPEG)
                        Flask /api/*  (status, config, faces, detections)
```

## Threads

| Thread | Started by | Job |
|---|---|---|
| Main | `webserver.py` | Flask dev server, `threaded=True` so `/video_feed` cannot block it |
| Detection | `start_detection_system()` | capture → detect → decide → draw overlays |
| Notification worker | `DetectionSystem.__init__` | drain `notify_queue`, talk to Telegram |
| Alarm loop | `play_alarm_sound()` | re-trigger `alarm.wav` while the alarm is on |
| TTS worker | `webserver.py` | gTTS synthesis + `mpg321` playback |

Shared state is `latest_frame` (behind `frame_lock`), `system_status`,
`last_detections` and `recent_faces`. Reads are of simple values, so the design
avoids long critical sections; the frame buffer is copied on publish and on read.

## Files

| Path | Role |
|---|---|
| `detection_system.py` | Camera, detectors, MQ-2, alarm wiring, notification worker, disk retention |
| `alarm_logic.py` | Pure decision logic — no hardware, no network, unit tested |
| `webserver.py` | Flask app, REST API, MJPEG stream, TTS |
| `inferno_logging.py` | Tees stdout/stderr to `logs/inferno.log` |
| `templates/index.html`, `static/main.js` | Dashboard |
| `models/fire_smoke_yolo11_ncnn_model/` | YOLO11 NCNN export (folder must end in `_ncnn_model`) |
| `scripts/ncnn_smoke_test.py` | Offline check that the NCNN export still loads |
| `streaming_server/server.py` | Standalone MJPEG server, no detection (port 5000) |

## The detection tick

One tick every `system.detection_interval` seconds (default 0.5 s):

1. Read a frame; on failure, count consecutive failures and reconnect after 5.
2. Resize once to `224×224` and reuse it for every detector.
3. Run enabled detectors. Fire/smoke boxes are scaled back to the original frame
   and drawn there, so the dashboard shows full-resolution evidence.
4. Read the MQ-2 pin.
5. Feed fire / smoke / gas into the state machine, one tick.
6. If a detection image was written, prune `detections/` down to
   `system.max_saved_detections` (default 200, oldest first).
7. Publish the overlaid frame for `/video_feed`.

Steps 1-2 and 7 run whether or not a detection was found; steps 3-6 only on a
tick boundary, which is what keeps the stream smooth while the model runs.

## Why 224×224 and NCNN

Fire and smoke are large, low-frequency regions; the model does not need
resolution to find them. 224 keeps inference in the tens of milliseconds on a Pi
4. The model is exported to NCNN and committed, so the Pi never has to convert it
— and `.pt` weights are not needed at runtime at all.

## Disk layout

| Directory | Written by | Retention |
|---|---|---|
| `detections/` | fire/smoke boxes | newest `max_saved_detections`, pruned while running |
| `faces/` | face detector | newest `max_saved_faces` |
| `voices/` | TTS | deleted after playback |
| `logs/` | logging tee | append-only; rotate externally if needed |

`faces/` and `detections/` are cleared on startup: they are evidence from the
last session, not an archive. If you need an archive, ship them somewhere else.
