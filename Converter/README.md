# Audio/MIDI to Sheet Converter

This project is split into 4 clear entry points:

- `audio2midi.py`: `Audio -> MIDI` only
- `midi2sheet.py`: `MIDI -> MusicXML/PDF` only
- `convert.py`: minimal CLI that chains both steps
- `webapp.py`: simple web UI with categorized actions

## 1. Install Dependencies

### Windows (PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-audio.txt
```

### WSL / Linux / macOS (bash)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-audio.txt
```

Python 3.11 is recommended for audio features (`basic-pitch`).

### Windows Python 3.11 setup

```powershell
py install 3.11
py -3.11 -m venv .venv311
.\.venv311\Scripts\python.exe -m pip install -r requirements.txt
.\.venv311\Scripts\python.exe -m pip install -r requirements-audio.txt
```

### WSL/Linux Python 3.11 setup

If `python3.11` is missing in WSL (Ubuntu), install it first:

```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip
```

```bash
python3.11 -m venv .venv311
source .venv311/bin/activate
python -m pip install -r requirements.txt
python -m pip install -r requirements-audio.txt
```

## 2. Step-by-Step Conversion

### A. MP3/WAV -> MIDI

Windows:

```powershell
.\.venv\Scripts\python.exe .\audio2midi.py .\input.mp3 -o .\out\from_audio.mid
```

WSL/Linux/macOS:

```bash
python audio2midi.py ./input.mp3 -o ./out/from_audio.mid
```

### B. MIDI -> MusicXML

Windows:

```powershell
.\.venv\Scripts\python.exe .\midi2sheet.py .\out\from_audio.mid -o .\out\score.musicxml
```

WSL/Linux/macOS:

```bash
python midi2sheet.py ./out/from_audio.mid -o ./out/score.musicxml
```

## 3. Minimal CLI (One Command)

Windows:

```powershell
.\.venv\Scripts\python.exe .\convert.py .\input.mp3 -o .\out\score.musicxml
```

WSL/Linux/macOS:

```bash
python convert.py ./input.mp3 -o ./out/score.musicxml
```

Optional: save intermediate MIDI

Windows:

```powershell
.\.venv\Scripts\python.exe .\convert.py .\input.mp3 `
  --midi-out .\out\from_audio.mid `
  -o .\out\score.musicxml
```

WSL/Linux/macOS:

```bash
python convert.py ./input.mp3 \
  --midi-out ./out/from_audio.mid \
  -o ./out/score.musicxml
```

If input is already MIDI:

```bash
python convert.py ./input.mid -o ./out/score.musicxml
```

## 4. Advanced `midi2sheet.py` Options

```bash
python midi2sheet.py ./input.mid \
  -o ./out/score.musicxml \
  --melody-only \
  --grid 4,8,16 \
  --set-time 4/4 \
  --estimate-key
```

Export PDF:

```bash
python midi2sheet.py ./input.mid --pdf ./out/score.pdf
```

If MuseScore is not in PATH, set it manually:

```bash
python midi2sheet.py ./input.mid \
  --pdf ./out/score.pdf \
  --musescore-bin "/path/to/MuseScore"
```

Windows example:

```powershell
.\.venv\Scripts\python.exe .\midi2sheet.py .\input.mid `
  --pdf .\out\score.pdf `
  --musescore-bin "C:\Program Files\MuseScore 4\bin\MuseScore4.exe"
```

## 5. Notes

- `Audio -> MIDI` is automatic transcription; complex songs may need manual cleanup.
- `MIDI -> MusicXML` does basic quantization/cleanup; final polishing is best done in MuseScore.

## 6. Web UI

Start server:

Windows:

```powershell
.\.venv\Scripts\python.exe .\webapp.py
```

WSL/Linux/macOS:

```bash
python webapp.py
```

Open:

```text
http://127.0.0.1:5000
```

UI categories:

- `Category A`: Audio -> MIDI
- `Category B`: MIDI -> MusicXML
- `Category C`: Audio -> MusicXML

Audio categories need `basic-pitch` (`requirements-audio.txt`).
If your Python version cannot install it, the web app keeps Category B available and disables A/C.
