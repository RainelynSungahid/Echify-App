import { Audio } from 'expo-av';
import React, { useState } from 'react';
import { Alert, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import AudioWave from '../components/AudioWave';
import CameraComponent from '../components/CameraView';

export default function MainScreen() {
  const [activeTab, setActiveTab] = useState<'sign' | 'speech'>('sign');
  const [isRecording, setIsRecording] = useState(false);

  const startSpeechToText = async () => {
    const { granted } = await Audio.requestPermissionsAsync();
    if (!granted) {
      Alert.alert("Permission Required", "Please enable microphone access in settings to use Speech to Text.");
      return;
    }
    setIsRecording(true);
  };

  return (
    <View style={styles.container}>      
      {/* Toggle Buttons */}
      <View style={styles.tabContainer}>
        <TouchableOpacity 
          style={[styles.tab, activeTab === 'sign' && styles.activeTab]} 
          onPress={() => setActiveTab('sign')}
        >
          <Text style={[styles.tabText, activeTab === 'sign' && styles.activeTabText]}>Sign to Speech</Text>
        </TouchableOpacity>
        
        <TouchableOpacity 
          style={[styles.tab, activeTab === 'speech' && styles.activeTab]} 
          onPress={() => {
            setActiveTab('speech');
            startSpeechToText();
          }}
        >
          <Text style={[styles.tabText, activeTab === 'speech' && styles.activeTabText]}>Speech to Text</Text>
        </TouchableOpacity>
      </View>

      {/* Main Content Area */}
      <View style={styles.content}>
        {activeTab === 'sign' ? (
          <View style={styles.stackedContainer}>
            <View style={styles.cameraBox}>
              <CameraComponent />
            </View>
            <View style={styles.fullTextBox}><Text>Annyeonghaseyo</Text></View>
          </View>
        ) : (
          <View>
            <AudioWave isRecording={isRecording} />
            <View style={styles.fullTextBox}><Text>Hello</Text></View>
          </View>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, paddingTop: 0, paddingHorizontal: 20, paddingBottom: 20, backgroundColor: '#fff'},
  header: { fontSize: 22, fontWeight: 'bold', color: '#6d3d1e', marginBottom: 20 },
  tabContainer: { flexDirection: 'row', backgroundColor: '#e5e0db', borderRadius: 25, padding: 5 },
  tab: { flex: 1, paddingVertical: 12, alignItems: 'center', borderRadius: 20 },
  activeTab: { backgroundColor: '#6d3d1e' },
  tabText: { color: '#777', fontWeight: '600' },
  activeTabText: { color: '#fff' },
  row: { flexDirection: 'row', gap: 15 },
  box: { flex: 1, height: 250, borderRadius: 20 },
  content: { 
    marginTop: 20, 
    flex: 1 
  },
  stackedContainer: { 
    flexDirection: 'column',
    gap: 15, 
    height: '100%' 
  },
  cameraBox: { 
    height: 300,
    borderRadius: 20, 
    overflow: 'hidden' 
  },
  textBox: { 
    flex: 1,
    backgroundColor: '#e5e0db', 
    borderRadius: 20, 
    padding: 20,
    minHeight: 150 
  },
  placeholderText: {
    fontSize: 18,
    color: '#333'
  },
  fullTextBox: { backgroundColor: '#e5e0db', height: 200, borderRadius: 20, padding: 20}
});