#!/usr/bin/env python3
"""
Combine LibriSpeech audio files into test samples.

This script reads the file lists created by process_librispeech.py
and combines them using ffmpeg to create test audio files.
"""

import os
import sys
import json
import subprocess
from pathlib import Path

def check_ffmpeg():
    """Check if ffmpeg is available."""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def combine_audio(filelist_path, output_path, description, sample_rate=16000):
    """
    Combine audio files using ffmpeg.

    Args:
        filelist_path: Path to file containing list of audio files
        output_path: Output audio file path
        description: Description for progress display
        sample_rate: Target sample rate (default: 16000 Hz)
    """
    print(f"\n{description}")
    print(f"  Input list: {filelist_path}")
    print(f"  Output: {output_path}")

    if not Path(filelist_path).exists():
        print(f"  ✗ File list not found: {filelist_path}")
        return False

    # Check if output already exists
    if Path(output_path).exists():
        size_mb = Path(output_path).stat().st_size / (1024 * 1024)
        print(f"  ! Output file already exists ({size_mb:.1f} MB)")
        response = input("  Overwrite? (y/n): ")
        if response.lower() != 'y':
            print(f"  Skipped")
            return True

    # Run ffmpeg
    cmd = [
        'ffmpeg',
        '-f', 'concat',
        '-safe', '0',
        '-i', filelist_path,
        '-ar', str(sample_rate),  # Sample rate
        '-ac', '1',               # Mono
        '-y',                     # Overwrite output
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

        # Get file size
        size_mb = Path(output_path).stat().st_size / (1024 * 1024)
        print(f"  Size: {size_mb:.1f} MB")

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
            hours = duration / 3600
            if hours >= 1:
                print(f"  Duration: {duration:.1f}s ({hours:.2f} hours)")
            else:
                print(f"  Duration: {duration:.1f}s ({minutes:.1f} minutes)")

        return True

    except subprocess.CalledProcessError as e:
        print(f"  ✗ Failed to combine audio files")
        if e.stderr:
            print(f"  Error: {e.stderr[:200]}")
        return False

def main():
    print("=" * 80)
    print("LIBRISPEECH AUDIO COMBINER")
    print("=" * 80)
    print()

    # Check ffmpeg
    if not check_ffmpeg():
        print("✗ ffmpeg not found. Please install ffmpeg:")
        print("   Ubuntu/Debian: sudo apt-get install ffmpeg")
        print("   macOS: brew install ffmpeg")
        print("   Windows: Download from https://ffmpeg.org/")
        return 1

    print("✓ ffmpeg is available")
    print()

    # Check if metadata exists
    metadata_file = Path("test_data/librispeech_samples.json")

    if not metadata_file.exists():
        print(f"✗ Metadata file not found: {metadata_file}")
        print("\nPlease run: python3 process_librispeech.py first")
        return 1

    print(f"✓ Metadata file found: {metadata_file}")

    # Load metadata
    with open(metadata_file, 'r') as f:
        samples = json.load(f)

    print(f"✓ Found {len(samples)} samples to process")
    print()

    # Ask user which samples to create
    print("Available samples:")
    for i, sample in enumerate(samples, 1):
        print(f"  {i}. {sample['name']:10s} - {sample['description']:15s} "
              f"({sample['actual_duration']/60:.1f} min, {sample['num_files']} files)")

    print(f"  {len(samples)+1}. All samples")
    print()

    try:
        choice = input(f"Select sample to create (1-{len(samples)+1}, or 'q' to quit): ").strip()

        if choice.lower() == 'q':
            print("Cancelled")
            return 0

        choice_num = int(choice)

        if choice_num == len(samples) + 1:
            # Create all samples
            selected_samples = samples
        elif 1 <= choice_num <= len(samples):
            # Create specific sample
            selected_samples = [samples[choice_num - 1]]
        else:
            print(f"Invalid choice: {choice}")
            return 1

    except (ValueError, KeyboardInterrupt):
        print("\nCancelled")
        return 0

    # Create selected samples
    print("\n" + "=" * 80)
    print("CREATING AUDIO FILES")
    print("=" * 80)

    success_count = 0
    failed_samples = []

    for sample in selected_samples:
        name = sample['name']
        filelist = sample['filelist_file']
        output_file = f"test_data/audio_{name}.wav"

        description = f"Creating {name} audio ({sample['actual_duration']/60:.1f} min, {sample['num_files']} files)"

        if combine_audio(filelist, output_file, description):
            sample['audio_file'] = output_file
            success_count += 1
        else:
            failed_samples.append(name)

    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    print(f"\n✓ Successfully created: {success_count}/{len(selected_samples)} audio files")

    if failed_samples:
        print(f"✗ Failed: {', '.join(failed_samples)}")

    if success_count > 0:
        print("\n" + "=" * 80)
        print("NEXT STEP: RUN EVALUATION")
        print("=" * 80)
        print("\nYou can now run ASR evaluations:")
        print()

        for sample in selected_samples:
            if 'audio_file' in sample:
                print(f"# Evaluate {sample['name']} ({sample['actual_duration']/60:.1f} min)")
                print(f"python evaluate_asr.py \\")
                print(f"  --audio {sample['audio_file']} \\")
                print(f"  --reference {sample['reference_file']} \\")
                print(f"  --chunk-duration 30 \\")
                print(f"  --output results_{sample['name']}.json \\")
                print(f"  --device cuda")
                print()

        print("=" * 80)

    return 0 if success_count > 0 else 1

if __name__ == '__main__':
    sys.exit(main())
