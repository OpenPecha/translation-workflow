"""
Tibetan Translator v2 Pipeline

A translation pipeline for processing multi-level-tree.jsonl input format
and generating translations and glossaries in multiple languages.

This pipeline is designed to work with:
- Glossary (raw text)
- UCCA formatted linguistic analysis (raw text)  
- Multilevel summary (JSON converted to hierarchical text)
"""

from .models import (
    MultiLevelTreeInput,
    ProcessingRequest, 
    ProcessingResult,
    TranslationResult,
    GlossaryEntry,
    WorkflowState
)

from .processors.pipeline import (
    TranslationPipeline,
    process_multilevel_tree_file
)

from .processors.input_processor import InputProcessor
from .processors.content_generator import ContentGenerator
from .processors.output_processor import OutputProcessor

from .prompts import (
    get_multilevel_translation_prompt,
    get_glossary_extraction_prompt
)

__version__ = "2.0.0"
__all__ = [
    # Models
    "MultiLevelTreeInput",
    "ProcessingRequest", 
    "ProcessingResult",
    "TranslationResult",
    "GlossaryEntry",
    "WorkflowState",
    
    # Main Pipeline
    "TranslationPipeline",
    "process_multilevel_tree_file",
    
    # Processors
    "InputProcessor",
    "ContentGenerator", 
    "OutputProcessor",
    
    # Prompts
    "get_multilevel_translation_prompt",
    "get_glossary_extraction_prompt"
]
