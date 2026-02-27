#!/usr/bin/env python
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Sequence

try:
    from music21 import chord, converter, instrument, key, meter, note, stream
except ImportError:
    print(
        "[ERROR] Missing dependency: music21. Please run: pip install -r requirements.txt"
    )
    raise SystemExit(1)


MIDI_SUFFIXES = {".mid", ".midi"}


def is_midi_file(path: Path) -> bool:
    return path.suffix.lower() in MIDI_SUFFIXES


def is_percussion_part(part: stream.Part) -> bool:
    part_name = f"{part.partName or ''} {part.id or ''}".lower()
    if any(
        x in part_name
        for x in ["drum", "perc", "kick", "snare", "hihat", "hi-hat", "cymbal"]
    ):
        return True

    for inst in part.recurse().getElementsByClass(instrument.Instrument):
        channel = getattr(inst, "midiChannel", None)
        if channel == 9:
            return True
        if getattr(inst, "isPercussion", False):
            return True
        name = (inst.instrumentName or "").lower()
        if "drum" in name or "percussion" in name:
            return True

    unpitched_count = len(list(part.recurse().getElementsByClass(note.Unpitched)))
    pitched_count = len(list(part.recurse().getElementsByClass(note.Note))) + len(
        list(part.recurse().getElementsByClass(chord.Chord))
    )
    if unpitched_count > 0 and pitched_count == 0:
        return True
    if unpitched_count > pitched_count:
        return True
    return False


def filter_percussion(score: stream.Score) -> stream.Score:
    kept_parts = []
    for p in score.parts:
        if not is_percussion_part(p):
            kept_parts.append(p)
    if not kept_parts:
        return score

    out = stream.Score(id=score.id)
    for p in kept_parts:
        out.append(p)
    return out


def replace_unpitched_with_rests(score: stream.Score) -> int:
    replaced = 0
    unpitched_notes = list(score.recurse().getElementsByClass(note.Unpitched))
    for up in unpitched_notes:
        site = up.activeSite
        if site is None:
            continue
        rest = note.Rest()
        rest.duration = up.duration
        try:
            site.replace(up, rest, allDerived=True)
            replaced += 1
        except Exception:
            try:
                site.remove(up, recurse=True)
                replaced += 1
            except Exception:
                continue
    return replaced


def part_note_count(part: stream.Part) -> int:
    count = 0
    for el in part.recurse().notes:
        if isinstance(el, note.Note):
            count += 1
        elif isinstance(el, chord.Chord):
            count += max(1, len(el.pitches))
    return count


def choose_melody_part(score: stream.Score) -> stream.Score:
    if len(score.parts) <= 1:
        return score

    best = max(score.parts, key=part_note_count)
    out = stream.Score(id=score.id)
    out.append(best)
    return out


def parse_grid_to_divisors(grid_text: str) -> Sequence[int]:
    mapping = {4: 1, 8: 2, 16: 4, 32: 8, 64: 16}
    divisors = []
    for token in grid_text.split(","):
        token = token.strip()
        if not token:
            continue
        value = int(token)
        if value not in mapping:
            raise ValueError(f"Unsupported grid denominator: {value}")
        divisors.append(mapping[value])
    if not divisors:
        raise ValueError("Quantization grid cannot be empty.")
    return sorted(set(divisors))


def quantize_score(score: stream.Score, divisors: Iterable[int]) -> stream.Score:
    return score.quantize(
        quarterLengthDivisors=tuple(divisors),
        processOffsets=True,
        processDurations=True,
        inPlace=False,
    )


def has_time_signature(score: stream.Score) -> bool:
    return bool(score.recurse().getElementsByClass(meter.TimeSignature))


def has_key_signature(score: stream.Score) -> bool:
    return bool(score.recurse().getElementsByClass(key.KeySignature))


def apply_time_signature(score: stream.Score, time_sig: str) -> None:
    ts = meter.TimeSignature(time_sig)
    if score.parts:
        for p in score.parts:
            p.insert(0, ts)
    else:
        score.insert(0, ts)


def apply_key(score: stream.Score, key_text: str) -> None:
    k = key.Key(key_text)
    if score.parts:
        for p in score.parts:
            p.insert(0, k)
    else:
        score.insert(0, k)


def estimate_key_if_needed(score: stream.Score) -> None:
    if has_key_signature(score):
        return
    try:
        k = score.analyze("key")
    except Exception:
        return
    if score.parts:
        for p in score.parts:
            p.insert(0, k)
    else:
        score.insert(0, k)


def resolve_musescore_bin(user_defined: str | None) -> str | None:
    if user_defined:
        return user_defined
    candidates = ["MuseScore4.exe", "MuseScore4", "musescore", "mscore", "mscore4portable"]
    for c in candidates:
        if shutil.which(c):
            return c
    return None


def render_pdf(musicxml_path: Path, pdf_path: Path, musescore_bin: str | None) -> None:
    binary = resolve_musescore_bin(musescore_bin)
    if not binary:
        raise RuntimeError(
            "MuseScore executable not found. Use --musescore-bin to specify it."
        )
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [binary, str(musicxml_path), "-o", str(pdf_path)]
    subprocess.run(cmd, check=True)


def convert_midi_to_sheet(
    input_midi: Path,
    output_musicxml: Path,
    *,
    pdf_path: Path | None = None,
    musescore_bin: str | None = None,
    keep_percussion: bool = False,
    melody_only: bool = False,
    grid: str = "4,8,16",
    set_time: str | None = None,
    set_key: str | None = None,
    estimate_key: bool = False,
) -> Path:
    if not input_midi.exists():
        raise FileNotFoundError(f"Input MIDI not found: {input_midi}")
    if not is_midi_file(input_midi):
        raise ValueError(
            f"Unsupported MIDI extension: {input_midi.suffix}. Supported: {sorted(MIDI_SUFFIXES)}"
        )

    output_musicxml.parent.mkdir(parents=True, exist_ok=True)

    try:
        score = converter.parse(str(input_midi))
    except Exception as exc:
        raise RuntimeError(f"Failed to parse MIDI: {exc}") from exc

    if not keep_percussion:
        score = filter_percussion(score)
        replace_unpitched_with_rests(score)

    if melody_only:
        score = choose_melody_part(score)

    try:
        divisors = parse_grid_to_divisors(grid)
        score = quantize_score(score, divisors)
    except Exception as exc:
        raise RuntimeError(f"Quantization failed: {exc}") from exc

    if set_time:
        try:
            apply_time_signature(score, set_time)
        except Exception as exc:
            raise RuntimeError(f"Invalid --set-time value: {exc}") from exc
    elif not has_time_signature(score):
        apply_time_signature(score, "4/4")

    if set_key:
        try:
            apply_key(score, set_key)
        except Exception as exc:
            raise RuntimeError(f"Invalid --set-key value: {exc}") from exc
    elif estimate_key:
        estimate_key_if_needed(score)

    try:
        score.write("musicxml", fp=str(output_musicxml))
    except Exception as exc:
        exc_text = str(exc)
        if "Unpitched" in exc_text or "instrumentStream" in exc_text:
            replaced = replace_unpitched_with_rests(score)
            if replaced > 0:
                score.write("musicxml", fp=str(output_musicxml))
            else:
                raise RuntimeError(f"Failed to write MusicXML: {exc}") from exc
        else:
            raise RuntimeError(f"Failed to write MusicXML: {exc}") from exc

    if pdf_path:
        render_pdf(output_musicxml, pdf_path, musescore_bin)

    return output_musicxml


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert MIDI file into MusicXML sheet, with optional PDF rendering."
    )
    parser.add_argument("input", type=Path, help="Input MIDI file path (.mid/.midi)")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output MusicXML path. Default: <input_stem>.musicxml",
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
    parser.add_argument(
        "--keep-percussion",
        action="store_true",
        help="Keep percussion/drum tracks (default removes them).",
    )
    parser.add_argument(
        "--melody-only",
        action="store_true",
        help="Extract only one melody-like part using a simple heuristic.",
    )
    parser.add_argument(
        "--grid",
        type=str,
        default="4,8,16",
        help="Quantization grid as note denominators, comma separated. Default: 4,8,16",
    )
    parser.add_argument(
        "--set-time",
        type=str,
        help='Force time signature (for example: "4/4").',
    )
    parser.add_argument(
        "--set-key",
        type=str,
        help='Force key (for example: "C", "G", "Am").',
    )
    parser.add_argument(
        "--estimate-key",
        action="store_true",
        help="Estimate key if missing and not set by --set-key.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = args.input
    output_path = args.output or input_path.with_suffix(".musicxml")

    try:
        convert_midi_to_sheet(
            input_path,
            output_path,
            pdf_path=args.pdf,
            musescore_bin=args.musescore_bin,
            keep_percussion=args.keep_percussion,
            melody_only=args.melody_only,
            grid=args.grid,
            set_time=args.set_time,
            set_key=args.set_key,
            estimate_key=args.estimate_key,
        )
    except Exception as exc:
        print(f"[ERROR] {exc}")
        return 1

    print(f"[OK] MusicXML written: {output_path}")
    if args.pdf:
        print(f"[OK] PDF written: {args.pdf}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
