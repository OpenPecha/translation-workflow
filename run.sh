#!/bin/bash

# Tibetan Buddhist Translation System: Full Translation Workflow
# This script runs both phases of the translation process:
# 1. Initial translation (with commentaries & basic glossary)
# 2. Post-translation processing (terminology standardization & word-by-word translation)

# Load environment variables
source .env 2>/dev/null || (echo "Warning: .env file not found. Please set ANTHROPIC_API_KEY manually.")

# Default values
INPUT_FILE="input/choenjuk_bo.json"
LANGUAGE="Chinese"
BATCH_SIZE=10
MAX_RETRIES=3
RETRY_DELAY=5
OUTPUT_PREFIX="choenjuk_zh"

# Color codes for pretty output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --input)
      INPUT_FILE="$2"
      shift 2
      ;;
    --language)
      LANGUAGE="$2"
      shift 2
      ;;
    --batch-size)
      BATCH_SIZE="$2"
      shift 2
      ;;
    --retries)
      MAX_RETRIES="$2"
      shift 2
      ;;
    --delay)
      RETRY_DELAY="$2"
      shift 2
      ;;
    --output)
      OUTPUT_PREFIX="$2"
      shift 2
      ;;
    --debug)
      DEBUG_FLAG="--debug"
      shift
      ;;
    --help)
      echo "Usage: ./run.sh [options]"
      echo "Options:"
      echo "  --input FILE        Input JSON or JSONL file with Tibetan text"
      echo "  --language LANG     Target language (English, Chinese, Hindi, etc.)"
      echo "  --batch-size SIZE   Number of texts to process in parallel"
      echo "  --retries NUM       Number of retry attempts for failed batches"
      echo "  --delay SECONDS     Delay between retry attempts"
      echo "  --output PREFIX     Output file prefix"
      echo "  --debug             Enable debug logging"
      echo "  --help              Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# Check for required environment variables
if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo "Error: ANTHROPIC_API_KEY environment variable not set"
  echo "Please set it in .env file or export it manually"
  exit 1
fi

# Create output directory if it doesn't exist
mkdir -p outputs

echo -e "${BLUE}======= Tibetan Buddhist Translation System =======${NC}"
echo -e "${BLUE}Input file:${NC} $INPUT_FILE"
echo -e "${BLUE}Target language:${NC} $LANGUAGE"
echo -e "${BLUE}Batch size:${NC} $BATCH_SIZE"

# Phase 1: Initial Translation
echo -e "\n${GREEN}===== Phase 1: Initial Translation =====${NC}"
echo "Running batch translation process..."

python examples/batch_process.py \
  --input "$INPUT_FILE" \
  --batch-size "$BATCH_SIZE" \
  --retries "$MAX_RETRIES" \
  --delay "$RETRY_DELAY" \
  --output "outputs/${OUTPUT_PREFIX}" \
  --language "$LANGUAGE" \
  $DEBUG_FLAG

# Check if Phase 1 was successful
if [ $? -ne 0 ]; then
  echo -e "${YELLOW}Warning: Phase 1 encountered errors, but continuing to Phase 2${NC}"
fi

# Phase 2: Post-Translation Processing
echo -e "\n${GREEN}===== Phase 2: Post-Translation Processing =====${NC}"
echo "Running post-translation standardization..."

PHASE1_OUTPUT="outputs/${OUTPUT_PREFIX}.jsonl"

# Check if Phase 1 output exists
if [ -f "$PHASE1_OUTPUT" ]; then
  echo "Processing output from Phase 1: $PHASE1_OUTPUT"
  
  python examples/post_translation_example.py \
    --input "$PHASE1_OUTPUT" \
    --output "outputs/${OUTPUT_PREFIX}_final.jsonl" \
    --glossary "outputs/${OUTPUT_PREFIX}_glossary.csv" \
    --language "$LANGUAGE" \
    $DEBUG_FLAG
  
  # Check if Phase 2 was successful
  if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}Translation process completed successfully!${NC}"
    echo -e "Final output: ${BLUE}outputs/${OUTPUT_PREFIX}_final.jsonl${NC}"
    echo -e "Standardized glossary: ${BLUE}outputs/${OUTPUT_PREFIX}_glossary.csv${NC}"
  else
    echo -e "\n${YELLOW}Phase 2 completed with errors.${NC}"
    echo -e "Partial results may be available in: ${BLUE}outputs/${OUTPUT_PREFIX}_final.jsonl${NC}"
  fi
else
  echo -e "${YELLOW}Phase 1 output file not found: $PHASE1_OUTPUT${NC}"
  echo "Cannot proceed with Phase 2. Please check Phase 1 logs for errors."
  exit 1
fi

echo -e "\n${BLUE}======= Translation Workflow Complete =======${NC}"