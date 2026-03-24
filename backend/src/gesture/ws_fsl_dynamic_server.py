"""
ws_fsl_dynamic_server.py
========================
Dynamic FSL Gesture Recognition — WebSocket Server

Timing:
  T1 = frame received
  T2 = inference done
  T3 = response sent
"""

import sys
import base64
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

# sys.path fix FIRST
_BACKEND_ROOT = Path(__file__).parent.parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

# Local imports
from src.gesture.sentence_builder import SentenceBuilder
from src.gesture.fsl_dynamic_inference import (
    initialize_dynamic_model,
    update_and_maybe_predict,
    reset_buffer,
    get_model_info,
)
from src.tts.tts_engine import speak
from session_logger import global_logger, get_mic_dbfs

# SharedMic — safe import
try:
    from src.audio.shared_mic import shared_mic
    _MIC_AVAILABLE = True
except Exception as _mic_err:
    print(f"WARNING: SharedMic not available: {_mic_err}")
    shared_mic = None
    _MIC_AVAILABLE = False

router = APIRouter()


def _strip_data_url(frame_b64: str) -> str:
    if frame_b64 and frame_b64.lower().startswith("data:") and "," in frame_b64:
        return frame_b64.split(",", 1)[1]
    return frame_b64


def _decode_frame(frame_b64: str):
    frame_b64 = _strip_data_url(frame_b64)
    try:
        img_bytes = base64.b64decode(frame_b64)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if frame is None:
            return None

        # ✅ FIX 1: Mirror like webcam
        frame = cv2.flip(frame, 1)

        # ✅ FIX 2: Force consistent resolution
        frame = cv2.resize(frame, (640, 480))

        return frame

    except Exception as e:
        print(f"Frame decode error: {e}")
        return None


@router.websocket("/ws/fsl-dynamic")
async def fsl_dynamic_endpoint(websocket: WebSocket):
    await websocket.accept()

    client_id  = f"{websocket.client.host}:{websocket.client.port}"
    session_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"\n[DYNAMIC] Client connected: {client_id}")

    # Initialize model
    try:
        initialize_dynamic_model()
        print(f"[DYNAMIC] Model ready: {get_model_info()}")
    except Exception as e:
        await websocket.send_json({"error": str(e), "prediction": "ERROR"})
        await websocket.close()
        return

    # Mark this connection in the global CSV
    global_logger.log_reconnect("Sign->TTS", client_id)

    # Per-connection state
    builder = SentenceBuilder()
    frame_count = 0

    frame_latencies_ms  = []
    inference_latencies = []
    gesture_intervals   = []
    last_gesture_time   = None
    last_printed_status = None

    print("\n" + "=" * 55)
    print("  LIVE STATUS LOG (prints only on change)")
    print("  [.] = no hand   [H] = hand seen   [C] = collecting")
    print("  [OK] = gesture predicted   [S] = sentence ready")
    print("=" * 55 + "\n")

    try:
        while True:
            # T1: frame received
            t1_received = time.monotonic()
            frame_b64   = await websocket.receive_text()
            frame_count += 1

            if frame_count <= 5 or frame_count % 30 == 0:
                print(f"Frame received from {client_id} | frame #{frame_count} | size={len(frame_b64)}")

            frame = _decode_frame(frame_b64)
            if frame is None:
                error_payload = {
                    "is_ready": False,
                    "top1_label": "DECODE_ERROR",
                    "top1_conf": 0.0,
                    "sentence_raw": None,
                    "sentence_english": None,
                    "debug": {
                        "frame_no": frame_count,
                        "hands_detected": False,
                        "collecting": False,
                        "frames_collected": 0,
                        "consec_hand": 0,
                        "consec_nohand": 0,
                        "status": "DECODE_ERROR"
                    }
                }
                await websocket.send_json(error_payload)
                continue

            if frame is not None and (frame_count <= 5 or frame_count % 30 == 0):
                print(f"Decoded frame #{frame_count} | shape={frame.shape}")

            # T2: inference/update
            t2_infer_start = time.monotonic()
            result         = update_and_maybe_predict(frame)
            t2_infer_end   = time.monotonic()

            inference_ms = (t2_infer_end - t2_infer_start) * 1000
            inference_latencies.append(inference_ms)

            dbg           = result.get("debug", {})
            collecting    = bool(dbg.get("collecting", False))
            frames_in_seg = int(dbg.get("frames_collected", 0))
            consec_hand   = int(dbg.get("consec_hand", 0))
            consec_nohand = int(dbg.get("consec_nohand", 0))
            is_ready      = bool(result.get("is_ready", False))
            top1_label    = result.get("top1_label", "Waiting...")
            hands_now     = consec_hand > 0

            if frame_count <= 5 or frame_count % 30 == 0:
                print(
                    f"Result #{frame_count} | "
                    f"label={result.get('top1_label')} | "
                    f"ready={result.get('is_ready')} | "
                    f"debug={result.get('debug', {})}"
                )

            # Status key for terminal logging
            if is_ready:
                status_key = f"READY:{top1_label}"
            elif top1_label == "Too short / ignored":
                status_key = "TOO_SHORT"
            elif collecting:
                status_key = f"COLLECTING:{(frames_in_seg // 3) * 3}"
            elif hands_now:
                status_key = f"HAND:{consec_hand}"
            else:
                status_key = f"NOHAND:{(consec_nohand // 3) * 3}"

            if status_key != last_printed_status:
                ts = datetime.now().strftime("%H:%M:%S")
                if is_ready:
                    conf = result.get("top1_conf", 0.0)
                    print(f"\n  [OK] [{ts}] PREDICTED -> {top1_label} ({conf:.0%})")
                elif top1_label == "Too short / ignored":
                    print(f"  [X] [{ts}] TOO SHORT -- {frames_in_seg} frames")
                elif collecting:
                    print(f"  [C] [{ts}] COLLECTING... {frames_in_seg} frames")
                elif hands_now:
                    print(f"  [H] [{ts}] HAND DETECTED -- {consec_hand}/2 needed")
                else:
                    print(f"  [.] [{ts}] Waiting... (frame #{frame_count})")
                last_printed_status = status_key

            # Build response
            enriched = {
                **result,
                "sentence_raw": None,
                "sentence_english": None,
                "debug": {
                    "frame_no": frame_count,
                    "hands_detected": hands_now,
                    "collecting": collecting,
                    "frames_collected": frames_in_seg,
                    "consec_hand": consec_hand,
                    "consec_nohand": consec_nohand,
                    "status": status_key,
                    "inference_ms": round(inference_ms, 1),
                    "frame_size": f"{frame.shape[1]}x{frame.shape[0]}",
                }
            }

            # Feed pause into sentence builder every frame
            sentence_result = builder.update_pause(hands_now)

            # On completed gesture, log + feed token
            if is_ready:
                label = result.get("top1_label", "UNKNOWN")
                conf  = result.get("top1_conf", 0.0)

                now_ts = time.monotonic()
                if last_gesture_time is not None:
                    gesture_intervals.append((now_ts - last_gesture_time) * 1000)
                last_gesture_time = now_ts

                global_logger.log_gesture(
                    predicted_label=label,
                    confidence=conf,
                    frames_collected=frames_in_seg,
                    inference_time_ms=inference_ms,
                    ground_truth=None,
                    notes=f"frame_no={frame_count}|client={client_id}"
                )

                token_result = builder.add_token(label)
                if token_result:
                    sentence_result = token_result

            # Finalize sentence and speak
            if sentence_result:
                raw, english = sentence_result

                current_dbfs = get_mic_dbfs(shared_mic)

                enriched["sentence_raw"]     = raw
                enriched["sentence_english"] = english

                builder.reset()

                ts     = datetime.now().strftime("%H:%M:%S")
                db_str = f" | {current_dbfs:.1f} dBFS" if current_dbfs is not None else ""
                print(f"\n  [S] [{ts}] SENTENCE FINALIZED{db_str}")
                print(f"       Signs   : {raw}")
                print(f"       English : \"{english}\"")
                print(f"       -> Speaking...\n")

                tts_latency_ms = 0.0
                try:
                    tts_t0 = time.monotonic()
                    speak(english)
                    tts_latency_ms = (time.monotonic() - tts_t0) * 1000
                except Exception as e:
                    print(f"TTS error: {e}")

                global_logger.log_tts(
                    text=english,
                    tts_latency_ms=tts_latency_ms,
                    dbfs=current_dbfs,
                    notes=f"sentence_raw={raw}|frame_no={frame_count}"
                )

            # T3: send response
            await websocket.send_json(enriched)
            t3_sent = time.monotonic()

            total_server_ms = (t3_sent - t1_received) * 1000
            frame_latencies_ms.append(total_server_ms)
            enriched["debug"]["server_total_ms"] = round(total_server_ms, 1)

            if frame_count % 30 == 0:
                avg_inf = sum(inference_latencies[-30:]) / min(30, len(inference_latencies))
                avg_srv = sum(frame_latencies_ms[-30:]) / min(30, len(frame_latencies_ms))
                print(
                    f"  [FRAME {frame_count:>5}]  "
                    f"inference={avg_inf:.1f}ms (avg30)  "
                    f"server_total={avg_srv:.1f}ms (avg30)  "
                    f"pred={result.get('top1_label', '?')}  "
                    f"ready={result.get('is_ready', False)}"
                )

    except WebSocketDisconnect:
        print(f"\nDisconnected: {client_id} | frames={frame_count}")

    except Exception as e:
        print(f"Error [{client_id}]: {e}")
        import traceback
        traceback.print_exc()
        try:
            await websocket.close()
        except Exception:
            pass

    finally:
        reset_buffer()
        builder.reset()

        if frame_latencies_ms:
            avg_inf = sum(inference_latencies) / len(inference_latencies) if inference_latencies else 0.0
            avg_srv = sum(frame_latencies_ms) / len(frame_latencies_ms)
            p95_srv = sorted(frame_latencies_ms)[int(len(frame_latencies_ms) * 0.95)]
            print(f"\n  Frame-level Stats ({frame_count} frames total)")
            print(f"     Avg inference      : {avg_inf:.2f} ms")
            print(f"     Avg server total   : {avg_srv:.2f} ms")
            print(f"     P95 server total   : {p95_srv:.2f} ms")
            if gesture_intervals:
                avg_interval = sum(gesture_intervals) / len(gesture_intervals)
                print(f"     Avg gesture interval: {avg_interval:.2f} ms")