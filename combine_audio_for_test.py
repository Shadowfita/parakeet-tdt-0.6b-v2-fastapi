#!/usr/bin/env python3
"""
Combine audio files for testing.

This script reads the file lists created by prepare_test_data.py and
combines audio files using ffmpeg.
"""

import os
import sys
import json
import subprocess
from pathlib import Path

def combine_audio(filelist_path, output_path, description):
    """
    Combine audio files using ffmpeg.

    Args:
        filelist_path: Path to file containing list of audio files
        output_path: Output audio file path
        description: Description for progress display
    """
    print(f"\n{description}")
    print(f"  Input: {filelist_path}")
    print(f"  Output: {output_path}")

    if not Path(filelist_path).exists():
        print(f"  ✗ File list not found: {filelist_path}")
        return False

    # Check if output already exists
    if Path(output_path).exists():
        print(f"  ! Output file already exists, will overwrite")

    # Run ffmpeg
    cmd = [
        'ffmpeg',
        '-f', 'concat',
        '-safe', '0',
        '-i', filelist_path,
        '-ar', '16000',  # 16kHz sample rate
        '-ac', '1',       # Mono
        '-y',             # Overwrite output
        output_path
    ]

    try:
        print(f"  Running ffmpeg...")
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )
        print(f"  ✓ Audio file created successfully")

        # Get duration
        duration_cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            output_path
        ]
        duration_result = subprocess.run(duration_cmd, capture_output=True, text=True)
        if duration_result.returncode == 0:
            duration = float(duration_result.stdout.strip())
            minutes = duration / 60
            print(f"  Duration: {duration:.1f}s ({minutes:.1f} minutes)")

        return True

    except subprocess.CalledProcessError as e:
        print(f"  ✗ Failed to combine audio files")
        print(f"  Error: {e.stderr}")
        return False
    except FileNotFoundError:
        print(f"  ✗ ffmpeg not found. Please install ffmpeg:")
        print(f"     Ubuntu/Debian: sudo apt-get install ffmpeg")
        print(f"     macOS: brew install ffmpeg")
        print(f"     Windows: Download from https://ffmpeg.org/")
        return False

def main():
    print("=" * 80)
    print("COMBINING AUDIO FILES FOR TESTING")
    print("=" * 80)

    # Check if test data exists
    test_dir = Path("test_data")
    if not test_dir.exists():
        print("\n✗ test_data directory not found")
        print("Please run prepare_test_data.py first")
        return 1

    # Load metadata
    metadata_file = test_dir / "test_data_info.json"
    if not metadata_file.exists():
        print("\n✗ Test data metadata not found")
        print("Please run prepare_test_data.py first")
        return 1

    with open(metadata_file, 'r') as f:
        test_samples = json.load(f)

    print(f"\nFound {len(test_samples)} test samples")

    # Combine audio for each sample
    success_count = 0
    for sample in test_samples:
        name = sample['name']
        filelist = sample['filelist']
        output_file = test_dir / f"audio_{name}.wav"

        if combine_audio(filelist, str(output_file), f"Creating {name} audio"):
            sample['audio_file'] = str(output_file)
            success_count += 1

    print("\n" + "=" * 80)
    print(f"COMPLETED: {success_count}/{len(test_samples)} audio files created")
    print("=" * 80)

    if success_count > 0:
        print("\n✓ You can now run evaluations:")
        for sample in test_samples:
            if 'audio_file' in sample:
                print(f"\n  {sample['name'].upper()} test ({sample['description']}):")
                print(f"    python evaluate_asr.py \\")
                print(f"      --audio {sample['audio_file']} \\")
                print(f"      --reference {sample['reference_file']} \\")
                print(f"      --output results_{sample['name']}.json")

    return 0 if success_count > 0 else 1

if __name__ == '__main__':
    sys.exit(main())
