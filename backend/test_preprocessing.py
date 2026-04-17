"""Test script for the enhanced preprocessing pipeline."""

import os
import sys
import json
import asyncio
import argparse

from app.services import DataPreprocessor, get_inference_service
from app.utils import get_logger

logger = get_logger(__name__)


def save_jsonl(data: list, filepath: str):
    """Save list of dicts as JSONL."""
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    logger.info(f"Saved {len(data)} records to {filepath}")


async def main():
    parser = argparse.ArgumentParser(description="Test enhanced preprocessing pipeline")
    parser.add_argument("file_path", help="Path to the raw training text file")
    parser.add_argument("--output-dir", default="./test_output", help="Directory to save train.jsonl and val.jsonl")
    parser.add_argument("--style", default="鲁迅风格", help="Target style name")
    parser.add_argument("--chunk-size", type=int, default=1024, help="Semantic chunk target length")
    parser.add_argument("--chunk-overlap", type=int, default=256, help="Chunk overlap")
    parser.add_argument("--cache-dir", default="./cache/preprocess", help="Cache directory for preprocessing results")
    args = parser.parse_args()
    print(args, end='\n')

    if not os.path.exists(args.file_path):
        logger.error(f"File not found: {args.file_path}")
        sys.exit(1)

    with open(args.file_path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    # logger.info(f"Read {len(raw_text)} chars from {args.file_path}")
    # print(raw_text, end='\n')

    style_config = {
        "target_style": f"{args.style}",
        "style_name": args.style,
        "style_description": "",
    }

    preprocessor = DataPreprocessor(style_config=style_config, cache_dir=args.cache_dir)
    inference_service = get_inference_service()

    result = await preprocessor.process(
        raw_text=raw_text,
        inference_service=inference_service,
        target_length=args.chunk_size,
        overlap=args.chunk_overlap,
        train_ratio=0.95,
    )

    train_data = result["train_data"]
    val_data = result["val_data"]
    metadata = result["metadata"]

    print(train_data, end='\n\n')
    print(val_data, end='\n')

    train_path = os.path.join(args.output_dir, "train.jsonl")
    val_path = os.path.join(args.output_dir, "val.jsonl")
    meta_path = os.path.join(args.output_dir, "metadata.json")

    save_jsonl(train_data, train_path)
    save_jsonl(val_data, val_path)

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved metadata to {meta_path}")

    logger.info("=" * 60)
    logger.info("Preprocessing complete")
    logger.info(f"  - Language: {metadata['language']}")
    logger.info(f"  - Chunks: {metadata['chunk_count']}")
    logger.info(f"  - Sentences: {metadata['sentence_count']}")
    logger.info(f"  - Continuation samples: {metadata['continuation_sample_count']}")
    logger.info(f"  - Style samples: {metadata['style_sample_count']}")
    logger.info(f"  - Total samples: {metadata['sample_count']}")
    logger.info(f"  - Valid samples: {metadata['valid_samples']}")
    logger.info(f"  - Train samples: {len(train_data)}")
    logger.info(f"  - Val samples: {len(val_data)}")
    logger.info(f"  - Avg length: {metadata['avg_length']:.0f} chars")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
