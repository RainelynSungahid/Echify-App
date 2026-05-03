import threading
import sys

def speak(text: str):
    if not text or not text.strip():
        return
    

    def _run():
        try:
            print(f"Speaking: {text}")
            if sys.platform == "win32":
                import subprocess
                subprocess.run(
                    ["powershell", "-Command",
                    f'Add-Type -AssemblyName System.Speech; '
                    f'$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; '
                    f'$s.Rate = -2; '   # ← was 0, now slower (-10 is slowest)
                    f'$s.Volume = 100; '       # Volume: 0–100
                    f'$s.SelectVoiceByHints([System.Speech.Synthesis.VoiceGender]::Female); '  # Female voice (sounds clearer)
                    f'$s.Speak("{text}")'],
                    check=False,
                    capture_output=True
                )
            else:
                # Pi/Linux: use espeak
                subprocess.run([
                    "espeak",
                    "-v", "en-us",
                    "-s", "100",     # ← was 130, now slower
                    "-p", "50",
                    "-a", "200",
                    text
                ], check=False)
        except Exception as e:
            print(f"TTS error: {e}")

    threading.Thread(target=_run, daemon=True).start()


class EmergencyAudio:
    def __init__(self, wav_path="/home/sms/Echify-App/assets/help_me.wav"):
        self.wav_path = wav_path

    def play_help_instant(self):
        def _run():
            try:
                print(f"Playing emergency audio: {self.wav_path}")
                if sys.platform == "win32":
                    import subprocess
                    subprocess.run(
                        ["powershell", "-Command",
                         f'(New-Object Media.SoundPlayer "{self.wav_path}").PlaySync()'],
                        check=False,
                        capture_output=True
                    )
                else:
                    import subprocess
                    subprocess.run(["aplay", self.wav_path], check=False)
            except Exception as e:
                print(f"Emergency audio error: {e}")

        threading.Thread(target=_run, daemon=True).start()