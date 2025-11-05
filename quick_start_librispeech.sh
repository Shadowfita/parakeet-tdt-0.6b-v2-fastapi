#!/bin/bash
# Quick start script for LibriSpeech ASR evaluation

set -e

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BOLD}================================================================================"
echo "LIBRISPEECH ASR EVALUATION - QUICK START"
echo -e "================================================================================${NC}"
echo ""

# Function to print colored messages
print_step() {
    echo -e "\n${BOLD}${GREEN}>>> STEP $1: $2${NC}\n"
}

print_info() {
    echo -e "${YELLOW}ℹ  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check if running in correct directory
if [ ! -f "evaluate_asr.py" ]; then
    print_error "evaluate_asr.py not found. Please run this script from the project root."
    exit 1
fi

# Step 1: Download LibriSpeech
print_step 1 "Downloading LibriSpeech Dataset"

if [ -f "test_data/dev-clean.tar.gz" ]; then
    print_info "Dataset already downloaded"
else
    print_info "This will download ~337MB of data"
    ./download_librispeech.sh || {
        print_error "Download failed. Please check LIBRISPEECH_GUIDE.md for manual download instructions"
        exit 1
    }
fi

# Check if extracted
if [ ! -d "test_data/LibriSpeech/dev-clean" ]; then
    print_error "LibriSpeech data not found after download"
    exit 1
fi

print_success "LibriSpeech dataset ready"

# Step 2: Process LibriSpeech
print_step 2 "Processing LibriSpeech Data"

if [ -f "test_data/librispeech_samples.json" ]; then
    print_info "LibriSpeech already processed"
else
    python3 process_librispeech.py || {
        print_error "Processing failed"
        exit 1
    }
fi

print_success "LibriSpeech data processed"

# Step 3: Ask user what to do
print_step 3 "Creating Test Audio"

echo "Available test samples:"
echo "  1. short   - ~5 minutes   (quick test)"
echo "  2. medium  - ~15 minutes  (moderate test)"
echo "  3. long    - ~30 minutes  (comprehensive test)"
echo "  4. xlarge  - ~1 hour      (extended test)"
echo "  5. 2hours  - ~2 hours     (full test)"
echo "  6. all     - Create all samples"
echo "  7. skip    - Skip audio creation (already created)"
echo ""

read -p "Select option (1-7): " CHOICE

case $CHOICE in
    1|2|3|4|5)
        # Map choice to sample name
        declare -A SAMPLES
        SAMPLES[1]="short"
        SAMPLES[2]="medium"
        SAMPLES[3]="long"
        SAMPLES[4]="xlarge"
        SAMPLES[5]="2hours"

        SAMPLE_NAME="${SAMPLES[$CHOICE]}"

        print_info "Creating $SAMPLE_NAME audio sample..."

        # Read metadata
        if [ ! -f "test_data/librispeech_samples.json" ]; then
            print_error "Metadata file not found"
            exit 1
        fi

        # Get file list path
        FILELIST=$(jq -r ".[] | select(.name==\"$SAMPLE_NAME\") | .filelist_file" test_data/librispeech_samples.json)
        OUTPUT_AUDIO="test_data/audio_$SAMPLE_NAME.wav"

        if [ -f "$OUTPUT_AUDIO" ]; then
            print_info "Audio file already exists: $OUTPUT_AUDIO"
        else
            print_info "Combining audio files with ffmpeg..."
            ffmpeg -f concat -safe 0 -i "$FILELIST" \
                -ar 16000 -ac 1 -y "$OUTPUT_AUDIO" 2>&1 | grep -E "(Duration|size=)" || true

            if [ -f "$OUTPUT_AUDIO" ]; then
                SIZE=$(du -h "$OUTPUT_AUDIO" | cut -f1)
                print_success "Audio created: $OUTPUT_AUDIO ($SIZE)"
            else
                print_error "Failed to create audio file"
                exit 1
            fi
        fi

        # Step 4: Run evaluation
        print_step 4 "Running ASR Evaluation"

        REFERENCE_FILE="test_data/reference_$SAMPLE_NAME.txt"
        OUTPUT_RESULTS="results_$SAMPLE_NAME.json"

        print_info "Evaluating $SAMPLE_NAME sample..."
        print_info "This may take a few minutes depending on your hardware"
        echo ""

        python3 evaluate_asr.py \
            --audio "$OUTPUT_AUDIO" \
            --reference "$REFERENCE_FILE" \
            --chunk-duration 30 \
            --output "$OUTPUT_RESULTS" \
            --device cuda 2>&1 || {
                print_error "Evaluation failed. Try with CPU: --device cpu"
                exit 1
            }

        # Step 5: Show results
        print_step 5 "Evaluation Results"

        if [ -f "$OUTPUT_RESULTS" ]; then
            print_success "Results saved to: $OUTPUT_RESULTS"
            echo ""

            # Extract and display key metrics
            WER=$(jq -r '.metrics.wer' "$OUTPUT_RESULTS")
            CER=$(jq -r '.metrics.cer' "$OUTPUT_RESULTS")
            DURATION=$(jq -r '.audio_duration' "$OUTPUT_RESULTS")
            PROC_TIME=$(jq -r '.transcription_time' "$OUTPUT_RESULTS")
            RTF=$(jq -r '.rtf' "$OUTPUT_RESULTS")
            MINUTES=$(echo "scale=1; $DURATION / 60" | bc)

            echo -e "${BOLD}Summary:${NC}"
            echo "  Audio Duration: ${MINUTES} minutes"
            echo "  Processing Time: ${PROC_TIME}s"
            echo "  Real-Time Factor: ${RTF}x"
            echo ""
            echo -e "${BOLD}Accuracy Metrics:${NC}"
            echo "  Word Error Rate (WER): ${WER}%"
            echo "  Character Error Rate (CER): ${CER}%"
            echo ""

            # Interpret WER
            WER_INT=$(echo "$WER / 1" | bc)
            if [ "$WER_INT" -lt 5 ]; then
                echo -e "  ${GREEN}Excellent transcription quality!${NC}"
            elif [ "$WER_INT" -lt 10 ]; then
                echo -e "  ${GREEN}Good transcription quality${NC}"
            elif [ "$WER_INT" -lt 15 ]; then
                echo -e "  ${YELLOW}Acceptable transcription quality${NC}"
            else
                echo -e "  ${YELLOW}Transcription needs improvement${NC}"
            fi

            echo ""
            print_info "Full results: cat $OUTPUT_RESULTS | jq"
        else
            print_error "Results file not found"
            exit 1
        fi
        ;;

    6)
        print_info "Creating all audio samples..."
        echo "yes" | python3 combine_librispeech_audio.py << EOF
6
EOF
        print_success "All audio samples created"
        print_info "Run individual evaluations manually or use batch script"
        ;;

    7)
        print_info "Skipping audio creation"
        ;;

    *)
        print_error "Invalid choice"
        exit 1
        ;;
esac

echo ""
print_success "Quick start completed!"
echo ""
echo -e "${BOLD}Next steps:${NC}"
echo "  • View results: cat results_*.json | jq"
echo "  • Run more evaluations: python3 evaluate_asr.py --help"
echo "  • Read full guide: cat LIBRISPEECH_GUIDE.md"
echo ""
