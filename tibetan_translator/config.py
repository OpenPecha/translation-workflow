import os
from dotenv import load_dotenv
import sys

# Load environment variables from .env file
try:
    load_dotenv()
except ImportError:
    print("python-dotenv module not found. Please install: pip install python-dotenv")
    sys.exit(1)

# API Configuration
# Require at least one provider key
if not (os.getenv("ANTHROPIC_API_KEY") or os.getenv("GOOGLE_API_KEY")):
    print("Error: No provider API key found. Set ANTHROPIC_API_KEY or GOOGLE_API_KEY in .env")
    sys.exit(1)

# Model Configuration
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "claude-3-7-sonnet-latest")
MAX_TOKENS = 5000

# File Paths
GLOSSARY_CSV_PATH = "translation_glossary.csv"
STATE_JSONL_PATH = "translation_states.jsonl"

# Translation Settings
MAX_TRANSLATION_ITERATIONS = 3 # Maximum iterations for translation quality improvements

# Formatting Settings
PRESERVE_SOURCE_FORMATTING = True  # Ensure translation matches source text formatting
MAX_FORMAT_ITERATIONS = 1  # Maximum iterations for formatting corrections