#!/usr/bin/env python3
"""
Main entry point for Tibetan Translator v2 Pipeline

This module provides a command-line interface and usage examples for the
multi-level tree translation pipeline.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List

from .processors.pipeline import TranslationPipeline, process_multilevel_tree_file
from .models import MultiLevelTreeInput

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_llm_client():
    """
    Setup LLM client. This is a placeholder - users need to provide their own client.
    The client should have an `invoke` method that takes a prompt and returns a response
    with a `content` attribute.
    """
    # This is where users would configure their LLM client
    # For example, with LangChain:
    # from langchain_openai import ChatOpenAI
    # return ChatOpenAI(model="gpt-4", temperature=0)
    
    class MockLLMClient:
        """Mock LLM client for demonstration purposes."""
        def invoke(self, prompt):
            class MockResponse:
                content = '{"format_matched": true, "plaintext_translation": "Mock translation", "translation": "Mock scholarly translation"}'
            return MockResponse()
    
    logger.warning("Using mock LLM client. Please configure a real LLM client for actual usage.")
    return MockLLMClient()


def process_single_file(
    input_file: str,
    target_languages: List[str],
    source_text: str = None,
    output_dir: str = "output"
):
    """
    Process a single multi-level-tree.jsonl file.
    
    Args:
        input_file: Path to input JSONL file
        target_languages: List of target languages
        source_text: Optional source text
        output_dir: Output directory
    """
    logger.info(f"Processing file: {input_file}")
    logger.info(f"Target languages: {target_languages}")
    
    try:
        # Setup LLM client (users should replace this with their own)
        llm_client = setup_llm_client()
        
        # Process the file
        result = process_multilevel_tree_file(
            input_file=input_file,
            target_languages=target_languages,
            llm_client=llm_client,
            source_text=source_text,
            output_dir=output_dir
        )
        
        logger.info(f"Processing completed successfully!")
        logger.info(f"Request ID: {result.request_id}")
        logger.info(f"Translations generated: {len([t for t in result.translations.values() if t])}")
        logger.info(f"Total glossary entries: {sum(len(g) for g in result.glossaries.values())}")
        
        return result
        
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        raise


def example_usage():
    """
    Demonstrate example usage of the v2 pipeline.
    """
    print("Tibetan Translator v2 Pipeline - Example Usage")
    print("=" * 50)
    
    # Example 1: Create input programmatically
    print("\nExample 1: Creating input programmatically")
    
    example_input = MultiLevelTreeInput(
        glossary="Sample glossary text with word-by-word translations",
        ucca_formatted="Sample UCCA linguistic analysis text",
        multilevel_summary={
            "main_theme": "Buddhist philosophy",
            "key_concepts": {
                "primary": "meditation",
                "secondary": ["mindfulness", "wisdom"]
            },
            "structure": {
                "introduction": "Opening statements",
                "body": "Main teachings", 
                "conclusion": "Final remarks"
            }
        }
    )
    
    print("Created MultiLevelTreeInput with:")
    print(f"- Glossary: {len(example_input.glossary)} characters")
    print(f"- UCCA formatted: {len(example_input.ucca_formatted)} characters") 
    print(f"- Multilevel summary: {len(example_input.multilevel_summary)} keys")
    
    # Show how JSON is converted to text
    print("\nMultilevel summary as text:")
    print(example_input.get_multilevel_summary_text())
    
    # Example 2: Using the pipeline
    print("\nExample 2: Using the pipeline")
    
    llm_client = setup_llm_client()
    pipeline = TranslationPipeline(llm_client=llm_client)
    
    try:
        result = pipeline.process_input_data(
            input_data=example_input,
            target_languages=["English", "Spanish"],
            source_text="Sample Tibetan source text"
        )
        
        print(f"Processing completed with request ID: {result.request_id}")
        print(f"Languages processed: {list(result.translations.keys())}")
        
    except Exception as e:
        print(f"Example processing failed: {e}")


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Tibetan Translator v2 Pipeline - Multi-level Tree Format Processor"
    )
    
    parser.add_argument(
        "input_file",
        help="Path to multi-level-tree.jsonl input file"
    )
    
    parser.add_argument(
        "--languages", "-l",
        nargs="+",
        default=["English"],
        help="Target languages for translation (default: English)"
    )
    
    parser.add_argument(
        "--source-text", "-s",
        help="Optional source text file path"
    )
    
    parser.add_argument(
        "--output-dir", "-o",
        default="output",
        help="Output directory (default: output)"
    )
    
    parser.add_argument(
        "--example",
        action="store_true",
        help="Show example usage instead of processing"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if args.example:
        example_usage()
        return
    
    # Validate input file
    if not Path(args.input_file).exists():
        logger.error(f"Input file not found: {args.input_file}")
        sys.exit(1)
    
    # Load source text if provided
    source_text = None
    if args.source_text:
        if not Path(args.source_text).exists():
            logger.error(f"Source text file not found: {args.source_text}")
            sys.exit(1)
        
        with open(args.source_text, 'r', encoding='utf-8') as f:
            source_text = f.read()
    
    # Process the file
    try:
        result = process_single_file(
            input_file=args.input_file,
            target_languages=args.languages,
            source_text=source_text,
            output_dir=args.output_dir
        )
        
        print(f"\nProcessing completed successfully!")
        print(f"Results saved to: {args.output_dir}")
        print(f"Request ID: {result.request_id}")
        
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 