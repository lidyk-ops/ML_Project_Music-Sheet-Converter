#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from audio2midi import convert_audio_to_midi, is_audio_file
from midi2sheet import convert_midi_to_sheet, is_midi_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Minimal CLI: convert MP3/WAV/MIDI directly to MusicXML."
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Input file path (.mp3/.wav/.flac/.m4a/.aac/.ogg/.mid/.midi)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output MusicXML path. Default: <input_stem>.musicxml",
    )
    parser.add_argument(
        "--midi-out",
        type=Path,
        help="Optional path to save intermediate MIDI when input is audio.",
    )
    parser.add_argument(
        "--pdf",
        type=Path,
        help="Optional PDF output path. Requires MuseScore CLI.",
    )
    parser.add_argument(
        "--musescore-bin",
        type=str,
        help="MuseScore executable path/name. Example: MuseScore4.exe",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = args.input
    if not input_path.exists():
        print(f"[ERROR] Input file not found: {input_path}")
        return 1

    output_path = args.output or input_path.with_suffix(".musicxml")

    if is_midi_file(input_path):
        try:
            convert_midi_to_sheet(
                input_path,
                output_path,
                pdf_path=args.pdf,
                musescore_bin=args.musescore_bin,
            )
        except Exception as exc:
            print(f"[ERROR] {exc}")
            return 1
        print(f"[OK] MusicXML written: {output_path}")
        if args.pdf:
            print(f"[OK] PDF written: {args.pdf}")
        return 0

    if is_audio_file(input_path):
        temp_dir_obj: tempfile.TemporaryDirectory[str] | None = None
        try:
            if args.midi_out:
                midi_path = args.midi_out
            else:
                temp_dir_obj = tempfile.TemporaryDirectory(prefix="pipeline_midi_")
                midi_path = Path(temp_dir_obj.name) / f"{input_path.stem}.mid"
            convert_audio_to_midi(input_path, midi_path)
            print(f"[OK] MIDI written: {midi_path}")
            convert_midi_to_sheet(
                midi_path,
                output_path,
                pdf_path=args.pdf,
                musescore_bin=args.musescore_bin,
            )
        except Exception as exc:
            print(f"[ERROR] {exc}")
            return 1
        finally:
            if temp_dir_obj is not None:
                temp_dir_obj.cleanup()

        print(f"[OK] MusicXML written: {output_path}")
        if args.pdf:
            print(f"[OK] PDF written: {args.pdf}")
        return 0

    print(
        "[ERROR] Unsupported input extension. "
        "Use .mid/.midi or .mp3/.wav/.flac/.m4a/.aac/.ogg."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
