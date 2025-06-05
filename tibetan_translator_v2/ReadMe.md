# Tibetan Translator v2 Pipeline

A specialized translation pipeline for processing multi-level-tree.jsonl input format and generating translations and glossaries in multiple languages.

## Overview

The Tibetan Translator v2 pipeline is designed to process a new input format that contains three key components:

1. **Glossary**: Raw text string containing word-by-word or glossary-style translations
2. **UCCA Formatted**: Raw text string containing UCCA linguistic analysis 
3. **Multilevel Summary**: JSON structure containing hierarchical summary/analysis that gets converted to readable text

## Key Features

- **Multi-language Support**: Generate translations in multiple target languages simultaneously
- **Comprehensive Output**: Produces both scholarly translations and simplified plaintext versions
- **Glossary Generation**: Automatically extracts and formats glossary entries for each language
- **Flexible Input**: Handles multi-level-tree.jsonl format with automatic JSON-to-text conversion
- **Source Analysis**: Uses direct source analysis rather than traditional commentary processing
- **Structured Output**: Saves results in multiple formats (JSON, text files) with organized directory structure

## Input Format

The pipeline expects a `multi-level-tree.jsonl` file with the following structure:

```json
{
  "glossary": "Raw text string containing word-by-word translations...",
  "ucca_formatted": "Raw text string containing UCCA linguistic analysis...",
  "multilevel_summary": {
    "main_theme": "Theme description",
    "key_concepts": {
      "primary": "Primary concept",
      "secondary": ["concept1", "concept2"]
    },
    "structure": {
      "section1": "Description",
      "section2": "Description"
    }
  }
}
```

### Multilevel Summary Conversion

The JSON multilevel_summary is automatically converted to hierarchical text format without quotes on keys:

```
main_theme: Theme description
key_concepts:
  primary: Primary concept
  secondary:
    - concept1
    - concept2
structure:
  section1: Description
  section2: Description
```

## Installation

```bash
# Clone or copy the tibetan_translator_v2 directory to your project
# Install dependencies (adjust based on your LLM client)
pip install langchain-openai  # or your preferred LLM client
```

## Quick Start

### Basic Usage

```python
from tibetan_translator_v2 import TranslationPipeline

# Setup your LLM client (example with OpenAI)
from langchain_openai import ChatOpenAI
llm_client = ChatOpenAI(model="gpt-4", temperature=0)

# Create pipeline
pipeline = TranslationPipeline(llm_client=llm_client)

# Process a file
result = pipeline.process_file(
    input_file="data/sample.jsonl",
    target_languages=["English", "Spanish", "French"],
    source_text="Optional source text if available separately"
)

print(f"Processing completed: {result.request_id}")
print(f"Languages processed: {list(result.translations.keys())}")
```

### Convenience Function

```python
from tibetan_translator_v2 import process_multilevel_tree_file

result = process_multilevel_tree_file(
    input_file="data/sample.jsonl",
    target_languages=["English", "Chinese"],
    llm_client=llm_client,
    output_dir="my_output"
)
```

### Programmatic Input

```python
from tibetan_translator_v2 import MultiLevelTreeInput, TranslationPipeline

# Create input programmatically
input_data = MultiLevelTreeInput(
    glossary="Word by word translation text...",
    ucca_formatted="UCCA analysis text...",
    multilevel_summary={
        "theme": "Buddhist philosophy",
        "concepts": {"main": "meditation", "supporting": ["mindfulness"]}
    }
)

# Process directly
pipeline = TranslationPipeline(llm_client=llm_client)
result = pipeline.process_input_data(
    input_data=input_data,
    target_languages=["English"],
    source_text="Original Tibetan text"
)
```

## Command Line Interface

```bash
# Basic usage
python -m tibetan_translator_v2.main input.jsonl --languages English Spanish

# With source text and custom output directory
python -m tibetan_translator_v2.main input.jsonl \
    --languages English Chinese French \
    --source-text source.txt \
    --output-dir results

# Show example usage
python -m tibetan_translator_v2.main --example

# Verbose logging
python -m tibetan_translator_v2.main input.jsonl --languages English --verbose
```

## Output Structure

The pipeline generates organized output directories:

```
output/
└── request_<id>_<timestamp>/
    ├── summary.json                    # Processing summary
    ├── source_components.json          # Input components used
    ├── component_glossary.txt          # Raw glossary component
    ├── component_ucca_formatted.txt    # Raw UCCA component  
    ├── component_multilevel_summary.txt # Converted multilevel summary
    ├── translation_english.json        # English translation (JSON)
    ├── plaintext_english.txt          # English plaintext version
    ├── scholarly_english.txt          # English scholarly version
    ├── glossary_english.json          # English glossary (JSON)
    ├── glossary_english.txt           # English glossary (formatted text)
    └── [similar files for other languages]
```

## Key Differences from Original Pipeline

| Aspect | Original Pipeline | v2 Pipeline |
|--------|------------------|-------------|
| **Input Format** | Commentary-based JSONL | Multi-level-tree JSONL |
| **Commentary Processing** | Complex commentary extraction | Direct use of provided glossary |
| **UCCA Analysis** | Processed/extracted | Used as raw text |
| **Multilevel Summary** | Not present | JSON converted to hierarchical text |
| **Glossary Reference** | Traditional commentaries | Source analysis insights |
| **Text Processing** | Extensive parsing | Direct component usage |

## Models

### Core Models

- `MultiLevelTreeInput`: Handles the three input components with JSON-to-text conversion
- `ProcessingRequest`: Simple request wrapper for input data and target languages
- `TranslationResult`: Contains translation outputs for a single language
- `GlossaryEntry`: Individual glossary term with source analysis references
- `ProcessingResult`: Complete results for all languages and glossaries
- `WorkflowState`: Tracks processing state and errors

### Key Features

- **JSON-to-Text Conversion**: Automatic conversion of multilevel_summary JSON to readable hierarchical text
- **Source Analysis Focus**: Glossary entries reference source analysis rather than traditional commentaries
- **Multi-language Results**: Structured storage of translations and glossaries for each target language

## LLM Client Requirements

Your LLM client must implement:

```python
class LLMClient:
    def invoke(self, prompt: str):
        # Return object with .content attribute containing the response
        pass
```

Examples of compatible clients:
- LangChain ChatModels (ChatOpenAI, ChatAnthropic, etc.)
- Custom API wrappers following this interface

## Error Handling

The pipeline includes comprehensive error handling:

- Input validation for required fields
- JSON parsing validation for LLM responses
- Graceful handling of individual language failures
- Detailed logging for debugging

## Logging

Configure logging to see processing details:

```python
import logging
logging.basicConfig(level=logging.INFO)

# For debug details
logging.getLogger().setLevel(logging.DEBUG)
```

## Examples

See `main.py` for complete examples including:
- File processing
- Programmatic input creation
- CLI usage
- Error handling

## License

[Add your license information here]