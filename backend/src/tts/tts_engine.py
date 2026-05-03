import threading
import sys
import subprocess
from pathlib import Path
from TTS.api import TTS
from pydub import AudioSegment

# ── Load Coqui model once ─────────────────────────────────────────────
tts = TTS(
    model_name="tts_models/en/ljspeech/tacotron2-DDC",
    progress_bar=False
)

# ── Paths ─────────────────────────────────────────────────────────────
OUTPUT_PATH = Path("coqui_output.wav")
SLOW_OUTPUT_PATH = Path("coqui_output_slow.wav")

# ── Speed control ─────────────────────────────────────────────────────
SPEECH_SPEED = 0.85  # adjust (0.8–0.9 recommended)


# ── Helper: slow down audio ────────────────────────────────────────────
def slow_down_wav(input_path, output_path, speed=0.85):
    audio = AudioSegment.from_wav(input_path)

    slowed = audio._spawn(
        audio.raw_data,
        overrides={
            "frame_rate": int(audio.frame_rate * speed)
        }
    ).set_frame_rate(audio.frame_rate)

    slowed.export(output_path, format="wav")


# ── Speak function (Coqui) ─────────────────────────────────────────────
def speak(text: str):
    if not text or not text.strip():
        return

    def _run():
        try:
            print(f"🔊 Speaking (Coqui): {text}")

            # Generate speech
            tts.tts_to_file(
                text=text,
                file_path=str(OUTPUT_PATH)
            )

            # Slow it down
            slow_down_wav(OUTPUT_PATH, SLOW_OUTPUT_PATH, SPEECH_SPEED)

            # Play audio
            if sys.platform == "win32":
                subprocess.run(
                    [
                        "powershell",
                        "-Command",
                        f'(New-Object Media.SoundPlayer "{SLOW_OUTPUT_PATH.resolve()}").PlaySync()'
                    ],
                    check=False
                )
            else:
                subprocess.run(["aplay", str(SLOW_OUTPUT_PATH)], check=False)

        except Exception as e:
            print(f"❌ TTS error: {e}")

    threading.Thread(target=_run, daemon=True).start()


# ── Emergency Audio (UNCHANGED) ────────────────────────────────────────
class EmergencyAudio:
    def __init__(self, wav_path="/home/sms/Echify-App/assets/help_me.wav"):
        self.wav_path = wav_path

    def play_help_instant(self):
        def _run():
            try:
                print(f"🔊 Playing emergency audio: {self.wav_path}")

                if sys.platform == "win32":
                    subprocess.run(
                        [
                            "powershell",
                            "-Command",
                            f'(New-Object Media.SoundPlayer "{self.wav_path}").PlaySync()'
                        ],
                        check=False
                    )
                else:
                    subprocess.run(["aplay", self.wav_path], check=False)

            except Exception as e:
                print(f"❌ Emergency audio error: {e}")

        threading.Thread(target=_run, daemon=True).start()