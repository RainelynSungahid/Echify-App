import { Ionicons } from "@expo/vector-icons";
import React, { useEffect, useRef, useState } from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";

export default function CameraComponent() {
  const videoRef = useRef<any>(null);
  const [isCameraActive, setIsCameraActive] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startCamera = async () => {
    try {
      setError(null);

      // STEP 1: Request a generic stream first.
      // This "unlocks" the hardware and populates the device labels.
      const initialStream = await navigator.mediaDevices.getUserMedia({
        video: true,
        audio: false,
      });

      // STEP 2: Enumerate devices now that labels are unlocked.
      const devices = await navigator.mediaDevices.enumerateDevices();
      const videoDevices = devices.filter((d) => d.kind === "videoinput");

      // STEP 3: Find your bridge or fallback to the first one.
      const selectedDevice =
        videoDevices.find((d) => d.label.toLowerCase().includes("echify")) ||
        videoDevices[0];

      // STEP 4: Start the final stream with your thesis dimensions.
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          deviceId: selectedDevice
            ? { exact: selectedDevice.deviceId }
            : undefined,
          width: 640,
          height: 480,
        },
      });

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        setIsCameraActive(true);
      }

      // Clean up the initial "unlock" stream
      initialStream.getTracks().forEach((track) => track.stop());
    } catch (err: any) {
      console.error(err);
      setError(`Hardware error: ${err.name}. Check your GStreamer Terminal.`);
    }
  };

  const stopCamera = () => {
    if (videoRef.current && videoRef.current.srcObject) {
      const tracks = videoRef.current.srcObject.getTracks();
      tracks.forEach((track: any) => track.stop());
      videoRef.current.srcObject = null;
      setIsCameraActive(false);
    }
  };

  // Cleanup camera when component unmounts
  useEffect(() => {
    return () => stopCamera();
  }, []);

  return (
    <View style={styles.container}>
      {isCameraActive ? (
        <View style={styles.cameraWrapper}>
          <video
            ref={videoRef}
            autoPlay
            playsInline
            style={styles.videoElement}
          />
          <TouchableOpacity style={styles.closeButton} onPress={stopCamera}>
            <Ionicons name="close-circle" size={32} color="white" />
          </TouchableOpacity>
        </View>
      ) : (
        <TouchableOpacity style={styles.placeholder} onPress={startCamera}>
          <Ionicons name="camera-outline" size={48} color="#777" />
          <Text style={styles.text}>
            {error ? error : "Tap to turn on camera"}
          </Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    borderRadius: 20,
    overflow: "hidden",
    backgroundColor: "#333",
  },
  cameraWrapper: { flex: 1, position: "relative" },
  // Native video element styling
  videoElement: {
    width: "100%",
    height: "100%",
    objectFit: "cover",
  },
  placeholder: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 20,
  },
  text: {
    marginTop: 10,
    color: "#bbb",
    fontSize: 14,
    textAlign: "center",
  },
  closeButton: {
    position: "absolute",
    top: 10,
    right: 10,
    backgroundColor: "rgba(0,0,0,0.5)",
    borderRadius: 20,
  },
});
