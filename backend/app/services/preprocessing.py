"""Text preprocessing service for training data preparation."""

import re
from typing import List


class PreprocessingService:
    """Service for preprocessing training text data."""

    # Approximate tokens per character (rough estimate for CJK + English)
    CHARS_PER_TOKEN = 2.0

    def __init__(self):
        self.default_chunk_size = 512
        self.default_overlap = 128

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        return int(len(text) / self.CHARS_PER_TOKEN)

    def chunk_text(
        self,
        text: str,
        chunk_size: int = None,
        overlap: int = None,
    ) -> List[str]:
        """
        Split text into overlapping chunks.

        Args:
            text: Input text to chunk
            chunk_size: Target chunk size in tokens (default: 512)
            overlap: Overlap between chunks in tokens (default: 128)

        Returns:
            List of text chunks
        """
        chunk_size = chunk_size or self.default_chunk_size
        overlap = overlap or self.default_overlap

        # Convert token counts to character counts
        chunk_chars = int(chunk_size * self.CHARS_PER_TOKEN)
        overlap_chars = int(overlap * self.CHARS_PER_TOKEN)

        chunks = []
        start = 0
        text_len = len(text)

        while start < text_len:
            # Calculate end position
            end = min(start + chunk_chars, text_len)

            # Try to break at a sentence boundary
            if end < text_len:
                # Look for sentence endings (. ! ?)
                search_end = min(end + 50, text_len)
                search_text = text[end:search_end]
                sentence_end = re.search(r'[.!?。！？]+\s*', search_text)
                if sentence_end:
                    end += sentence_end.end()

            # Extract chunk
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # Move to next chunk with overlap
            start = end - overlap_chars if end < text_len else text_len

        return chunks

    def clean_text(self, text: str) -> str:
        """
        Basic text cleaning.

        TODO v0.2+: Add more sophisticated cleaning
        - Remove special characters
        - Normalize whitespace
        - Fix encoding issues
        """
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove control characters
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        return text.strip()

    def preprocess_training_text(
        self,
        text: str,
        chunk_size: int = None,
        overlap: int = None,
    ) -> dict:
        """
        Full preprocessing pipeline for training text.

        Args:
            text: Raw input text
            chunk_size: Target chunk size in tokens
            overlap: Overlap between chunks in tokens

        Returns:
            Dictionary with:
                - cleaned_text: Cleaned full text
                - chunks: List of text chunks
                - chunk_count: Number of chunks
                - estimated_tokens: Estimated total tokens
        """
        # Clean text
        cleaned = self.clean_text(text)

        # Chunk text
        chunks = self.chunk_text(cleaned, chunk_size, overlap)

        return {
            "cleaned_text": cleaned,
            "chunks": chunks,
            "chunk_count": len(chunks),
            "estimated_tokens": self.estimate_tokens(cleaned),
        }

    def format_for_training(self, chunks: List[str], target_style: str) -> List[dict]:
        """
        Format chunks for training.

        TODO v0.2+: Format as instruction-following dataset for QLoRA
        """
        formatted = []
        for chunk in chunks:
            formatted.append({
                "text": chunk,
                "target_style": target_style,
                # v0.2+: Add instruction templates
            })
        return formatted


# Global preprocessing service instance
preprocessing_service = PreprocessingService()
