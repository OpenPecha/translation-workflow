# Tibetan Translation Workflow

A comprehensive system for translating Tibetan Buddhist texts with support for commentaries, terminology standardization, and multi-language outputs.

## Overview

This project provides a complete pipeline for translating Tibetan Buddhist texts to various target languages including English, Chinese, Hindi, and others. The translation workflow consists of two phases:

1. **Initial Translation**: Translates Tibetan texts with support for commentaries and basic glossary
2. **Post-Translation Processing**: Performs terminology standardization and provides word-by-word translation references

## Requirements

- Python 3.8+
- Anthropic API key (Claude)
- Input files in JSON/JSONL format with Tibetan text

## Installation

1. Clone this repository:
```bash
git clone https://github.com/OpenPecha/translation-workflow.git
cd translation-workflow
```

2. Set up your environment variables in a `.env` file:
```
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

## Using run.sh

The `run.sh` script provides a convenient way to execute the complete translation workflow. It handles both the initial translation and post-translation processing phases.

### Basic Usage

```bash
./run.sh
```

This runs the workflow with default settings:
- Input file: `input/choenjuk_bo.json`
- Target language: Chinese
- Batch size: 10
- Output prefix: `choenjuk_zh`

### Command Line Options

The script supports several command-line options:

```bash
./run.sh [options]
```

| Option | Description |
|--------|-------------|
| `--input FILE` | Input JSON or JSONL file with Tibetan text |
| `--language LANG` | Target language (English, Chinese, Hindi, etc.) |
| `--batch-size SIZE` | Number of texts to process in parallel |
| `--retries NUM` | Number of retry attempts for failed batches |
| `--delay SECONDS` | Delay between retry attempts |
| `--output PREFIX` | Output file prefix |
| `--debug` | Enable debug logging |
| `--help` | Show help message |

### Examples

Translate to English with a larger batch size:
```bash
./run.sh --input input/my_text.json --language English --batch-size 20 --output my_text_en
```

Translate to Hindi with debug logging:
```bash
./run.sh --language Hindi --output choenjuk_hi --debug
```

### Output Files

The script generates several output files in the `outputs` directory:
- `[prefix].jsonl`: Initial translation results
- `[prefix]_final.jsonl`: Post-processed translation with standardized terminology
- `[prefix]_glossary.csv`: Standardized glossary derived from the translations

## Project Structure

- `doc/`: Documentation for various components
- `examples/`: Example scripts for different use cases
- `input/`: Input Tibetan text files
- `outputs/`: Generated translations and glossaries
- `tibetan_translator/`: Core translation modules
  - `processors/`: Various text processing components
- `run.sh`: Main workflow script

## Additional Documentation

For more detailed information, refer to the documentation files in the `doc/` directory:
- `SYSTEM_OVERVIEW.md`: Full system architecture
- `USAGE_GUIDE.md`: Comprehensive usage instructions
- `POST_TRANSLATION.md`: Details on post-translation processing
- `MODULE_DETAILS.md`: Information about individual modules
