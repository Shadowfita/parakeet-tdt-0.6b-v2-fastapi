#!/usr/bin/env python3
"""
Prepare test data for ASR evaluation.

This script downloads sample audio from LibriSpeech dataset and prepares
reference transcriptions for testing the ASR evaluation pipeline.
"""

import os
import sys
import urllib.request
import tarfile
import json
from pathlib import Path

def download_file(url, destination, description="Downloading"):
    """Download a file with progress indication."""
    print(f"{description}...")
    print(f"  URL: {url}")
    print(f"  Destination: {destination}")

    def progress_hook(count, block_size, total_size):
        percent = int(count * block_size * 100 / total_size)
        sys.stdout.write(f"\r  Progress: {percent}%")
        sys.stdout.flush()

    try:
        urllib.request.urlretrieve(url, destination, progress_hook)
        print("\n  ✓ Download complete")
        return True
    except Exception as e:
        print(f"\n  ✗ Download failed: {e}")
        return False

def extract_tar(tar_path, extract_to):
    """Extract tar.gz file."""
    print(f"Extracting {tar_path}...")
    try:
        with tarfile.open(tar_path, 'r:gz') as tar:
            tar.extractall(extract_to)
        print("  ✓ Extraction complete")
        return True
    except Exception as e:
        print(f"  ✗ Extraction failed: {e}")
        return False

def find_flac_files(directory):
    """Find all FLAC files in directory."""
    return list(Path(directory).rglob("*.flac"))

def find_trans_files(directory):
    """Find all transcript files."""
    return list(Path(directory).rglob("*.trans.txt"))

def parse_librispeech_trans(trans_file):
    """Parse LibriSpeech transcript file."""
    transcripts = {}
    with open(trans_file, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split(' ', 1)
            if len(parts) == 2:
                file_id, text = parts
                transcripts[file_id] = text
    return transcripts

def combine_audio_files(audio_files, output_file, target_duration=None):
    """
    Combine multiple audio files into one long file.

    Args:
        audio_files: List of audio file paths
        output_file: Output file path
        target_duration: Target duration in seconds (optional)
    """
    import subprocess

    # Create a file list for ffmpeg
    list_file = output_file.replace('.wav', '_list.txt')
    with open(list_file, 'w') as f:
        for audio_file in audio_files:
            f.write(f"file '{audio_file}'\n")

    # Combine audio files
    cmd = [
        'ffmpeg', '-f', 'concat', '-safe', '0',
        '-i', list_file,
        '-ar', '16000',  # 16kHz sample rate
        '-ac', '1',       # Mono
        '-y',             # Overwrite output
        output_file
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True)
        os.remove(list_file)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error combining audio: {e}")
        return False

def prepare_librispeech_sample():
    """Download and prepare LibriSpeech test sample."""

    test_dir = Path("test_data")
    test_dir.mkdir(exist_ok=True)

    print("=" * 80)
    print("PREPARING LIBRISPEECH TEST DATA")
    print("=" * 80)
    print()

    # Download LibriSpeech test-clean sample (small subset)
    # Using dev-clean which is smaller (~350MB)
    dataset_url = "http://www.openslr.org/resources/12/dev-clean.tar.gz"
    dataset_tar = test_dir / "dev-clean.tar.gz"

    if not dataset_tar.exists():
        if not download_file(dataset_url, dataset_tar, "Downloading LibriSpeech dev-clean"):
            return False
    else:
        print(f"Dataset already downloaded: {dataset_tar}")

    # Extract dataset
    extract_dir = test_dir / "LibriSpeech"
    if not extract_dir.exists():
        if not extract_tar(dataset_tar, test_dir):
            return False
    else:
        print(f"Dataset already extracted: {extract_dir}")

    # Find audio files
    print("\nSearching for audio files...")
    audio_files = find_flac_files(extract_dir)
    print(f"  Found {len(audio_files)} audio files")

    # Find transcripts
    print("Searching for transcripts...")
    trans_files = find_trans_files(extract_dir)
    print(f"  Found {len(trans_files)} transcript files")

    # Parse all transcripts
    print("\nParsing transcripts...")
    all_transcripts = {}
    for trans_file in trans_files:
        transcripts = parse_librispeech_trans(trans_file)
        all_transcripts.update(transcripts)
    print(f"  Parsed {len(all_transcripts)} transcripts")

    # Select files to create test samples
    print("\nCreating test samples...")

    # Sort audio files by size to get consistent selection
    audio_files_sorted = sorted(audio_files, key=lambda x: x.stat().st_size)

    # Create different duration test samples
    test_samples = [
        ("short", 10, "~5 minutes"),
        ("medium", 30, "~15 minutes"),
        ("long", 100, "~50 minutes"),
    ]

    results = []

    for name, num_files, desc in test_samples:
        print(f"\n  Creating {name} test sample ({desc})...")

        selected_files = audio_files_sorted[:num_files]

        # Collect transcripts for selected files
        combined_text = []
        actual_files = []

        for audio_file in selected_files:
            file_id = audio_file.stem
            if file_id in all_transcripts:
                combined_text.append(all_transcripts[file_id])
                actual_files.append(str(audio_file))

        if not actual_files:
            print(f"    ✗ No matching transcripts found")
            continue

        # Save reference text
        ref_file = test_dir / f"reference_{name}.txt"
        with open(ref_file, 'w', encoding='utf-8') as f:
            f.write(' '.join(combined_text))

        # Save file list
        filelist_file = test_dir / f"filelist_{name}.txt"
        with open(filelist_file, 'w', encoding='utf-8') as f:
            for audio_file in actual_files:
                f.write(f"file '{audio_file}'\n")

        print(f"    ✓ Reference text: {ref_file}")
        print(f"    ✓ Audio files: {len(actual_files)}")
        print(f"    ✓ Total words: {len(' '.join(combined_text).split())}")

        results.append({
            "name": name,
            "description": desc,
            "audio_files": actual_files,
            "reference_file": str(ref_file),
            "filelist": str(filelist_file),
            "num_files": len(actual_files),
            "num_words": len(' '.join(combined_text).split())
        })

    # Save metadata
    metadata_file = test_dir / "test_data_info.json"
    with open(metadata_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✓ Test data prepared successfully!")
    print(f"✓ Metadata saved to: {metadata_file}")

    return results

def create_combined_audio_instructions():
    """Create instructions for combining audio files."""

    instructions = """
================================================================================
NEXT STEPS: Creating Combined Audio Files
================================================================================

The test data has been prepared with separate audio files and reference texts.
To evaluate long audio (e.g., 2 hours), you need to combine multiple files.

Option 1: Use ffmpeg directly
------------------------------
# Combine files for short test (~5 minutes)
ffmpeg -f concat -safe 0 -i test_data/filelist_short.txt \\
  -ar 16000 -ac 1 test_data/audio_short.wav

# Combine files for medium test (~15 minutes)
ffmpeg -f concat -safe 0 -i test_data/filelist_medium.txt \\
  -ar 16000 -ac 1 test_data/audio_medium.wav

# Combine files for long test (~50 minutes)
ffmpeg -f concat -safe 0 -i test_data/filelist_long.txt \\
  -ar 16000 -ac 1 test_data/audio_long.wav

Option 2: Use the provided helper script
-----------------------------------------
python combine_audio_for_test.py

Then run evaluation:
--------------------
# Short test
python evaluate_asr.py \\
  --audio test_data/audio_short.wav \\
  --reference test_data/reference_short.txt \\
  --output results_short.json

# Medium test
python evaluate_asr.py \\
  --audio test_data/audio_medium.wav \\
  --reference test_data/reference_medium.txt \\
  --output results_medium.json

# Long test
python evaluate_asr.py \\
  --audio test_data/audio_long.wav \\
  --reference test_data/reference_long.txt \\
  --output results_long.json

================================================================================
"""

    print(instructions)

    # Save to file
    with open('test_data/INSTRUCTIONS.txt', 'w') as f:
        f.write(instructions)

    print("Instructions saved to: test_data/INSTRUCTIONS.txt")

def main():
    print("Parakeet ASR Test Data Preparation")
    print()

    # Prepare LibriSpeech data
    results = prepare_librispeech_sample()

    if results:
        print("\n" + "=" * 80)
        print("TEST DATA SUMMARY")
        print("=" * 80)
        for item in results:
            print(f"\n{item['name'].upper()} ({item['description']}):")
            print(f"  Files: {item['num_files']}")
            print(f"  Words: {item['num_words']}")
            print(f"  Reference: {item['reference_file']}")
            print(f"  File list: {item['filelist']}")

        print()
        create_combined_audio_instructions()
    else:
        print("\n✗ Failed to prepare test data")
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())
