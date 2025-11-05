#!/usr/bin/env python3
"""
ASR Accuracy Evaluation Script for Parakeet-TDT

This script evaluates the accuracy of ASR transcriptions by comparing them
with reference text. It calculates WER (Word Error Rate) and CER (Character
Error Rate) metrics.

Usage:
    python evaluate_asr.py --audio <audio_file> --reference <reference_text_file>
    python evaluate_asr.py --audio <audio_file> --reference <reference_text_file> --chunk-duration 30
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import re

import numpy as np
import torch
import torchaudio
from jiwer import wer, cer
from tqdm import tqdm

# Add the parakeet_service to the path
sys.path.insert(0, str(Path(__file__).parent))

from parakeet_service.model import ASRModel
from parakeet_service.audio import preprocess_audio
from parakeet_service.config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ASREvaluator:
    """Evaluates ASR performance against reference transcriptions."""

    def __init__(self, model: ASRModel, chunk_duration: float = 30.0):
        """
        Initialize the evaluator.

        Args:
            model: The ASR model to evaluate
            chunk_duration: Duration of audio chunks in seconds (for long files)
        """
        self.model = model
        self.chunk_duration = chunk_duration
        self.config = Config()

    def load_audio(self, audio_path: str) -> Tuple[torch.Tensor, int]:
        """
        Load audio file and preprocess it.

        Args:
            audio_path: Path to audio file

        Returns:
            Tuple of (audio tensor, sample rate)
        """
        logger.info(f"Loading audio from: {audio_path}")
        waveform, sample_rate = torchaudio.load(audio_path)

        # Preprocess audio (convert to mono, resample to 16kHz)
        waveform = preprocess_audio(waveform, sample_rate, self.config.target_sr)

        logger.info(f"Audio loaded: duration={waveform.shape[1]/self.config.target_sr:.2f}s, sr={self.config.target_sr}Hz")
        return waveform, self.config.target_sr

    def chunk_audio(self, waveform: torch.Tensor, sample_rate: int) -> List[torch.Tensor]:
        """
        Split audio into chunks for processing.

        Args:
            waveform: Audio waveform tensor
            sample_rate: Sample rate

        Returns:
            List of audio chunks
        """
        chunk_samples = int(self.chunk_duration * sample_rate)
        total_samples = waveform.shape[1]

        chunks = []
        for start in range(0, total_samples, chunk_samples):
            end = min(start + chunk_samples, total_samples)
            chunk = waveform[:, start:end]
            chunks.append(chunk)

        logger.info(f"Audio split into {len(chunks)} chunks of ~{self.chunk_duration}s each")
        return chunks

    def transcribe_audio(self, audio_path: str) -> str:
        """
        Transcribe an audio file.

        Args:
            audio_path: Path to audio file

        Returns:
            Transcribed text
        """
        waveform, sample_rate = self.load_audio(audio_path)

        # Check if we need to chunk the audio
        duration = waveform.shape[1] / sample_rate

        if duration <= self.chunk_duration:
            # Process as single chunk
            logger.info("Processing audio as single chunk")
            result = self.model.transcribe(waveform.numpy(), sample_rate)
            return result['text']
        else:
            # Process in chunks
            logger.info(f"Processing audio in chunks (total duration: {duration:.2f}s)")
            chunks = self.chunk_audio(waveform, sample_rate)

            transcriptions = []
            for i, chunk in enumerate(tqdm(chunks, desc="Transcribing chunks")):
                result = self.model.transcribe(chunk.numpy(), sample_rate)
                transcriptions.append(result['text'])

            # Combine transcriptions
            full_transcription = ' '.join(transcriptions)
            return full_transcription

    def normalize_text(self, text: str) -> str:
        """
        Normalize text for comparison.

        Args:
            text: Input text

        Returns:
            Normalized text
        """
        # Convert to lowercase
        text = text.lower()

        # Remove extra whitespace
        text = ' '.join(text.split())

        # Remove punctuation (optional, can be configured)
        # text = re.sub(r'[^\w\s]', '', text)

        return text.strip()

    def calculate_metrics(self, hypothesis: str, reference: str) -> Dict[str, float]:
        """
        Calculate WER and CER metrics.

        Args:
            hypothesis: ASR transcription
            reference: Ground truth text

        Returns:
            Dictionary with metrics
        """
        # Normalize texts
        hypothesis_norm = self.normalize_text(hypothesis)
        reference_norm = self.normalize_text(reference)

        # Calculate WER (Word Error Rate)
        word_error_rate = wer(reference_norm, hypothesis_norm)

        # Calculate CER (Character Error Rate)
        char_error_rate = cer(reference_norm, hypothesis_norm)

        # Calculate accuracy
        word_accuracy = (1 - word_error_rate) * 100
        char_accuracy = (1 - char_error_rate) * 100

        # Count words
        ref_words = len(reference_norm.split())
        hyp_words = len(hypothesis_norm.split())

        metrics = {
            'wer': word_error_rate * 100,  # Convert to percentage
            'cer': char_error_rate * 100,  # Convert to percentage
            'word_accuracy': word_accuracy,
            'char_accuracy': char_accuracy,
            'reference_words': ref_words,
            'hypothesis_words': hyp_words,
        }

        return metrics

    def evaluate(self, audio_path: str, reference_text: str) -> Dict:
        """
        Evaluate ASR performance.

        Args:
            audio_path: Path to audio file
            reference_text: Ground truth transcription

        Returns:
            Dictionary with evaluation results
        """
        logger.info("=" * 80)
        logger.info("Starting ASR Evaluation")
        logger.info("=" * 80)

        # Transcribe audio
        start_time = time.time()
        hypothesis = self.transcribe_audio(audio_path)
        transcription_time = time.time() - start_time

        logger.info(f"\nTranscription completed in {transcription_time:.2f}s")

        # Calculate metrics
        metrics = self.calculate_metrics(hypothesis, reference_text)

        # Calculate RTF (Real-Time Factor)
        waveform, _ = self.load_audio(audio_path)
        audio_duration = waveform.shape[1] / self.config.target_sr
        rtf = transcription_time / audio_duration

        results = {
            'audio_path': audio_path,
            'audio_duration': audio_duration,
            'transcription_time': transcription_time,
            'rtf': rtf,
            'hypothesis': hypothesis,
            'reference': reference_text,
            'metrics': metrics,
        }

        return results

    def print_results(self, results: Dict):
        """Print evaluation results in a formatted way."""
        print("\n" + "=" * 80)
        print("ASR EVALUATION RESULTS")
        print("=" * 80)

        print(f"\n📁 Audio File: {results['audio_path']}")
        print(f"⏱️  Audio Duration: {results['audio_duration']:.2f}s ({results['audio_duration']/60:.2f} minutes)")
        print(f"⚡ Transcription Time: {results['transcription_time']:.2f}s")
        print(f"🚀 Real-Time Factor (RTF): {results['rtf']:.4f}x")

        print("\n" + "-" * 80)
        print("ACCURACY METRICS")
        print("-" * 80)

        metrics = results['metrics']
        print(f"📊 Word Error Rate (WER): {metrics['wer']:.2f}%")
        print(f"📊 Character Error Rate (CER): {metrics['cer']:.2f}%")
        print(f"✅ Word Accuracy: {metrics['word_accuracy']:.2f}%")
        print(f"✅ Character Accuracy: {metrics['char_accuracy']:.2f}%")

        print("\n" + "-" * 80)
        print("TEXT COMPARISON")
        print("-" * 80)

        print(f"\n📝 Reference ({metrics['reference_words']} words):")
        print(f"   {results['reference'][:200]}{'...' if len(results['reference']) > 200 else ''}")

        print(f"\n🎤 Hypothesis ({metrics['hypothesis_words']} words):")
        print(f"   {results['hypothesis'][:200]}{'...' if len(results['hypothesis']) > 200 else ''}")

        print("\n" + "=" * 80)

    def save_results(self, results: Dict, output_path: str):
        """
        Save evaluation results to a JSON file.

        Args:
            results: Evaluation results
            output_path: Path to output file
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.info(f"Results saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Evaluate ASR accuracy against reference transcriptions'
    )
    parser.add_argument(
        '--audio',
        type=str,
        required=True,
        help='Path to audio file (wav, mp3, flac, etc.)'
    )
    parser.add_argument(
        '--reference',
        type=str,
        required=True,
        help='Path to reference transcription text file'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='evaluation_results.json',
        help='Path to output JSON file with results'
    )
    parser.add_argument(
        '--chunk-duration',
        type=float,
        default=30.0,
        help='Duration of audio chunks in seconds (default: 30.0)'
    )
    parser.add_argument(
        '--device',
        type=str,
        default='cuda' if torch.cuda.is_available() else 'cpu',
        help='Device to use for inference (cuda/cpu)'
    )

    args = parser.parse_args()

    # Validate inputs
    if not os.path.exists(args.audio):
        logger.error(f"Audio file not found: {args.audio}")
        sys.exit(1)

    if not os.path.exists(args.reference):
        logger.error(f"Reference file not found: {args.reference}")
        sys.exit(1)

    # Load reference text
    with open(args.reference, 'r', encoding='utf-8') as f:
        reference_text = f.read().strip()

    if not reference_text:
        logger.error("Reference text is empty")
        sys.exit(1)

    logger.info(f"Reference text loaded: {len(reference_text)} characters")

    # Initialize model
    logger.info(f"Initializing ASR model on device: {args.device}")
    config = Config()
    config.device = args.device
    model = ASRModel(config)

    # Initialize evaluator
    evaluator = ASREvaluator(model, chunk_duration=args.chunk_duration)

    # Run evaluation
    try:
        results = evaluator.evaluate(args.audio, reference_text)

        # Print results
        evaluator.print_results(results)

        # Save results
        evaluator.save_results(results, args.output)

    except Exception as e:
        logger.error(f"Evaluation failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
