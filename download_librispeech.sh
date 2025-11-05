#!/bin/bash
# Download LibriSpeech dataset from alternative mirrors

set -e

TEST_DIR="test_data"
mkdir -p "$TEST_DIR"

echo "================================================================================"
echo "DOWNLOADING LIBRISPEECH DATASET"
echo "================================================================================"
echo ""

# Try multiple mirror sources
MIRRORS=(
    "https://www.openslr.org/resources/12/dev-clean.tar.gz"
    "http://www.openslr.org/resources/12/dev-clean.tar.gz"
    "https://us.openslr.org/resources/12/dev-clean.tar.gz"
)

DATASET="dev-clean"
FILENAME="${DATASET}.tar.gz"
FILEPATH="$TEST_DIR/$FILENAME"

# Check if already downloaded
if [ -f "$FILEPATH" ]; then
    echo "✓ Dataset already downloaded: $FILEPATH"
    echo "  Size: $(du -h $FILEPATH | cut -f1)"
    echo ""
else
    echo "Downloading $DATASET dataset (~337MB)..."
    echo ""

    DOWNLOADED=false
    for MIRROR in "${MIRRORS[@]}"; do
        echo "Trying mirror: $MIRROR"

        if wget -c -O "$FILEPATH" "$MIRROR" 2>&1; then
            echo "✓ Download successful from: $MIRROR"
            DOWNLOADED=true
            break
        else
            echo "✗ Failed to download from: $MIRROR"
            rm -f "$FILEPATH"
        fi
    done

    if [ "$DOWNLOADED" = false ]; then
        echo ""
        echo "✗ All mirrors failed. Trying with curl..."

        for MIRROR in "${MIRRORS[@]}"; do
            echo "Trying with curl: $MIRROR"

            if curl -C - -o "$FILEPATH" -L "$MIRROR"; then
                echo "✓ Download successful with curl"
                DOWNLOADED=true
                break
            else
                echo "✗ Failed with curl"
                rm -f "$FILEPATH"
            fi
        done
    fi

    if [ "$DOWNLOADED" = false ]; then
        echo ""
        echo "================================================================================"
        echo "DOWNLOAD FAILED"
        echo "================================================================================"
        echo ""
        echo "All automatic download methods failed. Please download manually:"
        echo ""
        echo "1. Visit: https://www.openslr.org/12/"
        echo "2. Download: dev-clean.tar.gz (~337MB)"
        echo "3. Place in: $TEST_DIR/"
        echo ""
        exit 1
    fi
fi

# Extract dataset
echo ""
echo "================================================================================"
echo "EXTRACTING DATASET"
echo "================================================================================"
echo ""

if [ -d "$TEST_DIR/LibriSpeech" ]; then
    echo "✓ Dataset already extracted: $TEST_DIR/LibriSpeech"
else
    echo "Extracting $FILEPATH..."
    tar -xzf "$FILEPATH" -C "$TEST_DIR"
    echo "✓ Extraction complete"
fi

echo ""
echo "================================================================================"
echo "DATASET READY"
echo "================================================================================"
echo ""

# Show dataset info
echo "Dataset location: $TEST_DIR/LibriSpeech/dev-clean"
echo "Audio files: $(find $TEST_DIR/LibriSpeech/dev-clean -name "*.flac" | wc -l)"
echo "Transcript files: $(find $TEST_DIR/LibriSpeech/dev-clean -name "*.txt" | wc -l)"
echo ""
echo "Next steps:"
echo "  1. Run: python3 process_librispeech.py"
echo "  2. Run: python3 combine_audio_for_test.py"
echo "  3. Run: python3 evaluate_asr.py --audio <file> --reference <file>"
echo ""
