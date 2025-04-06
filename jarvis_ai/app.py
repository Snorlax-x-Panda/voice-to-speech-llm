from chalice import Chalice
import boto3
import json
import base64
import google.generativeai as genai
from chalicelib import transcribe_service
from chalicelib import polly_service
import subprocess
import tempfile
import os

key=None
app = Chalice(app_name='jarvis_ai')

def downsample_pcm(input_path, output_path):
    cmd = [
        "ffmpeg", "-y",
        "-f", "s16le",
        "-ar", "48000",             # Pass Microphone Sample Rate
        "-ac", "1",
        "-i", input_path,
        "-ar", "16000",
        "-ac", "1",
        "-f", "s16le",
        output_path
    ]
    subprocess.run(cmd, check=True)

@app.route('/')
def index():
    return {'hello': 'world'}

@app.route('/handshake', methods=['POST'], cors=True)
def handshake():
    global key
    body = app.current_request.json_body
    key = body.get('api_key')
    genai.configure(api_key=key)

    return "success"


@app.route('/gemini', methods=['POST'], cors=True)
def prompt():
    body = app.current_request.json_body
    prompt = body.get('message')
    print(prompt)
    if not prompt:
        return {'error': 'No message provided'}
    
    # Establish Client Connection
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    if not model:
        return {'error': 'Gemini Model Failed'}

    response = model.generate_content(prompt)
    print(response.text)
    if not response:
        return {'error': 'Gemini Failed to Produce a Message'}
    return {'response': response.text}


@app.route('/transcribe', methods=['POST'], content_types=['application/json'], cors=True)
def transcribe():
    try:
        body = app.current_request.json_body
        audio_b64 = body.get('audio_blob')

        if not audio_b64:
            return {'error': 'Missing audio_blob'}

        audio_bytes = base64.b64decode(audio_b64)

        # Save the Original PCM File
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pcm') as f:
            f.write(audio_bytes)
            raw_path = f.name

        # Downsample for AWS
        downsampled_path = raw_path.replace('.pcm', '_16k.pcm')
        downsample_pcm(raw_path, downsampled_path)

        service = transcribe_service.TranscriptionService()
        transcript = service.transcribe_from_file(downsampled_path)

        return {'transcript': transcript}

    except Exception as e:
        return {'error': str(e)}


@app.route('/speak', methods=['POST'], content_types=['application/json'], cors=True)
def synthesize_speech():
    body = app.current_request.json_body
    text = body.get('text')

    if not text:
        return {'error': 'No text Provided!'}

    service = polly_service.PollyService()
    audio_b64 = service.synthesize(text)

    if not audio_b64:
        return {'error': 'Polly Failed!'}

    return {'audio_base64': audio_b64}