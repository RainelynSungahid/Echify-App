import React, { useEffect, useMemo, useRef, useState } from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";
import { sendFrame } from "../services/socket";

interface CameraViewProps {
  onPrediction?: (prediction: string) => void;
}

export default function CameraView({ onPrediction }: CameraViewProps) {
  const [previewLoaded, setPreviewLoaded] = useState(false);
  const [cameraError, setCameraError] = useState("");

  const imgRef = useRef<HTMLImageElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const frameTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const sentPreviewCountRef = useRef(0);

  const previewUrl = useMemo(() => {
    const host =
      typeof window !== "undefined" ? window.location.hostname : "localhost";
    return `http://${host}:8000/preview`;
  }, []);

useEffect(() => {
  const retryInterval = setInterval(() => {
    if (!previewLoaded && imgRef.current) {
      console.log("🔁 Retrying camera preview...");
      imgRef.current.src = previewUrl + "?t=" + new Date().getTime();
    }
  }, 3000);

  return () => clearInterval(retryInterval);
}, [previewLoaded, previewUrl]);
  useEffect(() => {
    if (!previewLoaded) return;

    const sendCurrentFrame = () => {
  const img = imgRef.current;
  const canvas = canvasRef.current;

  if (!img || !canvas) return;
  if (!img.naturalWidth || !img.naturalHeight) return;

  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const targetWidth = 640;
  const targetHeight = 480;

  canvas.width = targetWidth;
  canvas.height = targetHeight;

  try {
    // ✅ CRITICAL: disable smoothing (keeps landmark sharp)
    ctx.imageSmoothingEnabled = false;

    ctx.drawImage(img, 0, 0, targetWidth, targetHeight);

    // ✅ HIGH QUALITY JPEG
    const frameBase64 = canvas.toDataURL("image/jpeg", 0.9);

    sentPreviewCountRef.current += 1;

    const ok = sendFrame(frameBase64);

    if (
      sentPreviewCountRef.current <= 5 ||
      sentPreviewCountRef.current % 30 === 0
    ) {
      console.log(
        `🎥 Frame #${sentPreviewCountRef.current} sent | size=${frameBase64.length} | ok=${ok}`
      );
    }

  } catch (e) {
    console.log("❌ Failed to capture/send frame:", e);
  }
};

    frameTimerRef.current = setInterval(sendCurrentFrame, 33);

    return () => {
      if (frameTimerRef.current) {
        clearInterval(frameTimerRef.current);
        frameTimerRef.current = null;
      }
    };
  }, [previewLoaded]);

  return (
    <View style={styles.container}>
      {!previewLoaded && !cameraError && (
        <View style={styles.loadingOverlay}>
          <ActivityIndicator size="large" color="#4CAF50" />
          <Text style={styles.loadingText}>Loading preview...</Text>
        </View>
      )}

      {cameraError ? (
        <View style={styles.loadingContainer}>
          <Text style={styles.loadingText}>Preview unavailable</Text>
          <Text style={styles.loadingSubtext}>
            Check backend stream on port 8000.
          </Text>
        </View>
      ) : (
        <>
          <img
            ref={imgRef}
            src={previewUrl}
            crossOrigin="anonymous"
            alt="Camera Preview"
            style={styles.previewImage as any}
            onLoad={() => {
              setPreviewLoaded(true);
              setCameraError("");
            }}
            onError={() => {
            console.log("❌ Preview failed, retrying...");
            setPreviewLoaded(false);
            setCameraError("");

            setTimeout(() => {
              if (imgRef.current) {
                imgRef.current.src = previewUrl + "?t=" + new Date().getTime();
              }
            }, 2000);
          }}
          />
          <canvas ref={canvasRef} style={{ display: "none" }} />
        </>
      )}

      <View style={styles.statusIndicator}>
        <View
          style={[styles.statusDot, previewLoaded && styles.statusDotActive]}
        />
        <Text style={styles.statusText}>
          {cameraError ? "Offline" : previewLoaded ? "Live" : "Loading"}
        </Text>
      </View>
    </View>
  );
}

const styles: any = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#000",
    position: "relative",
  },
  previewImage: {
    width: "100%",
    height: "100%",
    objectFit: "cover",
    display: "block",
  },
  loadingOverlay: {
    position: "absolute",
    inset: 0,
    zIndex: 2,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "#111",
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
    zIndex: 3,
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
