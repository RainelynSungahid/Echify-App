"""
main.py
========
FastAPI application entry point — with session lifecycle management.

Logging is temporarily disabled.
To enable again later, search for: ENABLE_LOGGING
"""

from contextlib import asynccontextmanager
from datetime import datetime
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.camera.shared_camera import shared_camera
from src.audio.shared_mic import shared_mic

from src.gesture.ws_fsl_server import router as fsl_router
from src.gesture.ws_fsl_dynamic_server import router as fsl_dynamic_router
from src.stt.stt_http import router as stt_router
from src.routes.preview import router as preview_router
from src.stt.ws_stt_live import router as stt_live_router
from src.gesture.fsl_dynamic_inference import initialize_dynamic_model
from src.stt.ws_stt_live import get_model as get_stt_model

# ENABLE_LOGGING
# from session_logger import SessionLogger


# ENABLE_LOGGING
# _server_logger: SessionLogger | None = None
_server_logger = None


def get_server_logger():
    return _server_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _server_logger

    startup_ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # ENABLE_LOGGING
    # _server_logger = SessionLogger(
    #     session_label=f"Server_Session_{startup_ts}",
    #     log_dir="logs"
    # )
    # _server_logger.start_session()

    print("=" * 60)
    print("🚀 FSL Communication System — Server Started")
    print(f"   Session ID : {startup_ts}")
    print("   Logging    : DISABLED")
    print("=" * 60)

    import asyncio
    loop = asyncio.get_event_loop()

    shared_camera.start()
    shared_mic.start()

    print("⏳ Pre-loading STT model...")
    await loop.run_in_executor(None, get_stt_model)
    print("✅ STT model ready.")

    print("⏳ Pre-loading FSL dynamic model...")
    await loop.run_in_executor(None, initialize_dynamic_model)
    print("✅ FSL dynamic model ready.")

    yield

    shared_camera.stop()
    shared_mic.stop()

    # ENABLE_LOGGING
    # if _server_logger:
    #     _server_logger.end_session()

    print("✅ Shutdown complete.")


app = FastAPI(
    title="FSL Bidirectional Communication System",
    lifespan=lifespan 
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Keep exactly what already works
app.include_router(fsl_router)
app.include_router(stt_router)
app.include_router(fsl_dynamic_router)
app.include_router(stt_live_router)
app.include_router(preview_router)


@app.post("/sos/trigger")
async def sos_trigger(request: Request):
    logger = get_server_logger()

    t8 = time.monotonic()
    t8_dt = datetime.now().strftime("%H:%M:%S.%f")[:-3]

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})

    state = body.get("state", "unknown")
    response_time_ms = float(body.get("response_time_ms", 0.0))
    success = bool(body.get("success", True))
    client_id = body.get("client_id", "unknown")

    server_receive_ms = (time.monotonic() - t8) * 1000

    print(f"\n  [SOS T8] Received @ {t8_dt}")
    print(f"  {'─'*50}")
    print("  🆘 SOS EVENT")
    print(f"     State            : {state}")
    print(f"     Frontend response: {response_time_ms:.1f} ms  (button → audio)")
    print(f"     Server receive   : {server_receive_ms:.1f} ms")
    print(f"     Client           : {client_id}")
    print(f"     Result           : {'✅ PASS' if success else '❌ FAIL'}")
    print(f"  {'─'*50}\n")

    # ENABLE_LOGGING
    # if logger:
    #     logger.log_sos(
    #         response_time_ms=response_time_ms,
    #         state=state,
    #         success=success,
    #         notes=f"client_id={client_id}|server_receive_ms={server_receive_ms:.2f}"
    #     )

    return JSONResponse(content={
        "logged": False,
        "state": state,
        "response_time_ms": response_time_ms,
        "success": success,
    })


@app.get("/session/summary")
async def session_summary():
    logger = get_server_logger()
    if not logger:
        return JSONResponse(content={
            "logging": "disabled",
            "message": "No active session logger."
        })

    g_events = logger._gesture_events
    t_events = logger._tts_latencies
    s_events = logger._stt_events
    o_events = logger._sos_events

    def avg(lst):
        return round(sum(lst) / len(lst), 2) if lst else 0

    return JSONResponse(content={
        "session_label": logger.session_label,
        "gesture": {
            "total": len(g_events),
            "avg_conf": avg([e["confidence"] for e in g_events]),
            "avg_infer_ms": avg([e["inference_ms"] for e in g_events]),
        },
        "tts": {
            "total": len(t_events),
            "avg_latency": avg(t_events),
        },
        "stt": {
            "total": len(s_events),
            "quiet_count": len([e for e in s_events if e["environment"] == "quiet"]),
            "noisy_count": len([e for e in s_events if e["environment"] == "noisy"]),
        },
        "sos": {
            "total": len(o_events),
            "passed": len([e for e in o_events if e["success"]]),
            "avg_response": avg([e["response_ms"] for e in o_events]),
        },
        # ENABLE_LOGGING
        # "csv_path": str(logger._csv_path),
        # "summary_path": str(logger._summary_path),
    })


# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware


# from src.camera.shared_camera import shared_camera
# from src.audio.shared_mic import shared_mic

# from src.gesture.ws_fsl_server import router as fsl_router
# from src.stt.stt_http import router as stt_router
# from src.routes.preview import router as preview_router
# from src.stt.ws_stt_live import router as stt_live_router


# app = FastAPI()

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# @app.on_event("startup")
# def startup_event():
#     shared_camera.start()

# @app.on_event("shutdown")
# def shutdown_event():
#     shared_camera.stop()

# app.include_router(fsl_router)
# app.include_router(stt_router)
# app.include_router(stt_live_router)
# app.include_router(preview_router)