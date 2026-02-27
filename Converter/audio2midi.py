#!/usr/bin/env python
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


AUDIO_SUFFIXES = {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg"}


def is_audio_file(path: Path) -> bool:
    return path.suffix.lower() in AUDIO_SUFFIXES


def run_basic_pitch_cli(audio_path: Path, output_dir: Path) -> None:
    commands = [
        ["basic-pitch", str(output_dir), str(audio_path)],
        [sys.executable, "-m", "basic_pitch", str(output_dir), str(audio_path)],
    ]
    errors: list[str] = []
    for cmd in commands:
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            return
        except FileNotFoundError:
            errors.append(f"Command not found: {cmd[0]}")
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or str(exc)).strip()
            errors.append(f"{' '.join(cmd)} failed: {detail}")
    raise RuntimeError(
        "Unable to run basic-pitch. Install it with: pip install -r requirements-audio.txt. "
        f"Details: {' | '.join(errors)}"
    )


def resolve_generated_midi(audio_path: Path, output_dir: Path) -> Path:
    expected = output_dir / f"{audio_path.stem}_basic_pitch.mid"
    if expected.exists():
        return expected

    midi_files = sorted(output_dir.glob("*.mid"))
    if not midi_files:
        raise RuntimeError("basic-pitch finished but no MIDI file was produced.")
    return max(midi_files, key=lambda p: p.stat().st_mtime)


def convert_audio_to_midi(
    input_audio: Path, output_midi: Path, *, engine: str = "basic-pitch"
) -> Path:
    if not input_audio.exists():
        raise FileNotFoundError(f"Input audio not found: {input_audio}")
    if not is_audio_file(input_audio):
        raise ValueError(
            f"Unsupported audio extension: {input_audio.suffix}. Supported: {sorted(AUDIO_SUFFIXES)}"
        )
    if engine != "basic-pitch":
        raise ValueError(f"Unsupported audio engine: {engine}")

    output_midi.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="audio2midi_") as temp_dir:
        tmp_out = Path(temp_dir)
        run_basic_pitch_cli(input_audio, tmp_out)
        generated = resolve_generated_midi(input_audio, tmp_out)
        shutil.copy2(generated, output_midi)
    return output_midi


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert audio file into MIDI using basic-pitch."
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Input audio file path (.mp3/.wav/.flac/.m4a/.aac/.ogg)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output MIDI path. Default: <input_stem>.mid",
    )
    parser.add_argument(
        "--engine",
        type=str,
        default="basic-pitch",
        choices=["basic-pitch"],
        help="Audio-to-MIDI engine. Default: basic-pitch",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = args.input
    output_path = args.output or input_path.with_suffix(".mid")

    try:
        convert_audio_to_midi(input_path, output_path, engine=args.engine)
    except Exception as exc:
        print(f"[ERROR] {exc}")
        return 1

    print(f"[OK] MIDI written: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
