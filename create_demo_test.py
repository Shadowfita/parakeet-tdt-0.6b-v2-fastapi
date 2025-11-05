#!/usr/bin/env python3
"""
Create demo test data for ASR evaluation.

Since we can't download LibriSpeech data, this script creates a practical
demo using synthetic audio or guides users to use their own audio files.
"""

import os
import sys
import json
import subprocess
from pathlib import Path

def check_dependencies():
    """Check if required tools are available."""
    dependencies = {
        'ffmpeg': 'ffmpeg -version',
        'sox': 'sox --version',
    }

    available = {}
    for name, cmd in dependencies.items():
        try:
            subprocess.run(cmd.split(), capture_output=True, check=True)
            available[name] = True
            print(f"  ✓ {name} is available")
        except (subprocess.CalledProcessError, FileNotFoundError):
            available[name] = False
            print(f"  ✗ {name} is not available")

    return available

def create_sample_reference_texts():
    """Create sample reference texts for testing."""

    samples = {
        'sample1': """
The quick brown fox jumps over the lazy dog. This is a classic pangram
used to test keyboards and fonts. It contains every letter of the English
alphabet at least once. Many people use this sentence for typing practice
and font samples. The phrase has been around since at least the late
nineteenth century.
""".strip(),

        'sample2': """
Speech recognition technology has advanced significantly in recent years.
Modern systems use deep learning and neural networks to achieve high accuracy.
These systems can now understand natural language with remarkable precision.
Applications range from virtual assistants to medical transcription services.
The technology continues to improve with larger datasets and better models.
""".strip(),

        'sample3': """
Artificial intelligence is transforming many industries today. Machine learning
algorithms can now perform tasks that once required human intelligence. From
image recognition to language translation, AI systems are becoming increasingly
capable. However, there are still many challenges to overcome, including bias
in training data and the need for more interpretable models. Researchers are
working on making AI systems more robust and reliable.
""".strip(),
    }

    return samples

def create_test_structure():
    """Create test directory structure."""

    test_dir = Path("test_data")
    test_dir.mkdir(exist_ok=True)

    print("\n" + "=" * 80)
    print("CREATING DEMO TEST DATA")
    print("=" * 80)

    # Create sample reference texts
    print("\nCreating sample reference texts...")
    samples = create_sample_reference_texts()

    sample_info = []
    for name, text in samples.items():
        ref_file = test_dir / f"reference_{name}.txt"
        with open(ref_file, 'w', encoding='utf-8') as f:
            f.write(text)

        word_count = len(text.split())
        char_count = len(text)

        print(f"  ✓ {ref_file.name}")
        print(f"    Words: {word_count}, Characters: {char_count}")

        sample_info.append({
            'name': name,
            'reference_file': str(ref_file),
            'words': word_count,
            'characters': char_count,
            'text_preview': text[:100] + '...' if len(text) > 100 else text
        })

    # Save metadata
    metadata_file = test_dir / "demo_test_info.json"
    with open(metadata_file, 'w') as f:
        json.dump(sample_info, f, indent=2)

    print(f"\n✓ Metadata saved to: {metadata_file}")

    return sample_info

def create_instructions():
    """Create instructions for users."""

    instructions = """
================================================================================
DEMO TEST DATA CREATED
================================================================================

I've created sample reference texts for testing the ASR evaluation pipeline.

OPTION 1: Use Your Own Audio Files
-----------------------------------
If you have audio files to test:

1. Place your audio files in the test_data/ directory
2. Make sure you have corresponding reference text files
3. Run the evaluation:

   python evaluate_asr.py \\
     --audio test_data/your_audio.wav \\
     --reference test_data/reference_sample1.txt \\
     --output results.json

OPTION 2: Record Audio for the Reference Texts
-----------------------------------------------
You can record audio reading the reference texts:

1. Read one of the reference texts:
   - test_data/reference_sample1.txt
   - test_data/reference_sample2.txt
   - test_data/reference_sample3.txt

2. Save the recording as a WAV file in test_data/

3. Run the evaluation

OPTION 3: Use Text-to-Speech (if available)
--------------------------------------------
If you have TTS tools available (like espeak, pyttsx3, etc.):

# Example with espeak (if installed)
espeak -w test_data/audio_sample1.wav -f test_data/reference_sample1.txt

Then evaluate:
python evaluate_asr.py \\
  --audio test_data/audio_sample1.wav \\
  --reference test_data/reference_sample1.txt \\
  --output results_sample1.json

OPTION 4: Download Audio from Public Sources
---------------------------------------------
You can download audio files from:

1. Common Voice: https://commonvoice.mozilla.org/
   - Download validated audio files
   - Use the corresponding transcripts

2. YouTube with transcripts:
   - Download audio from educational videos with captions
   - Use the captions as reference text

3. Podcasts with transcripts:
   - Download podcast audio
   - Use their published transcripts

CREATING A 2-HOUR TEST AUDIO
-----------------------------
To create a long test audio (like 2 hours), you can:

1. Combine multiple audio files:

   # Create a file list
   cat > test_data/long_audio_list.txt << EOF
   file 'audio1.wav'
   file 'audio2.wav'
   file 'audio3.wav'
   ...
   EOF

   # Combine with ffmpeg
   ffmpeg -f concat -safe 0 -i test_data/long_audio_list.txt \\
     -ar 16000 -ac 1 test_data/audio_long_2hours.wav

2. Concatenate the reference texts in the same order

QUICK START FOR TESTING THE PIPELINE
-------------------------------------
To test the evaluation pipeline without real data:

1. Create a simple test audio:
   # Generate a tone (10 seconds)
   ffmpeg -f lavfi -i "sine=frequency=1000:duration=10" \\
     -ar 16000 -ac 1 test_data/test_tone.wav

2. Create a dummy reference:
   echo "This is a test audio file" > test_data/test_reference.txt

3. Run the evaluation (it will transcribe the tone, which won't match):
   python evaluate_asr.py \\
     --audio test_data/test_tone.wav \\
     --reference test_data/test_reference.txt \\
     --output test_results.json

   This tests that the pipeline works end-to-end.

RECOMMENDED APPROACH
--------------------
The most practical approach for testing:

1. Find a video or audio with accurate transcripts
2. Download the audio
3. Copy the transcript as reference text
4. Run the evaluation

Example sources:
- TED Talks (have transcripts)
- Audiobooks (have text)
- Educational videos with closed captions

================================================================================

For detailed evaluation documentation, see EVALUATION_GUIDE.md

================================================================================
"""

    print(instructions)

    instructions_file = Path("test_data/DEMO_INSTRUCTIONS.txt")
    with open(instructions_file, 'w') as f:
        f.write(instructions)

    print(f"Instructions saved to: {instructions_file}")

def create_simple_test_example():
    """Create a simple end-to-end test example."""

    print("\n" + "=" * 80)
    print("CREATING SIMPLE TEST EXAMPLE")
    print("=" * 80)

    # Check if ffmpeg is available
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        has_ffmpeg = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        has_ffmpeg = False
        print("\n✗ ffmpeg not available - skipping audio generation")
        return False

    if has_ffmpeg:
        print("\nGenerating test audio (10-second tone)...")
        test_audio = Path("test_data/test_tone.wav")

        cmd = [
            'ffmpeg', '-f', 'lavfi',
            '-i', 'sine=frequency=440:duration=10',
            '-ar', '16000',
            '-ac', '1',
            '-y',
            str(test_audio)
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True)
            print(f"  ✓ Test audio created: {test_audio}")

            # Create reference
            test_ref = Path("test_data/test_reference.txt")
            with open(test_ref, 'w') as f:
                f.write("This is a test audio file for pipeline verification")

            print(f"  ✓ Test reference created: {test_ref}")
            print("\nYou can test the pipeline with:")
            print(f"  python evaluate_asr.py \\")
            print(f"    --audio {test_audio} \\")
            print(f"    --reference {test_ref} \\")
            print(f"    --output test_results.json")

            return True

        except subprocess.CalledProcessError as e:
            print(f"  ✗ Failed to create test audio: {e}")
            return False

    return False

def main():
    print("Parakeet ASR Demo Test Data Creation")
    print()

    # Check dependencies
    print("Checking dependencies...")
    deps = check_dependencies()

    # Create test structure
    sample_info = create_test_structure()

    # Create simple test example
    create_simple_test_example()

    # Show instructions
    print()
    create_instructions()

    print("\n" + "=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print("""
1. Prepare your audio files (or download from suggested sources)
2. Place audio and reference text in test_data/
3. Run the evaluation script
4. Check the results

For a 2-hour audio test, you'll need to source appropriate audio data
from public datasets or your own recordings.
""")

    return 0

if __name__ == '__main__':
    sys.exit(main())
