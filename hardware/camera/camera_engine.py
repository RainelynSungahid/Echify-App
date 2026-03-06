import subprocess
import os
import threading
import time

def start_gstreamer():
    print("Step 1: Starting GStreamer Bridge...")
    command = [
        "env", "GST_PLUGIN_FEATURE_RANK=v4l2codecs:NONE",
        "gst-launch-1.0", "libcamerasrc", "!",
        "video/x-raw,width=640,height=480,format=YUY2", "!",
        "videoconvert", "!",
        "v4l2sink", "device=/dev/video10"
    ]
    subprocess.run(command)

def start_web_server():
    print("Step 2: Starting Web Server on Port 3000...")
    # Change directory to where your 'dist' folder is
    os.chdir("/home/sms/Echify-App/dist")
    subprocess.run(["python3", "-m", "http.server", "3000"])

def launch_app():
    print("Step 3: Launching App in Chromium...")
    # These are the flags you wanted to 'put inside the code'
    chrome_cmd = [
        "chromium",
        "--app=http://localhost:3000",
        "--use-fake-ui-for-media-stream",
        "--no-sandbox",
        "--test-type" # Helps bypass some warnings
    ]
    subprocess.run(chrome_cmd)

if __name__ == "__main__":
    # Initialize hardware
    os.system("sudo modprobe v4l2loopback video_nr=10 card_label='Echify-Camera' exclusive_caps=1")
    os.system("sudo chmod 777 /dev/video10")

    # Start Bridge and Server in the background
    threading.Thread(target=start_gstreamer, daemon=True).start()
    threading.Thread(target=start_web_server, daemon=True).start()

    # Wait 2 seconds for server to boot, then launch the UI
    time.sleep(2)
    launch_app()