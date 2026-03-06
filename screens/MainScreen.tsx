import { Audio } from "expo-av";
import * as Speech from "expo-speech";
import React, { useEffect, useRef, useState } from "react";
import {
  Alert,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

import { closeSocket, connectSocket } from "../services/socket";
import { sendAudioForSTT } from "../services/stt";

import AudioWave from "../components/AudioWave";
import CameraComponent from "../components/CameraView";

export default function MainScreen() {
  const [activeTab, setActiveTab] = useState<"sign" | "speech">("sign");

  // Sign-to-speech state
  const [typedText, setTypedText] = useState("");
  const [finalWord, setFinalWord] = useState("");
  const newWordStartedRef = useRef(false);

  // Speech-to-text state
  const [isRecording, setIsRecording] = useState(false);
  const [sttText, setSttText] = useState("Listening...");

  const recordingRef = useRef<Audio.Recording | null>(null);
  const silenceTimerRef = useRef(0);
  const speechStartedRef = useRef(false);
  const speechDurationRef = useRef(0);

  const isStoppingRef = useRef(false);
  const isUploadingRef = useRef(false);

  // Keep latest text reference
  const typedRef = useRef<string>("");
  useEffect(() => {
    typedRef.current = typedText;
  }, [typedText]);

  // Connect websocket for sign-to-speech
  useEffect(() => {
    if (activeTab === "sign") {
      connectSocket(async (data: any) => {
        const committed = data?.committed_letter;

        if (typeof committed === "string" && committed.length > 0) {
          if (!newWordStartedRef.current) {
            setFinalWord("");
            setTypedText("");
            newWordStartedRef.current = true;
          }

          setTypedText((prev) => (prev || "") + committed);
          return;
        }

        const q = data?.queue_text;
        if (typeof q === "string" && q.length > 0) {
          setTypedText(q);
        }

        if (data?.should_speak && Array.isArray(data?.letters_to_speak)) {
          const word = data.letters_to_speak.join("");

          if (word.length > 0) {
            try {
              await Speech.stop();
              Speech.speak(word, {
                language: "en-US",
                rate: 0.9,
                pitch: 1.0,
              });
              console.log("🔊 Speaking word:", word);
            } catch (e) {
              console.log("❌ Speech error:", e);
            }

            setFinalWord(word);
          }

          setTypedText("");
          newWordStartedRef.current = false;
        }
      });
    } else {
      closeSocket();
    }

    return () => closeSocket();
  }, [activeTab]);

  // Start/stop STT depending on tab
  useEffect(() => {
    if (activeTab === "speech") {
      startSpeechLoop();
    } else {
      stopRecordingAndSend(false);
      setIsRecording(false);
    }

    return () => {
      stopRecordingAndSend(false);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab]);

  const startSpeechLoop = async () => {
    const { granted } = await Audio.requestPermissionsAsync();

    if (!granted) {
      Alert.alert(
        "Permission Required",
        "Please enable microphone access in settings to use Speech to Text."
      );
      setActiveTab("sign");
      return;
    }

    await Audio.setAudioModeAsync({
      allowsRecordingIOS: true,
      playsInSilentModeIOS: true,
    });

    await startRecording();
  };

  const startRecording = async () => {
    try {
      setSttText((prev) =>
        prev && prev !== "Listening..." && prev !== "Say something..."
          ? prev
          : "Listening..."
      );

      setIsRecording(true);

      speechStartedRef.current = false;
      silenceTimerRef.current = 0;
      speechDurationRef.current = 0;

      const rec = new Audio.Recording();
      recordingRef.current = rec;

      await rec.prepareToRecordAsync(Audio.RecordingOptionsPresets.HIGH_QUALITY);

      rec.setProgressUpdateInterval(100);

      const silenceDbThreshold = -35;
      const silenceSecondsToStop = 1.0;
      const minSpeechSeconds = 0.3;
      const frameSec = 0.1;

      rec.setOnRecordingStatusUpdate((status) => {
        if (!status.isRecording) return;

        const db = (status as any).metering;
        if (typeof db !== "number") return;

        if (db > silenceDbThreshold) {
          speechStartedRef.current = true;
          silenceTimerRef.current = 0;
          speechDurationRef.current += frameSec;
        } else {
          if (speechStartedRef.current) {
            silenceTimerRef.current += frameSec;
          }
        }

        if (
          speechStartedRef.current &&
          speechDurationRef.current >= minSpeechSeconds &&
          silenceTimerRef.current >= silenceSecondsToStop
        ) {
          if (isStoppingRef.current || isUploadingRef.current) return;
          stopRecordingAndSend(true);
        }
      });

      await rec.startAsync();
    } catch (e) {
      console.log("❌ startRecording error:", e);
      setIsRecording(false);
      setSttText("Mic error.");
    }
  };

  const stopRecordingAndSend = async (restartAfter: boolean) => {
    if (isStoppingRef.current) return;
    isStoppingRef.current = true;

    const rec = recordingRef.current;
    if (!rec) {
      isStoppingRef.current = false;
      return;
    }

    try {
      recordingRef.current = null;
      setIsRecording(false);

      await rec.stopAndUnloadAsync();
      const uri = rec.getURI();

      if (!uri) {
        setSttText((prev) => prev || "No audio captured.");
        return;
      }

      if (!restartAfter) return;

      if (isUploadingRef.current) return;
      isUploadingRef.current = true;

      setSttText((prev) =>
        prev && prev !== "Say something..." ? prev : "Transcribing..."
      );

      const text = await sendAudioForSTT(uri);

      setSttText((prev) => {
        const t = (text || "").trim();
        if (!t) return prev || "…";
        if (
          !prev ||
          prev === "Say something..." ||
          prev === "Listening..." ||
          prev === "Transcribing..."
        ) {
          return t;
        }
        return t || "…";
      });
    } catch (e) {
      console.log("❌ stop/send error:", e);
      setSttText((prev) => (prev ? prev : "STT error."));
    } finally {
      isUploadingRef.current = false;
      isStoppingRef.current = false;

      if (restartAfter && activeTab === "speech") {
        await startRecording();
      }
    }
  };

  const signBoxText =
    typedText.length > 0
      ? typedText
      : finalWord.length > 0
      ? finalWord
      : "Waiting for sign...";

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.scrollContent}
    >
      <View style={styles.tabContainer}>
        <TouchableOpacity
          style={[styles.tab, activeTab === "sign" && styles.activeTab]}
          onPress={() => setActiveTab("sign")}
        >
          <Text
            style={[
              styles.tabText,
              activeTab === "sign" && styles.activeTabText,
            ]}
          >
            Sign to Speech
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.tab, activeTab === "speech" && styles.activeTab]}
          onPress={() => setActiveTab("speech")}
        >
          <Text
            style={[
              styles.tabText,
              activeTab === "speech" && styles.activeTabText,
            ]}
          >
            Speech to Text
          </Text>
        </TouchableOpacity>
      </View>

      {activeTab === "sign" ? (
        <View style={styles.content}>
          <View style={styles.stackedContainer}>
            <View style={styles.cameraBox}>
              <CameraComponent />
            </View>

            <View style={styles.fullTextBox}>
              <Text style={styles.resultLabel}>FSL TRANSLATION:</Text>
              <Text style={styles.placeholderText}>{signBoxText}</Text>
            </View>
          </View>
        </View>
      ) : (
        <View style={styles.content1}>
          <View style={styles.stackedContainer2}>
            <View style={styles.audioWave}>
              <AudioWave isRecording={isRecording} />
            </View>

            <View style={styles.fullTextBoxSpeech}>
              <Text style={styles.resultLabel}>SPEECH RESULT:</Text>
              <Text style={styles.placeholderText}>{sttText}</Text>
            </View>
          </View>
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingHorizontal: 20,
    paddingBottom: 20,
    backgroundColor: "#fff",
  },
  scrollContent: {
    paddingHorizontal: 20,
    paddingBottom: 40,
  },
  tabContainer: {
    flexDirection: "row",
    backgroundColor: "#e5e0db",
    borderRadius: 25,
    padding: 0,
  },
  tab: {
    flex: 1,
    paddingVertical: 12,
    alignItems: "center",
    borderRadius: 20,
  },
  activeTab: {
    backgroundColor: "#6d3d1e",
  },
  tabText: {
    color: "#777",
    fontWeight: "600",
  },
  activeTabText: {
    color: "#fff",
  },
  content: {
    marginTop: 20,
    flex: 1,
  },
  content1: {
    flex: 1,
    marginTop: 20,
  },
  stackedContainer: {
    flexDirection: "row",
    gap: 15,
    height: 500,
    width: "100%",
  },
  cameraBox: {
    flex: 2,
    height: "100%",
    borderRadius: 20,
    backgroundColor: "#000",
    overflow: "hidden",
  },
  fullTextBox: {
    flex: 1,
    backgroundColor: "#f4f1ee",
    height: "100%",
    borderRadius: 20,
    padding: 20,
    borderWidth: 1,
    borderColor: "#e5e0db",
    justifyContent: "flex-start",
  },
  stackedContainer2: {
    flexDirection: "column",
    gap: 15,
    height: 500,
    width: "100%",
  },
  audioWave: {
    flex: 0.2,
    overflow: "hidden",
  },
  fullTextBoxSpeech: {
    flex: 1,
    backgroundColor: "#f4f1ee",
    borderRadius: 20,
    padding: 20,
    borderWidth: 1,
    borderColor: "#e5e0db",
    justifyContent: "flex-start",
  },
  resultLabel: {
    fontSize: 12,
    color: "#6d3d1e",
    fontWeight: "bold",
    marginBottom: 8,
    textTransform: "uppercase",
  },
  placeholderText: {
    fontSize: 24,
    color: "#333",
    fontWeight: "500",
  },
});