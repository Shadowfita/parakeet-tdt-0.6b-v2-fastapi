#!/usr/bin/env python3
"""
Process LibriSpeech dataset and prepare test samples.

This script:
1. Finds all FLAC audio files
2. Parses transcript files
3. Creates combined test samples of different durations
4. Generates file lists for audio concatenation
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from collections import defaultdict

def find_flac_files(directory):
    """Find all FLAC files in directory."""
    print(f"Searching for FLAC files in {directory}...")
    files = list(Path(directory).rglob("*.flac"))
    print(f"  Found {len(files)} FLAC files")
    return sorted(files)

def find_transcript_files(directory):
    """Find all transcript files."""
    print(f"Searching for transcript files in {directory}...")
    files = list(Path(directory).rglob("*.trans.txt"))
    print(f"  Found {len(files)} transcript files")
    return files

def parse_transcript_file(trans_file):
    """
    Parse a LibriSpeech transcript file.

    Format: <utterance-id> <transcript-text>
    Example: 1272-128104-0000 MISTER QUILTER IS THE APOSTLE OF THE MIDDLE CLASSES
    """
    transcripts = {}
    with open(trans_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(' ', 1)
            if len(parts) == 2:
                utterance_id, text = parts
                transcripts[utterance_id] = text
    return transcripts

def get_audio_duration(audio_file):
    """Get duration of audio file using ffprobe."""
    try:
        cmd = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(audio_file)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        return 0.0

def create_test_samples(audio_files, all_transcripts, target_durations):
    """
    Create test samples of different durations.

    Args:
        audio_files: List of audio file paths
        all_transcripts: Dictionary of {utterance_id: text}
        target_durations: List of (name, target_seconds, description)

    Returns:
        List of sample metadata
    """
    samples = []

    for name, target_seconds, description in target_durations:
        print(f"\nCreating {name} sample ({description})...")

        selected_files = []
        selected_transcripts = []
        total_duration = 0.0

        for audio_file in audio_files:
            if total_duration >= target_seconds:
                break

            utterance_id = audio_file.stem

            if utterance_id in all_transcripts:
                # Get duration
                duration = get_audio_duration(audio_file)
                if duration > 0:
                    selected_files.append(str(audio_file))
                    selected_transcripts.append(all_transcripts[utterance_id])
                    total_duration += duration

                    if len(selected_files) % 10 == 0:
                        print(f"  Selected {len(selected_files)} files, duration: {total_duration:.1f}s")

        if not selected_files:
            print(f"  ✗ No files selected for {name}")
            continue

        # Create sample metadata
        sample = {
            'name': name,
            'description': description,
            'target_duration': target_seconds,
            'actual_duration': total_duration,
            'num_files': len(selected_files),
            'audio_files': selected_files,
            'transcripts': selected_transcripts,
            'total_words': sum(len(t.split()) for t in selected_transcripts),
            'total_chars': sum(len(t) for t in selected_transcripts)
        }

        samples.append(sample)

        print(f"  ✓ {name} sample created:")
        print(f"    Files: {len(selected_files)}")
        print(f"    Duration: {total_duration:.1f}s ({total_duration/60:.1f} minutes)")
        print(f"    Words: {sample['total_words']}")

    return samples

def save_sample_files(sample, output_dir):
    """Save sample files (reference text and audio file list)."""
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    name = sample['name']

    # Save reference text
    ref_file = output_dir / f"reference_{name}.txt"
    with open(ref_file, 'w', encoding='utf-8') as f:
        # Join transcripts with spaces
        combined_text = ' '.join(sample['transcripts'])
        f.write(combined_text)

    # Save audio file list for ffmpeg concat
    filelist_file = output_dir / f"filelist_{name}.txt"
    with open(filelist_file, 'w', encoding='utf-8') as f:
        for audio_file in sample['audio_files']:
            # FFmpeg concat requires absolute paths or paths with proper escaping
            f.write(f"file '{audio_file}'\n")

    sample['reference_file'] = str(ref_file)
    sample['filelist_file'] = str(filelist_file)

    print(f"  Saved: {ref_file.name} and {filelist_file.name}")

    return sample

def main():
    print("=" * 80)
    print("LIBRISPEECH DATA PROCESSOR")
    print("=" * 80)
    print()

    # Check if LibriSpeech data exists
    librispeech_dir = Path("test_data/LibriSpeech/dev-clean")

    if not librispeech_dir.exists():
        print(f"✗ LibriSpeech directory not found: {librispeech_dir}")
        print("\nPlease run: ./download_librispeech.sh first")
        return 1

    print(f"✓ LibriSpeech directory found: {librispeech_dir}")
    print()

    # Find audio files
    audio_files = find_flac_files(librispeech_dir)

    if not audio_files:
        print("✗ No audio files found")
        return 1

    # Find and parse transcripts
    transcript_files = find_transcript_files(librispeech_dir)

    print("\nParsing transcripts...")
    all_transcripts = {}
    for trans_file in transcript_files:
        transcripts = parse_transcript_file(trans_file)
        all_transcripts.update(transcripts)

    print(f"  Parsed {len(all_transcripts)} transcripts")

    # Define target durations
    # For 2 hours = 7200 seconds, but let's create progressively longer samples
    target_durations = [
        ("short", 300, "~5 minutes"),
        ("medium", 900, "~15 minutes"),
        ("long", 1800, "~30 minutes"),
        ("xlarge", 3600, "~1 hour"),
        ("2hours", 7200, "~2 hours"),
    ]

    print("\n" + "=" * 80)
    print("CREATING TEST SAMPLES")
    print("=" * 80)

    # Create samples
    samples = create_test_samples(audio_files, all_transcripts, target_durations)

    if not samples:
        print("\n✗ No samples created")
        return 1

    # Save sample files
    print("\n" + "=" * 80)
    print("SAVING SAMPLE FILES")
    print("=" * 80)
    print()

    output_dir = Path("test_data")

    for sample in samples:
        save_sample_files(sample, output_dir)

    # Save metadata
    metadata_file = output_dir / "librispeech_samples.json"

    # Remove audio_files and transcripts from metadata (too large)
    metadata_samples = []
    for sample in samples:
        meta_sample = {k: v for k, v in sample.items()
                      if k not in ['audio_files', 'transcripts']}
        meta_sample['reference_file'] = sample['reference_file']
        meta_sample['filelist_file'] = sample['filelist_file']
        metadata_samples.append(meta_sample)

    with open(metadata_file, 'w') as f:
        json.dump(metadata_samples, f, indent=2)

    print(f"\n✓ Metadata saved: {metadata_file}")

    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    for sample in samples:
        print(f"\n{sample['name'].upper()}:")
        print(f"  Target: {sample['target_duration']}s ({sample['target_duration']/60:.1f} min)")
        print(f"  Actual: {sample['actual_duration']:.1f}s ({sample['actual_duration']/60:.1f} min)")
        print(f"  Files: {sample['num_files']}")
        print(f"  Words: {sample['total_words']}")
        print(f"  Reference: {sample['reference_file']}")
        print(f"  File list: {sample['filelist_file']}")

    print("\n" + "=" * 80)
    print("NEXT STEP: COMBINE AUDIO FILES")
    print("=" * 80)
    print("\nRun the following to combine audio files:")
    print()

    for sample in samples:
        output_audio = f"test_data/audio_{sample['name']}.wav"
        print(f"# Create {sample['name']} audio ({sample['actual_duration']/60:.1f} min)")
        print(f"ffmpeg -f concat -safe 0 -i {sample['filelist_file']} \\")
        print(f"  -ar 16000 -ac 1 {output_audio}")
        print()

    print("Or use the helper script:")
    print("  python3 combine_librispeech_audio.py")
    print()

    return 0

if __name__ == '__main__':
    sys.exit(main())
