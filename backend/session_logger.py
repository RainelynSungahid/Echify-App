"""
session_logger.py
=================
Comprehensive testing session logger for FSL Bidirectional Communication System.

ONE CSV FOR THE ENTIRE PI SESSION (boot → shutdown).
─────────────────────────────────────────────────────
The CSV is opened once when the server starts and is appended to for ALL
subsequent WebSocket connections and flows:

  Flow A - Sign → TTS  : GESTURE + TTS rows  (ws_fsl_dynamic_server.py)
  Flow B - STT         : STT rows             (ws_stt_live.py)
  SOS                  : SOS rows             (main.py  /sos/trigger)

Every WebSocket reconnect just appends rows to the SAME file.
A RECONNECT marker row is written so you can slice sessions in post-processing.
The CSV is closed and the summary JSON is written when the Pi process exits
(via atexit) or when main.py calls global_logger.close() in the lifespan.

Usage:
    from session_logger import global_logger

    global_logger.start()                          # called once in lifespan startup
    global_logger.log_reconnect("Sign-TTS", cid)  # each WS connect
    global_logger.log_gesture(...)
    global_logger.log_tts(...)
    global_logger.log_stt(...)
    global_logger.log_sos(...)
    global_logger.close()                          # called once in lifespan shutdown

dB Notes:
  SharedMic._audio_callback computes RMS on a boosted+clipped mono signal.
  dBFS = 20 * log10(max(rms, 1e-5)),  floored at -100 dBFS.
    0 dBFS  = loudest possible (clipping)
  -20 dBFS  = typical speech in a quiet room
  -60 dBFS  = near silence
"""

import csv
import json
import math
import time
import atexit
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Optional

# ── Optional: WER ─────────────────────────────────────────────────────────────
try:
    from jiwer import wer as compute_wer
    WER_AVAILABLE = True
except ImportError:
    WER_AVAILABLE = False
    print("WARNING:  jiwer not installed - WER disabled. Run: pip install jiwer")


# ─────────────────────────────────────────────────────────────────────────────
# dB helpers  (also imported by server files)
# ─────────────────────────────────────────────────────────────────────────────

def rms_to_dbfs(rms: float) -> float:
    """
    Convert SharedMic linear RMS → dBFS (decibels relative to full scale).
    SharedMic clips audio to [-1, 1], so 1.0 RMS = 0 dBFS (max).
    Floored at -100 dBFS.
    """
    dbfs = 20.0 * math.log10(max(rms, 1e-5))
    return round(max(dbfs, -100.0), 2)


def get_mic_dbfs(shared_mic) -> Optional[float]:
    """
    Read current dBFS from a SharedMic instance.
    Returns None silently if mic is None or unavailable.
    """
    if shared_mic is None:
        return None
    try:
        return rms_to_dbfs(shared_mic.get_level())
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# SessionLogger
# ─────────────────────────────────────────────────────────────────────────────

class SessionLogger:
    """
    Persistent logger - ONE CSV file for the Pi's entire runtime.

    All WebSocket connections (Sign-TTS and STT) share the same instance
    via the module-level `global_logger` singleton at the bottom of this file.
    """

    EVENT_GESTURE   = "GESTURE"
    EVENT_TTS       = "TTS"
    EVENT_STT       = "STT"
    EVENT_SOS       = "SOS"
    EVENT_SESSION   = "SESSION"
    EVENT_RECONNECT = "RECONNECT"

    CSV_FIELDS = [
        "event_id",
        "event_type",
        "timestamp",
        "datetime",

        # Sign → TTS flow
        "predicted_label",
        "ground_truth",
        "is_correct",
        "confidence",
        "frames_collected",
        "inference_time_ms",

        # TTS
        "tts_text",
        "tts_latency_ms",
        "tts_dbfs",

        # STT flow
        "stt_transcript",
        "stt_reference",
        "stt_wer",
        "stt_latency_ms",
        "stt_environment",
        "stt_dbfs",

        # SOS
        "sos_state",
        "sos_response_time_ms",
        "sos_success",

        # Generic
        "notes",
    ]

    def __init__(self, log_dir: str = "logs", shared_mic=None):
        self.log_dir    = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.shared_mic = shared_mic

        # Filename is fixed at boot - never changes across reconnects
        boot_ts            = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._csv_path     = self.log_dir / f"session_{boot_ts}.csv"
        self._summary_path = self.log_dir / f"session_{boot_ts}_summary.json"

        self._lock          = Lock()
        self._event_counter = 0
        self._started       = False
        self._closed        = False
        self._boot_time     = time.monotonic()

        # Aggregates - accumulate across ALL connections for the full summary
        self._gesture_events: list = []
        self._tts_events:     list = []
        self._stt_events:     list = []
        self._sos_events:     list = []

        self._csv_file   = None
        self._csv_writer = None

        # Auto-close on Python exit so summary is always written
        atexit.register(self.close)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self):
        """
        Open the CSV and write the BOOT row.
        Idempotent - safe to call multiple times (only opens once).
        Called once from main.py lifespan startup.
        """
        if self._started:
            return
        self._started = True

        self._csv_file   = open(self._csv_path, "w", newline="", encoding="utf-8")
        self._csv_writer = csv.DictWriter(self._csv_file, fieldnames=self.CSV_FIELDS)
        self._csv_writer.writeheader()
        self._csv_file.flush()

        mic_status = "enabled" if self.shared_mic is not None else "disabled"
        print(f"\n{'='*60}")
        print(f"📋 SESSION LOGGER STARTED  (one CSV for entire Pi session)")
        print(f"   CSV     : {self._csv_path}")
        print(f"   Summary : {self._summary_path}")
        print(f"   Mic dB  : {mic_status}")
        print(f"{'='*60}\n")

        self._write_row({
            "event_type": self.EVENT_SESSION,
            "notes": f"BOOT mic_db={mic_status}",
        })

    def log_reconnect(self, flow: str, client_id: str = ""):
        """
        Write a RECONNECT marker row when a new WebSocket connection arrives.
        Lets you slice the CSV into individual connections in post-processing.

        Args:
            flow      : "Sign-TTS" or "STT"
            client_id : e.g. "192.168.1.5:50123"
        """
        self._ensure_started()
        self._write_row({
            "event_type": self.EVENT_RECONNECT,
            "notes": f"RECONNECT flow={flow} client={client_id}",
        })
        print(f"[LOGGER] 🔗 Reconnect - flow={flow} client={client_id}")

    def close(self):
        """
        Finalize the CSV: write SHUTDOWN row, close file, write summary JSON.
        Called from main.py lifespan shutdown OR automatically via atexit.
        Safe to call multiple times.
        """
        if self._closed or not self._started:
            return
        self._closed = True

        total_uptime = time.monotonic() - self._boot_time

        self._write_row({
            "event_type": self.EVENT_SESSION,
            "notes": f"SHUTDOWN total_uptime={total_uptime:.2f}s",
        })

        if self._csv_file:
            self._csv_file.close()

        summary = self._build_summary(total_uptime)
        with open(self._summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        self._print_summary(summary)
        return summary

    def _ensure_started(self):
        """Auto-start on first log call if start() wasn't called explicitly."""
        if not self._started:
            self.start()

    # ── Logging methods ───────────────────────────────────────────────────────

    def log_gesture(
        self,
        predicted_label: str,
        confidence: float,
        frames_collected: int,
        inference_time_ms: float,
        ground_truth: str = None,
        notes: str = "",
    ):
        """Log a single FSL gesture recognition event (Sign → TTS flow)."""
        self._ensure_started()

        is_correct = None
        if ground_truth is not None:
            is_correct = (
                predicted_label.strip().upper() == ground_truth.strip().upper()
            )

        row = {
            "event_type":        self.EVENT_GESTURE,
            "predicted_label":   predicted_label,
            "ground_truth":      ground_truth or "",
            "is_correct":        "" if is_correct is None else str(is_correct),
            "confidence":        f"{confidence:.4f}",
            "frames_collected":  frames_collected,
            "inference_time_ms": f"{inference_time_ms:.2f}",
            "notes":             notes,
        }
        self._write_row(row)

        self._gesture_events.append({
            "predicted":    predicted_label,
            "ground_truth": ground_truth,
            "is_correct":   is_correct,
            "confidence":   confidence,
            "frames":       frames_collected,
            "inference_ms": inference_time_ms,
        })

        correct_str = ""
        if is_correct is not None:
            correct_str = " ✅" if is_correct else " ❌"
        print(
            f"[GESTURE] {predicted_label}{correct_str} | "
            f"conf={confidence:.1%} | frames={frames_collected} | "
            f"latency={inference_time_ms:.1f}ms"
        )

    def log_tts(
        self,
        text: str,
        tts_latency_ms: float,
        dbfs: Optional[float] = None,
        notes: str = "",
    ):
        """
        Log a TTS output event (Sign → TTS flow).

        Args:
            text           : Text spoken by espeak
            tts_latency_ms : TTS call → thread dispatched (ms)
            dbfs           : Ambient dBFS. None = auto-read from shared_mic.
            notes          : Free-text notes
        """
        self._ensure_started()

        if dbfs is None:
            dbfs = get_mic_dbfs(self.shared_mic)

        dbfs_str = f"{dbfs:.2f}" if dbfs is not None else ""

        row = {
            "event_type":     self.EVENT_TTS,
            "tts_text":       text,
            "tts_latency_ms": f"{tts_latency_ms:.2f}",
            "tts_dbfs":       dbfs_str,
            "notes":          notes,
        }
        self._write_row(row)

        self._tts_events.append({
            "text":       text,
            "latency_ms": tts_latency_ms,
            "dbfs":       dbfs,
        })

        db_tag = f" | dB={dbfs:.1f} dBFS" if dbfs is not None else ""
        print(f"[TTS] \"{text}\" | latency={tts_latency_ms:.1f}ms{db_tag}")

    def log_stt(
        self,
        transcript: str,
        stt_latency_ms: float,
        reference: str = None,
        environment: str = "quiet",
        dbfs: Optional[float] = None,
        notes: str = "",
    ):
        """
        Log a Speech-to-Text result (STT flow).

        Args:
            transcript      : Whisper output text
            stt_latency_ms  : Transcription time (ms)
            reference       : Ground-truth text for WER (optional)
            environment     : "quiet" or "noisy"
            dbfs            : dBFS during recording. None = auto-read from mic.
            notes           : Free-text notes
        """
        self._ensure_started()

        wer_score = None
        if reference and WER_AVAILABLE:
            try:
                wer_score = compute_wer(
                    reference.lower().strip(),
                    transcript.lower().strip(),
                )
            except Exception:
                wer_score = None

        if dbfs is None:
            dbfs = get_mic_dbfs(self.shared_mic)

        dbfs_str = f"{dbfs:.2f}" if dbfs is not None else ""

        row = {
            "event_type":      self.EVENT_STT,
            "stt_transcript":  transcript,
            "stt_reference":   reference or "",
            "stt_wer":         f"{wer_score:.4f}" if wer_score is not None else "",
            "stt_latency_ms":  f"{stt_latency_ms:.2f}",
            "stt_environment": environment,
            "stt_dbfs":        dbfs_str,
            "notes":           notes,
        }
        self._write_row(row)

        self._stt_events.append({
            "transcript":  transcript,
            "reference":   reference,
            "wer":         wer_score,
            "latency_ms":  stt_latency_ms,
            "environment": environment,
            "dbfs":        dbfs,
        })

        wer_str = f" | WER={wer_score:.2%}" if wer_score is not None else ""
        db_tag  = f" | dB={dbfs:.1f} dBFS" if dbfs is not None else ""
        print(
            f"[STT] \"{transcript}\" | env={environment} | "
            f"latency={stt_latency_ms:.1f}ms{wer_str}{db_tag}"
        )

    def log_sos(
        self,
        response_time_ms: float,
        state: str = "idle",
        success: bool = True,
        notes: str = "",
    ):
        """Log an SOS button press event."""
        self._ensure_started()

        row = {
            "event_type":           self.EVENT_SOS,
            "sos_state":            state,
            "sos_response_time_ms": f"{response_time_ms:.2f}",
            "sos_success":          str(success),
            "notes":                notes,
        }
        self._write_row(row)

        self._sos_events.append({
            "response_ms": response_time_ms,
            "state":       state,
            "success":     success,
        })

        status = "✅ PASS" if success else "❌ FAIL"
        print(f"[SOS] {status} | state={state} | response={response_time_ms:.1f}ms")

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _write_row(self, data: dict):
        """Thread-safe CSV row write with auto-flush."""
        with self._lock:
            self._event_counter += 1
            now  = time.time()
            base = {
                "event_id":  self._event_counter,
                "timestamp": f"{now:.4f}",
                "datetime":  datetime.fromtimestamp(now).strftime(
                    "%Y-%m-%d %H:%M:%S.%f"
                )[:-3],
            }
            row = {field: "" for field in self.CSV_FIELDS}
            row.update(base)
            row.update(data)
            self._csv_writer.writerow(row)
            self._csv_file.flush()

    def _safe_avg(self, lst):
        return sum(lst) / len(lst) if lst else 0.0

    def _safe_median(self, lst):
        if not lst:
            return 0.0
        s = sorted(lst)
        n = len(s)
        return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2

    def _safe_p95(self, lst):
        if not lst:
            return 0.0
        s   = sorted(lst)
        idx = int(len(s) * 0.95)
        return s[min(idx, len(s) - 1)]

    def _build_summary(self, total_uptime: float) -> dict:

        # ── Gesture ──────────────────────────────────────────────────────
        with_truth  = [e for e in self._gesture_events if e["is_correct"] is not None]
        correct     = [e for e in with_truth if e["is_correct"]]
        accuracy    = len(correct) / len(with_truth) if with_truth else None
        inf_times   = [e["inference_ms"] for e in self._gesture_events]
        confidences = [e["confidence"]   for e in self._gesture_events]
        frames_list = [e["frames"]       for e in self._gesture_events]

        gesture_summary = {
            "total_predictions":    len(self._gesture_events),
            "evaluated_with_truth": len(with_truth),
            "correct":              len(correct),
            "accuracy_percent":     round(accuracy * 100, 2) if accuracy is not None else "N/A",
            "inference_latency_ms": {
                "mean":   round(self._safe_avg(inf_times), 2),
                "median": round(self._safe_median(inf_times), 2),
                "p95":    round(self._safe_p95(inf_times), 2),
                "min":    round(min(inf_times), 2) if inf_times else 0,
                "max":    round(max(inf_times), 2) if inf_times else 0,
            },
            "confidence": {
                "mean": round(self._safe_avg(confidences), 4),
                "min":  round(min(confidences), 4) if confidences else 0,
                "max":  round(max(confidences), 4) if confidences else 0,
            },
            "frames_per_gesture": {
                "mean": round(self._safe_avg(frames_list), 1),
                "min":  min(frames_list) if frames_list else 0,
                "max":  max(frames_list) if frames_list else 0,
            },
        }

        # ── TTS ──────────────────────────────────────────────────────────
        tts_lats = [e["latency_ms"] for e in self._tts_events]
        tts_dbs  = [e["dbfs"] for e in self._tts_events if e["dbfs"] is not None]

        tts_summary = {
            "total_tts_events": len(self._tts_events),
            "latency_ms": {
                "mean":   round(self._safe_avg(tts_lats), 2),
                "median": round(self._safe_median(tts_lats), 2),
                "p95":    round(self._safe_p95(tts_lats), 2),
            },
            "ambient_dbfs": {
                "mean": round(self._safe_avg(tts_dbs), 2) if tts_dbs else "N/A",
                "min":  round(min(tts_dbs), 2) if tts_dbs else "N/A",
                "max":  round(max(tts_dbs), 2) if tts_dbs else "N/A",
            },
        }

        # ── STT ──────────────────────────────────────────────────────────
        quiet_ev = [e for e in self._stt_events if e["environment"] == "quiet"]
        noisy_ev = [e for e in self._stt_events if e["environment"] == "noisy"]

        def _wer_stats(events):
            wers = [e["wer"]        for e in events if e["wer"]  is not None]
            lats = [e["latency_ms"] for e in events]
            dbs  = [e["dbfs"]       for e in events if e["dbfs"] is not None]
            return {
                "count":          len(events),
                "avg_wer":        round(self._safe_avg(wers), 4) if wers else "N/A",
                "avg_latency_ms": round(self._safe_avg(lats), 2) if lats else "N/A",
                "avg_dbfs":       round(self._safe_avg(dbs),  2) if dbs  else "N/A",
                "min_dbfs":       round(min(dbs), 2) if dbs else "N/A",
                "max_dbfs":       round(max(dbs), 2) if dbs else "N/A",
            }

        stt_summary = {
            "total_stt_events": len(self._stt_events),
            "quiet": _wer_stats(quiet_ev),
            "noisy": _wer_stats(noisy_ev),
        }

        # ── SOS ──────────────────────────────────────────────────────────
        sos_pass   = [e for e in self._sos_events if e["success"]]
        sos_idle   = [e for e in self._sos_events if e["state"] == "idle"]
        sos_active = [e for e in self._sos_events if e["state"] == "active"]
        sos_times  = [e["response_ms"] for e in self._sos_events]

        sos_summary = {
            "total_trials":         len(self._sos_events),
            "passed":               len(sos_pass),
            "success_rate_percent": (
                round(len(sos_pass) / len(self._sos_events) * 100, 2)
                if self._sos_events else "N/A"
            ),
            "response_time_ms": {
                "mean":   round(self._safe_avg(sos_times), 2),
                "median": round(self._safe_median(sos_times), 2),
                "p95":    round(self._safe_p95(sos_times), 2),
            },
            "idle_trials":   len(sos_idle),
            "active_trials": len(sos_active),
        }

        return {
            "session_info": {
                "csv_log":          str(self._csv_path),
                "summary_path":     str(self._summary_path),
                "total_uptime_sec": round(total_uptime, 2),
                "ended_at":         datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "mic_db_enabled":   self.shared_mic is not None,
                "total_events":     self._event_counter,
            },
            "gesture_recognition": gesture_summary,
            "text_to_speech":      tts_summary,
            "speech_to_text":      stt_summary,
            "sos_feature":         sos_summary,
        }

    def _print_summary(self, summary: dict):
        g = summary["gesture_recognition"]
        t = summary["text_to_speech"]
        s = summary["speech_to_text"]
        o = summary["sos_feature"]

        print(f"\n{'='*60}")
        print(f"📊 FINAL SESSION SUMMARY")
        print(f"{'='*60}")
        print(f"  Total uptime  : {summary['session_info']['total_uptime_sec']}s")
        print(f"  Total events  : {summary['session_info']['total_events']}")
        print(f"  Mic dB        : {'enabled' if summary['session_info']['mic_db_enabled'] else 'disabled'}")

        print(f"\n  🤟 Gesture Recognition  [Sign → TTS]")
        print(f"     Total predictions : {g['total_predictions']}")
        print(f"     Accuracy          : {g['accuracy_percent']}%")
        print(f"     Avg inference     : {g['inference_latency_ms']['mean']}ms")
        print(f"     P95 inference     : {g['inference_latency_ms']['p95']}ms")
        print(f"     Avg confidence    : {g['confidence']['mean']:.1%}")
        print(f"     Avg frames/gesture: {g['frames_per_gesture']['mean']}")

        print(f"\n  🔊 TTS")
        print(f"     Events      : {t['total_tts_events']}")
        print(f"     Avg latency : {t['latency_ms']['mean']}ms")
        if t["ambient_dbfs"]["mean"] != "N/A":
            print(f"     Avg ambient : {t['ambient_dbfs']['mean']} dBFS")

        print(f"\n  🎙️  STT  [Speech → Text]")
        print(f"     Events      : {s['total_stt_events']}")
        if s["quiet"]["count"] > 0:
            db_str = (
                f" | Avg dBFS={s['quiet']['avg_dbfs']}"
                if s["quiet"]["avg_dbfs"] != "N/A" else ""
            )
            print(f"     Quiet WER   : {s['quiet']['avg_wer']}{db_str}")
        if s["noisy"]["count"] > 0:
            db_str = (
                f" | Avg dBFS={s['noisy']['avg_dbfs']}"
                if s["noisy"]["avg_dbfs"] != "N/A" else ""
            )
            print(f"     Noisy WER   : {s['noisy']['avg_wer']}{db_str}")

        print(f"\n  🆘 SOS")
        print(f"     Trials        : {o['total_trials']}")
        print(f"     Success rate  : {o['success_rate_percent']}%")
        print(f"     Avg response  : {o['response_time_ms']['mean']}ms")

        print(f"\n  📁 Files saved:")
        print(f"     {self._csv_path}")
        print(f"     {self._summary_path}")
        print(f"{'='*60}\n")


# ─────────────────────────────────────────────────────────────────────────────
# Global singleton - import this in ALL server files
# ─────────────────────────────────────────────────────────────────────────────

# SharedMic is wired in by main.py after it imports shared_mic itself.
# We create the singleton without a mic here; main.py assigns it via
# global_logger.shared_mic = shared_mic  before calling global_logger.start()

global_logger = SessionLogger(log_dir="logs", shared_mic=None)