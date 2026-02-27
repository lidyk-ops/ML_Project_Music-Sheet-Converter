#!/usr/bin/env python
from __future__ import annotations

import uuid
import importlib.util
from pathlib import Path

from flask import Flask, render_template_string, request, send_file

from audio2midi import convert_audio_to_midi
from midi2sheet import convert_midi_to_sheet


APP_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = APP_DIR / "web_uploads"
OUTPUT_DIR = APP_DIR / "web_out"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
AUDIO_ENGINE_READY = importlib.util.find_spec("basic_pitch") is not None


HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Audio/MIDI Converter</title>
  <style>
    :root {
      --bg: #f2f5f8;
      --card: #ffffff;
      --line: #d8e0e8;
      --text: #1f2a37;
      --muted: #57667a;
      --accent: #0d6efd;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", Tahoma, sans-serif;
      color: var(--text);
      background: linear-gradient(140deg, #eef4ff 0%, #f6fbf4 100%);
    }
    .wrap {
      max-width: 960px;
      margin: 28px auto;
      padding: 0 16px 24px;
    }
    h1 { margin: 0 0 10px; font-size: 28px; }
    p.sub { margin: 0 0 20px; color: var(--muted); }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 14px;
    }
    .card {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 14px;
    }
    .card h2 {
      margin: 0 0 10px;
      font-size: 18px;
    }
    .hint {
      margin: 0 0 10px;
      color: #8a5a00;
      font-size: 13px;
      background: #fff8e1;
      border: 1px solid #f4de9a;
      border-radius: 8px;
      padding: 8px;
    }
    .label {
      display: block;
      margin-bottom: 6px;
      color: var(--muted);
      font-size: 13px;
    }
    input[type=file] {
      width: 100%;
      margin-bottom: 10px;
    }
    button {
      border: 0;
      border-radius: 8px;
      padding: 9px 12px;
      background: var(--accent);
      color: white;
      cursor: pointer;
      font-weight: 600;
    }
    button[disabled] {
      background: #9cb1d1;
      cursor: not-allowed;
    }
    .result {
      margin: 14px 0;
      padding: 10px 12px;
      border-radius: 10px;
      background: #fff;
      border: 1px solid var(--line);
    }
    .error {
      border-color: #f0b3b3;
      background: #fff5f5;
      color: #8a1f1f;
    }
    .ok {
      border-color: #b8dfc6;
      background: #f3fff7;
      color: #155d33;
    }
    a {
      color: var(--accent);
      text-decoration: none;
      font-weight: 600;
    }
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Audio/MIDI to Music Sheet</h1>
    <p class="sub">Simple web UI with clear categories.</p>

    {% if message %}
      <div class="result {{ 'error' if is_error else 'ok' }}">
        {{ message }}
        {% if files %}
          <ul>
            {% for name in files %}
              <li><a href="/download/{{ name }}">Download {{ name }}</a></li>
            {% endfor %}
          </ul>
        {% endif %}
      </div>
    {% endif %}

    <div class="grid">
      <div class="card">
        <h2>Category A: Audio -> MIDI</h2>
        {% if not audio_ready %}
          <p class="hint">Audio engine is not installed in this environment.</p>
        {% endif %}
        <form method="post" action="/audio-to-midi" enctype="multipart/form-data">
          <label class="label">Upload audio (.mp3/.wav/.flac/.m4a/.aac/.ogg)</label>
          <input type="file" name="audio_file" accept=".mp3,.wav,.flac,.m4a,.aac,.ogg" required {% if not audio_ready %}disabled{% endif %} />
          <button type="submit" {% if not audio_ready %}disabled{% endif %}>Convert</button>
        </form>
      </div>

      <div class="card">
        <h2>Category B: MIDI -> MusicXML</h2>
        <form method="post" action="/midi-to-sheet" enctype="multipart/form-data">
          <label class="label">Upload MIDI (.mid/.midi)</label>
          <input type="file" name="midi_file" accept=".mid,.midi" required />
          <button type="submit">Convert</button>
        </form>
      </div>

      <div class="card">
        <h2>Category C: Audio -> MusicXML</h2>
        {% if not audio_ready %}
          <p class="hint">Audio engine is not installed in this environment.</p>
        {% endif %}
        <form method="post" action="/audio-to-sheet" enctype="multipart/form-data">
          <label class="label">Upload audio (.mp3/.wav/.flac/.m4a/.aac/.ogg)</label>
          <input type="file" name="audio_file" accept=".mp3,.wav,.flac,.m4a,.aac,.ogg" required {% if not audio_ready %}disabled{% endif %} />
          <button type="submit" {% if not audio_ready %}disabled{% endif %}>Convert</button>
        </form>
      </div>
    </div>
  </div>
</body>
</html>
"""


def _unique_path(original_name: str, suffix: str, base_dir: Path) -> Path:
    token = uuid.uuid4().hex[:10]
    stem = Path(original_name).stem or "file"
    safe_stem = "".join(ch for ch in stem if ch.isalnum() or ch in ("-", "_")) or "file"
    return base_dir / f"{safe_stem}_{token}{suffix}"


def _home(message: str | None = None, is_error: bool = False, files: list[str] | None = None):
    return render_template_string(
        HTML,
        message=message,
        is_error=is_error,
        files=files or [],
        audio_ready=AUDIO_ENGINE_READY,
    )


@app.get("/")
def index():
    return _home()


@app.post("/audio-to-midi")
def audio_to_midi():
    if not AUDIO_ENGINE_READY:
        return _home(
            "Audio engine not available. Install requirements-audio.txt with a supported Python version.",
            True,
        )
    up = request.files.get("audio_file")
    if not up or not up.filename:
        return _home("Missing audio file.", True)
    in_path = _unique_path(up.filename, Path(up.filename).suffix.lower(), UPLOAD_DIR)
    out_path = _unique_path(up.filename, ".mid", OUTPUT_DIR)
    up.save(in_path)

    try:
        convert_audio_to_midi(in_path, out_path)
    except Exception as exc:
        return _home(f"Audio to MIDI failed: {exc}", True)

    return _home("Conversion completed.", False, [out_path.name])


@app.post("/midi-to-sheet")
def midi_to_sheet():
    up = request.files.get("midi_file")
    if not up or not up.filename:
        return _home("Missing MIDI file.", True)
    in_path = _unique_path(up.filename, Path(up.filename).suffix.lower(), UPLOAD_DIR)
    out_path = _unique_path(up.filename, ".musicxml", OUTPUT_DIR)
    up.save(in_path)

    try:
        convert_midi_to_sheet(in_path, out_path)
    except Exception as exc:
        return _home(f"MIDI to MusicXML failed: {exc}", True)

    return _home("Conversion completed.", False, [out_path.name])


@app.post("/audio-to-sheet")
def audio_to_sheet():
    if not AUDIO_ENGINE_READY:
        return _home(
            "Audio engine not available. Install requirements-audio.txt with a supported Python version.",
            True,
        )
    up = request.files.get("audio_file")
    if not up or not up.filename:
        return _home("Missing audio file.", True)
    in_path = _unique_path(up.filename, Path(up.filename).suffix.lower(), UPLOAD_DIR)
    mid_path = _unique_path(up.filename, ".mid", OUTPUT_DIR)
    xml_path = _unique_path(up.filename, ".musicxml", OUTPUT_DIR)
    up.save(in_path)

    try:
        convert_audio_to_midi(in_path, mid_path)
        convert_midi_to_sheet(mid_path, xml_path)
    except Exception as exc:
        return _home(f"Audio to MusicXML failed: {exc}", True)

    return _home("Conversion completed.", False, [mid_path.name, xml_path.name])


@app.get("/download/<path:name>")
def download(name: str):
    path = OUTPUT_DIR / name
    if not path.exists() or not path.is_file():
        return _home("File not found.", True)
    return send_file(path, as_attachment=True)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
