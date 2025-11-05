#!/bin/bash
# Example script for evaluating ASR accuracy on a 2-hour audio file

set -e

echo "==================================================================="
echo "ASR Accuracy Evaluation Example"
echo "==================================================================="
echo ""

# Configuration
AUDIO_FILE="${1:-audio_2hours.wav}"
REFERENCE_FILE="${2:-reference_2hours.txt}"
OUTPUT_FILE="${3:-evaluation_results.json}"
CHUNK_DURATION="${4:-30}"
DEVICE="${5:-cuda}"

# Check if files exist
if [ ! -f "$AUDIO_FILE" ]; then
    echo "❌ Error: Audio file not found: $AUDIO_FILE"
    echo ""
    echo "Usage: $0 <audio_file> <reference_file> [output_file] [chunk_duration] [device]"
    echo ""
    echo "Example:"
    echo "  $0 audio.wav reference.txt results.json 30 cuda"
    echo ""
    echo "You need to provide:"
    echo "  1. Audio file (WAV, MP3, FLAC, etc.)"
    echo "  2. Reference text file (accurate transcription)"
    echo ""
    exit 1
fi

if [ ! -f "$REFERENCE_FILE" ]; then
    echo "❌ Error: Reference file not found: $REFERENCE_FILE"
    echo ""
    echo "The reference file should contain the accurate transcription of the audio."
    echo ""
    exit 1
fi

echo "📁 Audio file: $AUDIO_FILE"
echo "📝 Reference file: $REFERENCE_FILE"
echo "💾 Output file: $OUTPUT_FILE"
echo "⏱️  Chunk duration: ${CHUNK_DURATION}s"
echo "🖥️  Device: $DEVICE"
echo ""

# Check if dependencies are installed
echo "Checking dependencies..."
python3 -c "import jiwer, tqdm" 2>/dev/null || {
    echo "❌ Missing dependencies. Installing..."
    pip install jiwer tqdm
}

echo "✅ Dependencies OK"
echo ""

# Get audio file info
echo "Getting audio file information..."
DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$AUDIO_FILE" 2>/dev/null || echo "unknown")
if [ "$DURATION" != "unknown" ]; then
    MINUTES=$(echo "scale=2; $DURATION / 60" | bc)
    echo "  Duration: ${DURATION}s (${MINUTES} minutes)"
fi

# Get reference text info
REFERENCE_CHARS=$(wc -c < "$REFERENCE_FILE")
REFERENCE_WORDS=$(wc -w < "$REFERENCE_FILE")
echo "  Reference: $REFERENCE_WORDS words, $REFERENCE_CHARS characters"
echo ""

# Run evaluation
echo "==================================================================="
echo "Starting evaluation..."
echo "==================================================================="
echo ""

python3 evaluate_asr.py \
    --audio "$AUDIO_FILE" \
    --reference "$REFERENCE_FILE" \
    --output "$OUTPUT_FILE" \
    --chunk-duration "$CHUNK_DURATION" \
    --device "$DEVICE"

echo ""
echo "==================================================================="
echo "Evaluation completed!"
echo "==================================================================="
echo ""
echo "Results saved to: $OUTPUT_FILE"
echo ""
echo "To view the results:"
echo "  cat $OUTPUT_FILE | jq"
echo ""
echo "To extract specific metrics:"
echo "  cat $OUTPUT_FILE | jq '.metrics'"
echo ""
