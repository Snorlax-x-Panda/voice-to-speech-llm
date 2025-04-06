"use strict";

const serverUrl = "http://127.0.0.1:8000";

let audioContext;
let processor;
let input;
let stream;
let pcmChunks = [];

// Convert Float32 audio to 16-bit PCM
function floatTo16BitPCM(input) {
    const buffer = new ArrayBuffer(input.length * 2);
    const view = new DataView(buffer);
    for (let i = 0; i < input.length; i++) {
        let s = Math.max(-1, Math.min(1, input[i]));
        view.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
    }
    return new Uint8Array(buffer);
}

// Safe base64 encoder for large buffers
function base64ArrayBuffer(arrayBuffer) {
    const bytes = new Uint8Array(arrayBuffer);
    let binary = '';
    for (let i = 0; i < bytes.length; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
}

async function startRecording() {
    pcmChunks = [];
    stream = await navigator.mediaDevices.getUserMedia({audio: true});
    audioContext = new (window.AudioContext || window.webkitAudioContext)();

    const source = audioContext.createMediaStreamSource(stream);

    processor = audioContext.createScriptProcessor(4096, 1, 1);
    processor.onaudioprocess = (e) => {
        const input = e.inputBuffer.getChannelData(0);
        const pcm = floatTo16BitPCM(input);
        pcmChunks.push(pcm);
    };

    source.connect(processor);
    processor.connect(audioContext.destination);

    document.getElementById("startBtn").disabled = true;
    document.getElementById("stopBtn").disabled = false;
}

async function stopRecording() {
    document.getElementById("stopBtn").disabled = true;

    processor.disconnect();

    if (audioContext && audioContext.state !== 'closed') {
        await audioContext.close();
    }

    stream.getTracks().forEach(track => track.stop());

    const fullPCM = new Blob(pcmChunks, {type: "application/octet-stream"});
    const arrayBuffer = await fullPCM.arrayBuffer();
    const base64 = base64ArrayBuffer(arrayBuffer);

    // Send to backend
    const response = await fetch("http://127.0.0.1:8000/transcribe", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({audio_blob: base64})
    });

    const result = await response.json();
    document.getElementById("transcript").textContent = result.transcript || result.error;
    if (result.transcript) {
        fetchGeminiResponse(result.transcript);
    }

    document.getElementById("startBtn").disabled = false;
}

document.getElementById("startBtn").addEventListener("click", startRecording);
document.getElementById("stopBtn").addEventListener("click", stopRecording);

async function fetchGeminiResponse(text) {
    const res = await fetch("http://127.0.0.1:8000/gemini", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ message: text })
    });
    const result = await res.json();
    const reply = result.response || result.error || "No Response.";
    document.getElementById("gemini").textContent = reply

    // POST to Polly
    const voiceRes = await fetch("http://127.0.0.1:8000/speak", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ text: reply })
      });
  

    const voiceResult = await voiceRes.json();

    if (voiceResult.audio_base64) {
        const audio = document.getElementById("audioPlayer");
        audio.src = "data:audio/mp3;base64," + voiceResult.audio_base64;
        audio.play();
    }
    else {
        console.error("Polly error:", voiceResult.error);
    }
}

async function sendApiKey() {
    const key = document.getElementById("apiKeyInput").value;
    const res = await fetch("http://127.0.0.1:8000/handshake", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({api_key: key})
    });
    const result = await res.text();
    alert("Handshake result: " + result);
}