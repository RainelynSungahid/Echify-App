import asyncio
import sys
import base64
import time
from datetime import datetime
from pathlib import Path
 
import cv2
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
 
_BACKEND_ROOT = Path(__file__).parent.parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))
 
from src.gesture.sentence_builder import SentenceBuilder
from src.gesture.fsl_dynamic_inference import (
    initialize_dynamic_model,
    update_and_maybe_predict,
    reset_buffer,
    get_model_info,
)
from src.tts.tts_engine import speak
from session_logger import global_logger, get_mic_dbfs
 
try:
    from src.audio.shared_mic import shared_mic
except:
    shared_mic = None
 
router = APIRouter()
 
_inference_busy = False
 
 
def _strip_data_url(frame_b64: str) -> str:
    if frame_b64.startswith("data:"):
        return frame_b64.split(",", 1)[1]
    return frame_b64
 
 
def _decode_frame_sync(frame_b64: str):
    try:
        frame_b64 = _strip_data_url(frame_b64)
        img_bytes = base64.b64decode(frame_b64)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        return frame
    except Exception as e:
        print("Decode error:", e)
        return None
 
 
@router.websocket("/ws/fsl-dynamic")
async def fsl_dynamic_endpoint(websocket: WebSocket):
    global _inference_busy
 
    await websocket.accept()
    print("Client connected")
 
    try:
        initialize_dynamic_model()
    except Exception as e:
        await websocket.send_json({"error": str(e)})
        return
 
    builder = SentenceBuilder()
    loop = asyncio.get_event_loop()
 
    try:
        while True:
            frame_b64 = await websocket.receive_text()
 
            if _inference_busy:
                await websocket.send_json({
                    "is_ready": False,
                    "top1_label": "SKIPPED",
                    "top1_conf": 0.0,
                    "sentence_english": None,
                })
                continue
 
            frame = await loop.run_in_executor(None, _decode_frame_sync, frame_b64)
 
            if frame is None:
                await websocket.send_json({
                    "is_ready": False,
                    "top1_label": "DECODE_ERROR",
                    "top1_conf": 0.0,
                    "sentence_english": None,
                })
                continue
 
            _inference_busy = True
            try:
                result = await loop.run_in_executor(None, update_and_maybe_predict, frame)
            finally:
                _inference_busy = False
 
            dbg = result.get("debug", {})
            consec_hand = int(dbg.get("consec_hand", 0))
            hands_now = consec_hand > 0
            is_ready = result.get("is_ready", False)
 
            enriched = {
                **result,
                "sentence_raw": None,
                "sentence_english": None,
            }
 
            # ✅ FIX 1: Check for pause-based sentence completion
            sentence_result = builder.update_pause(hands_now)
 
            # ✅ FIX 2: Add recognized tokens to the builder
            if is_ready:
                label = result.get("top1_label", "UNKNOWN")
                token_result = builder.add_token(label)
                if token_result:
                    sentence_result = token_result
 
            # ✅ FIX 3: Speak IMMEDIATELY when sentence is ready
            if sentence_result:
                raw, english = sentence_result
                enriched["sentence_raw"] = raw
                enriched["sentence_english"] = english
                
                print("\n[SENTENCE READY]")
                print("RAW:", raw)
                print("ENGLISH:", english)
                print("[SPEAKING NOW]", english)
                
                # ✅ SPEAK IMMEDIATELY (don't wait for hands to disappear)
                try:
                    await loop.run_in_executor(None, speak, english)
                except Exception as e:
                    print("TTS error:", e)
                
                # Reset builder for next sentence
                builder.reset()
 
            await websocket.send_json(enriched)
 
    except WebSocketDisconnect:
        print("Disconnected")
    finally:
        _inference_busy = False
        reset_buffer()
        builder.reset()