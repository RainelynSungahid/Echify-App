import React, { useEffect, useRef, useState } from "react";
import { StyleSheet, Text, View, ActivityIndicator, Platform } from "react-native";
import { sendFrame } from "../services/socket";

interface CameraViewProps {
  onPrediction?: (prediction: string) => void;
}

export default function CameraView({ onPrediction }: CameraViewProps) {
  const videoRef = useRef<any>(null);
  const canvasRef = useRef<any>(null);

  const [isInitialized, setIsInitialized] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let stream: MediaStream | null = null;
    let interval: ReturnType<typeof setInterval> | null = null;
    let isMounted = true;

    const startCamera = async () => {
      if (Platform.OS !== "web") {
        setErrorMessage("This camera setup is intended for the Raspberry Pi web app running in Chromium.");
        setIsInitialized(true);
        return;
      }

      try {
        console.log("📷 Requesting browser camera access...");

        stream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: 640,
            height: 480,
            facingMode: "user",
          },
          audio: false,
        });

        if (!isMounted) return;

        if (videoRef.current) {
          videoRef.current.srcObject = stream;

          await new Promise<void>((resolve) => {
            videoRef.current.onloadedmetadata = () => {
              videoRef.current
                .play()
                .then(() => resolve())
                .catch((err: any) => {
                  console.log("Video play error:", err);
                  resolve();
                });
            };
          });
        }

        console.log("✅ Camera stream started");
        setIsStreaming(true);
        setIsInitialized(true);

        interval = setInterval(() => {
          captureAndSendFrame();
        }, 300);
      } catch (error: any) {
        console.error("❌ Camera access error:", error);
        setErrorMessage(
          error?.message || "Failed to access Raspberry Pi camera from Chromium."
        );
        setIsInitialized(true);
      }
    };

    const captureAndSendFrame = () => {
      try {
        if (!videoRef.current || !canvasRef.current) return;

        const video = videoRef.current;
        const canvas = canvasRef.current;
        const ctx = canvas.getContext("2d");

        if (!ctx) return;
        if (video.videoWidth === 0 || video.videoHeight === 0) return;

        canvas.width = 640;
        canvas.height = 480;

        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

        const base64 = canvas.toDataURL("image/jpeg", 0.7).split(",")[1];

        if (base64) {
          sendFrame(base64);
        }
      } catch (err) {
        console.log("📸 Frame capture error:", err);
      }
    };

    startCamera();

    return () => {
      isMounted = false;

      if (interval) {
        clearInterval(interval);
      }

      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }

      setIsStreaming(false);
    };
  }, []);

  if (!isInitialized) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#4CAF50" />
        <Text style={styles.loadingText}>Initializing Raspberry Pi camera...</Text>
        <Text style={styles.loadingSubtext}>Opening browser camera stream...</Text>
      </View>
    );
  }

  if (errorMessage) {
    return (
      <View style={styles.loadingContainer}>
        <Text style={styles.errorIcon}>📷</Text>
        <Text style={styles.errorTitle}>Camera Error</Text>
        <Text style={styles.errorText}>{errorMessage}</Text>
        <Text style={styles.errorSubtext}>
          Make sure camera_engine.py is running and Chromium has camera access.
        </Text>
      </View>
    );
  }

  if (Platform.OS !== "web") {
    return (
      <View style={styles.loadingContainer}>
        <Text style={styles.errorIcon}>⚠️</Text>
        <Text style={styles.errorTitle}>Unsupported Platform</Text>
        <Text style={styles.errorText}>
          This version is for the Raspberry Pi Chromium web build only.
        </Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        style={webStyles.video as any}
      />

      <canvas
        ref={canvasRef}
        style={webStyles.hiddenCanvas as any}
      />

      <View style={styles.statusIndicator}>
        <View style={[styles.statusDot, isStreaming && styles.statusDotActive]} />
        <Text style={styles.statusText}>
          {isStreaming ? "Capturing..." : "Idle"}
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#000",
    position: "relative",
    overflow: "hidden",
    borderRadius: 20,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "#f5f5f5",
    padding: 20,
  },
  loadingText: {
    marginTop: 16,
    fontSize: 18,
    color: "#333",
    fontWeight: "600",
    textAlign: "center",
  },
  loadingSubtext: {
    marginTop: 8,
    fontSize: 14,
    color: "#666",
    textAlign: "center",
  },
  errorIcon: {
    fontSize: 64,
    marginBottom: 16,
  },
  errorTitle: {
    fontSize: 22,
    fontWeight: "bold",
    color: "#333",
    marginBottom: 12,
    textAlign: "center",
  },
  errorText: {
    fontSize: 15,
    color: "#666",
    textAlign: "center",
    marginTop: 8,
    paddingHorizontal: 20,
    lineHeight: 22,
  },
  errorSubtext: {
    fontSize: 13,
    color: "#999",
    textAlign: "center",
    marginTop: 8,
    paddingHorizontal: 20,
    lineHeight: 20,
    fontStyle: "italic",
  },
  statusIndicator: {
    position: "absolute",
    top: 10,
    right: 10,
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "rgba(0,0,0,0.6)",
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
    zIndex: 10,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: "#ff4444",
    marginRight: 6,
  },
  statusDotActive: {
    backgroundColor: "#44ff44",
  },
  statusText: {
    color: "#fff",
    fontSize: 12,
    fontWeight: "600",
  },
});

const webStyles = {
  video: {
    width: "100%",
    height: "100%",
    objectFit: "cover",
    backgroundColor: "#000",
  },
  hiddenCanvas: {
    display: "none",
  },
};