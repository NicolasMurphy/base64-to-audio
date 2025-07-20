from flask import Flask, render_template, request, send_file, jsonify
import wave
import io
import struct
import base64

app = Flask(__name__)


def is_wav_data(decoded_bytes):
    """Check if the decoded bytes represent a WAV file"""
    return (
        len(decoded_bytes) >= 12
        and decoded_bytes[:4] == b"RIFF"
        and decoded_bytes[8:12] == b"WAVE"
    )


def analyze_base64_for_audio(text):
    """Analyze Base64 input and provide educational feedback"""
    try:
        decoded = base64.b64decode(text, validate=True)
    except Exception as e:
        return {
            "valid": False,
            "error": f"Invalid Base64 format: {str(e)}",
            "suggestions": [
                "Base64 must contain only A-Z, a-z, 0-9, +, / characters",
                "Must end with proper padding (0, 1, or 2 '=' signs)",
                "Length must be divisible by 4",
            ],
        }

    if len(decoded) == 0:
        return {
            "valid": False,
            "error": "Base64 decoded to empty data",
            "suggestions": ["Try entering some actual Base64 content"],
        }

    data_length = len(decoded)
    issues = []
    suggestions = []
    facts = []

    # Check if it's already a WAV file
    if is_wav_data(decoded):
        return {
            "valid": True,
            "is_wav": True,
            "message": "This is already a valid WAV file!",
            "stats": {
                "base64_length": len(text),
                "file_size": data_length,
                "type": "Complete WAV file",
            },
        }

    # Analyze for WAV requirements
    facts.append(f"Your Base64 text: {len(text)} characters")
    facts.append(f"Decoded data size: {data_length} bytes")

    # Length analysis
    if data_length < 100:
        issues.append(f"Data is only {data_length} bytes - very short for audio")
        suggestions.append("Try longer Base64 text (aim for 100+ bytes)")

    duration_44k = (data_length / 2) / 44100
    facts.append(f"Would create {duration_44k:.4f} seconds of audio at 44.1kHz")

    # Even bytes check for 16-bit audio
    if data_length % 2 != 0:
        issues.append("Odd number of bytes - 16-bit audio needs even byte count")
        suggestions.append("Add one more character to make the decoded length even")
    else:
        facts.append("Even byte count is good for 16-bit audio")

    # Sample analysis
    sample_count = data_length // 2
    facts.append(f"Creates {sample_count} audio samples")

    return {
        "valid": len(issues) == 0,
        "is_wav": False,
        "issues": issues,
        "suggestions": suggestions,
        "facts": facts,
        "stats": {
            "base64_length": len(text),
            "decoded_size": data_length,
            "sample_count": sample_count,
            "duration_seconds": duration_44k,
        },
    }


def wrap_audio_data_as_wav(audio_data):
    """Wrap raw audio data with WAV headers"""
    wav_buffer = io.BytesIO()

    with wave.open(wav_buffer, "wb") as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(44100)  # Fixed sample rate
        wav_file.writeframes(audio_data)

    wav_buffer.seek(0)
    return wav_buffer


def text_to_wav_base64(text):
    """Convert Base64 text to WAV - auto-detect if it's already WAV or raw audio data"""
    try:
        decoded_bytes = base64.b64decode(text, validate=True)
    except Exception as e:
        raise ValueError(f"Invalid Base64 input: {str(e)}")

    if len(decoded_bytes) == 0:
        raise ValueError("Base64 decoded to empty data")

    # Check if it's already a complete WAV file
    if is_wav_data(decoded_bytes):
        wav_buffer = io.BytesIO(decoded_bytes)
        return wav_buffer
    else:
        # Treat as raw audio data and wrap with WAV headers
        return wrap_audio_data_as_wav(decoded_bytes)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    """Analyze Base64 input and return educational feedback"""
    if not request.is_json or request.json is None:
        return jsonify({"error": "JSON required"}), 400

    text = request.json.get("text", "").strip()
    if not text:
        return jsonify({"error": "No text provided"}), 400

    analysis = analyze_base64_for_audio(text)
    return jsonify(analysis)


@app.route("/generate", methods=["POST"])
def generate_audio():
    """Generate audio from Base64 input"""
    if not request.is_json or request.json is None:
        return "JSON required", 400

    text = request.json.get("text", "").strip()
    if not text:
        return "No text provided", 400

    try:
        wav_buffer = text_to_wav_base64(text)
        return send_file(wav_buffer, mimetype="audio/wav", as_attachment=False)
    except Exception as e:
        return f"Error: {str(e)}", 500


if __name__ == "__main__":
    app.run(debug=True)
