from flask import Flask, render_template, request, send_file
import wave
import io
import struct
import base64

app = Flask(__name__)

def text_to_wav_base64(text, sample_rate=44100):
    """Convert Base64 text directly to WAV audio data"""
    try:
        # Decode the text as base64 (must be valid base64)
        decoded_bytes = base64.b64decode(text, validate=True)
    except Exception as e:
        raise ValueError(f"Invalid Base64 input: {str(e)}")

    if len(decoded_bytes) == 0:
        raise ValueError("Base64 decoded to empty data")

    # Create WAV data in memory
    wav_buffer = io.BytesIO()

    with wave.open(wav_buffer, 'wb') as wav_file:
        # Set WAV parameters
        wav_file.setnchannels(1)        # Mono
        wav_file.setsampwidth(2)        # 16-bit
        wav_file.setframerate(sample_rate)

        # Convert decoded bytes to audio samples
        audio_data = b''
        for byte in decoded_bytes:
            # Convert byte (0-255) to signed 16-bit sample (-32768 to 32767)
            sample = (byte - 128) * 256
            audio_data += struct.pack('<h', sample)  # Little-endian 16-bit

        wav_file.writeframes(audio_data)

    wav_buffer.seek(0)
    return wav_buffer, len(decoded_bytes)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_audio():
    # Handle both form data and JSON
    if request.is_json:
        text = request.json.get('text', '') if request.json else ''
    else:
        text = request.form.get('text', '') if request.form else ''

    if not text.strip():
        return "No text provided", 400

    try:
        # Generate WAV file
        wav_buffer, byte_count = text_to_wav_base64(text)

        # Return the audio file for browser playback
        return send_file(
            wav_buffer,
            mimetype='audio/wav',
            as_attachment=False,  # Play in browser, don't download
        )
    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True)
