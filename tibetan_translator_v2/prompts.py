from tibetan_translator.models import KeyPoint, State
from typing import List
from tibetan_translator.models import CommentaryVerification, Translation_extractor
import json
from tibetan_translator.utils import llm


def get_multilevel_translation_prompt(source_text, multilevel_summary, glossary, ucca_analysis, target_language="English"):
    """
    Generate a prompt for creating translations using multilevel summary, glossary, and UCCA analysis.
    
    Args:
        source_text: The original source text to translate
        multilevel_summary: Hierarchical summary/analysis of the text
        glossary: Word-by-word or glossary-style translation
        ucca_analysis: UCCA formatted linguistic analysis
        target_language: Target language for translation
    
    Returns:
        Formatted prompt string for translation generation
    """
    
    return f"""You are an expert translator tasked with creating a high-quality translation in {target_language}. You have been provided with three complementary sources of analysis to inform your translation:

SOURCE TEXT:
{source_text}

MULTILEVEL SUMMARY:
{multilevel_summary}

GLOSSARY:
{glossary}

UCCA LINGUISTIC ANALYSIS:
{ucca_analysis}

TRANSLATION TASK:
Create a coherent, accurate, and natural translation in {target_language} by synthesizing insights from all three sources above.

TRANSLATION PRINCIPLES:
1. ACCURACY: Preserve the exact meaning and nuances of the source text
2. FLUENCY: Produce natural, idiomatic {target_language} that flows well
3. COHERENCE: Ensure the translation maintains logical structure and clarity
4. COMPLETENESS: Translate all elements of the source text without omission
5. CONSISTENCY: Use consistent terminology throughout the translation

GUIDANCE FOR USING THE THREE SOURCES:
- Use the MULTILEVEL SUMMARY to understand the overall structure, themes, and hierarchical relationships
- Use the GLOSSARY for precise lexical choices and technical term accuracy
- Use the UCCA ANALYSIS to understand syntactic relationships and linguistic structure
- When sources conflict, prioritize accuracy to the source text meaning

LANGUAGE-SPECIFIC REQUIREMENTS FOR {target_language.upper()}:
- Use natural {target_language} grammar, syntax, and sentence structure
- Choose vocabulary that is appropriate for educated {target_language} speakers
- Maintain {target_language} stylistic conventions for this type of text
- Ensure cultural and linguistic appropriateness for {target_language} readers

OUTPUT REQUIREMENTS:
You must provide your response as a valid JSON object with exactly these three fields:

1. "format_matched": boolean - true if your translation preserves the source text's formatting (line breaks, paragraph structure, etc.), false otherwise
2. "plaintext_translation": string - An easy-to-understand, simplified translation in {target_language} that is accessible to general readers
3. "translation": string - The main scholarly translation in {target_language}, preserving original formatting where appropriate

CRITICAL INSTRUCTIONS:
- Your entire response must be a valid JSON object with these three fields only
- Both translation fields must be entirely in {target_language}
- Do not include any explanatory text outside the JSON structure
- Do not mix languages or include text in other languages 
- Preserve line breaks and formatting from the source text in the "translation" field when appropriate
- The "plaintext_translation" should be simplified and easy to understand for general readers
- The "translation" field can be more formal/scholarly while maintaining accuracy

Example output format:
{{
  "format_matched": true,
  "plaintext_translation": "Easy to understand translation for general readers in {target_language}",
  "translation": "Scholarly translation in {target_language} with\\nline breaks preserved if needed"
}}

IMPORTANT: 
- Output ONLY the JSON object - no other text before or after
- Ensure valid JSON formatting for all languages including Chinese, Japanese, Korean, etc.
- The plaintext_translation should be simplified and accessible while remaining accurate
- Both translation fields must contain the complete translation in {target_language}"""


def get_glossary_extraction_prompt(source_text, glossary, ucca_analysis, final_translation, language="English"):
    """
    Generate a prompt for extracting glossary terms from a translation using source analysis.
    
    Args:
        source_text: The original source text
        glossary: The glossary/word-by-word translation
        ucca_analysis: UCCA linguistic analysis  
        final_translation: The final translation result
        language: Target language for the glossary
    
    Returns:
        Formatted prompt string for glossary extraction
    """
    
    return f"""
Extract a comprehensive glossary from the final {language} translation using the provided source analysis:

SOURCE TEXT:
{source_text}

GLOSSARY:
{glossary}

UCCA ANALYSIS:
{ucca_analysis}

FINAL TRANSLATION:
{final_translation}

For each technical term, provide:
1. Original Tibetan term in the Source Text
2. Exact {language} translation term used
3. Usage context (IMPORTANT: This MUST be written in {language})
4. Commentary reference (IMPORTANT: Since this translation was based on direct source analysis rather than traditional commentaries, indicate this by starting with 'From source analysis:' (in {language}!) followed by relevant linguistic or structural insights in {language})
5. Term category (e.g., philosophical, technical, ritual, doctrinal) (In {language})
6. Entity category (e.g., person, place, etc.), if not entity then leave it blank

Focus on:
- Buddhist terms
- Important Entities (names of people, places, etc.)
- Specialized vocabulary in Buddhist Texts
- Do not use any terms that are not in the Source text
- Only refer to the source analysis for linguistic insights

CRITICAL INSTRUCTIONS:
- ALL descriptions, context, explanations, and categorical information MUST be in {language}
- DO NOT provide any content in English unless the target language is English
- The only field that should not be in {language} is the original Tibetan term
- For commentary_reference fields, always start with 'From source analysis:' to indicate this was not from traditional commentaries

OUTPUT FORMAT REQUIREMENTS:
- You MUST structure your output as valid, properly formatted JSON
- The output MUST be a JSON array (list) of objects
- Each object MUST have exactly these fields: tibetan_term, translation, context, commentary_reference, category, entity_category
- No extra fields or comments outside the JSON structure are allowed
- For ALL languages including Chinese, Japanese, Korean, etc., ensure the JSON is properly formatted with correct delimiters

Example of the required JSON structure:
```json
[
  {{
    "tibetan_term": "བྱང་ཆུབ་སེམས",
    "translation": "bodhicitta",
    "context": "The mind of enlightenment",
    "commentary_reference": "From source analysis: Term identified as key philosophical concept in Buddhist soteriology",
    "category": "philosophical",
    "entity_category": ""
  }},
  {{
    "tibetan_term": "ཤེས་རབ",
    "translation": "wisdom",
    "context": "Transcendent understanding",
    "commentary_reference": "From source analysis: Linguistic analysis shows connection to Sanskrit prajñā",
    "category": "philosophical",
    "entity_category": ""
  }}
]
```

IMPORTANT: 
1. The output MUST ONLY contain the JSON array - no other text
2. The JSON must be valid and properly formatted
3. All field contents in {language} (except the tibetan_term)
4. Even for Chinese, Japanese, Korean and other non-Latin languages, preserve the JSON structure exactly as shown
5. Do not add any text before or after the JSON array"""