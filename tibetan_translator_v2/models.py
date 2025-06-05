import json
import logging
from typing import List, Literal, TypedDict, Any, Union, Dict, Optional
from pydantic import BaseModel, Field, field_validator
from dataclasses import dataclass

# Setup model-specific logger
logger = logging.getLogger("tibetan_translator.models")



# Add new model for glossary entries
class GlossaryEntry(BaseModel):
    tibetan_term: str = Field(description="Original Tibetan term")
    translation: str = Field(description="Exact translation used in the target language")
    context: str = Field(description="Context or usage notes in the target language")
    entity_category: str = Field(description="Entity category (e.g., person, place, etc.) in the target language, if not entity then leave it blank")
    commentary_reference: str = Field(description="Reference to commentary explanation in the target language")
    category: str = Field(description="Term category (philosophical, technical, etc.) in the target language")

class GlossaryExtraction(BaseModel):
    entries: List[GlossaryEntry] = Field(description="List of extracted glossary entries")
    
    @field_validator('entries', mode='before')
    @classmethod
    def validate_entries(cls, v: Any) -> List[GlossaryEntry]:
        """Validator to handle string inputs for entries field.
        
        This is especially important for Chinese and other non-Latin languages where
        JSON parsing might return a string instead of properly parsing to a list.
        """
        logger.debug(f"GlossaryExtraction validator received entries of type: {type(v)}")
        
        # If it's already a list, return it
        if isinstance(v, list):
            logger.debug(f"Entries is already a list with {len(v)} items")
            return v
            
        # If it's a string, try to parse it as JSON
        if isinstance(v, str):
            logger.debug(f"Entries is a string, attempting to parse as JSON. Content sample: {v[:200]}...")
            try:
                parsed = json.loads(v)
                logger.debug(f"Successfully parsed string to {type(parsed)}")
                
                # If parsing gave us a list, return it
                if isinstance(parsed, list):
                    logger.debug(f"Parsed to a list with {len(parsed)} items")
                    return parsed
                else:
                    logger.error(f"Parsed JSON is not a list but {type(parsed)}")
                    raise ValueError(f"Expected a list after parsing string, got {type(parsed)}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse entries string as JSON: {str(e)}")
                raise ValueError(f"Invalid JSON string for entries: {str(e)}")
        
        # If we got here, it's neither a list nor a string that parses to a list
        logger.error(f"Invalid type for entries: {type(v)}")
        raise ValueError(f"entries must be a list or a string containing a JSON list, got {type(v)}")

class LanguageCheck(BaseModel):
    is_target_language: bool = Field(
        description="Whether the translation is actually in the specified target language",
    )
    language_issues: str = Field(
        description="Description of any issues with the target language if not in target language",
        default="",
    )


class Translation(BaseModel):
    format_matched: bool = Field(
        description="Evaluate if translation preserves source text's formatting such as linebreaks",
    )
    plaintext_translation: str = Field("Exact Plaintext translation in key plaintext_translation: '' ")
    translation : str = Field("Exact Translation text in key translation: '' ")





class State(TypedDict):
    translation: str
    source: str
    language: str 
    plaintext_translation: str 
    ucca : str
    word_by_word_translation: str
    itteration: int 
    formated: bool
    glossary: List[GlossaryEntry]
    plaintext_translation: str
    multilevel_summary: str


@dataclass
class MultiLevelTreeInput:
    """
    Input model for multi-level-tree.jsonl format.
    Contains three main components: glossary, ucca_formatted, and multilevel_summary.
    """
    glossary: str  # Raw text string
    ucca_formatted: str  # Raw text string 
    multilevel_summary: Dict[str, Any]  # JSON structure to be converted to text
    
    def _json_to_text(self, obj: Any, indent: int = 0) -> str:
        """
        Convert JSON object to hierarchical text format without quotes on keys.
        
        Args:
            obj: JSON object to convert
            indent: Current indentation level
            
        Returns:
            String representation of the JSON in hierarchical text format
        """
        if isinstance(obj, dict):
            lines = []
            for key, value in obj.items():
                prefix = "  " * indent
                if isinstance(value, (dict, list)):
                    lines.append(f"{prefix}{key}:")
                    lines.append(self._json_to_text(value, indent + 1))
                else:
                    lines.append(f"{prefix}{key}: {value}")
            return "\n".join(lines)
        elif isinstance(obj, list):
            lines = []
            for i, item in enumerate(obj):
                prefix = "  " * indent
                if isinstance(item, (dict, list)):
                    lines.append(f"{prefix}- Item {i+1}:")
                    lines.append(self._json_to_text(item, indent + 1))
                else:
                    lines.append(f"{prefix}- {item}")
            return "\n".join(lines)
        else:
            return str(obj)
    
    def get_multilevel_summary_text(self) -> str:
        """
        Convert multilevel_summary JSON to text format.
        
        Returns:
            Text representation of the multilevel summary
        """
        return self._json_to_text(self.multilevel_summary)


@dataclass
class ProcessingRequest:
    """
    Request model for processing multi-level tree input.
    """
    input_data: MultiLevelTreeInput
    target_languages: list[str]
    source_text: Optional[str] = None  # Original source text if available


@dataclass
class TranslationResult:
    """
    Result model for a single language translation.
    """
    language: str
    format_matched: bool
    plaintext_translation: str
    translation: str


@dataclass
class GlossaryEntry:
    """
    Model for individual glossary entries.
    """
    tibetan_term: str
    translation: str
    context: str
    commentary_reference: str
    category: str
    entity_category: str


@dataclass
class ProcessingResult:
    """
    Complete processing result containing translations and glossaries for all languages.
    """
    request_id: str
    translations: Dict[str, TranslationResult]  # language -> translation result
    glossaries: Dict[str, list[GlossaryEntry]]  # language -> glossary entries
    source_components: Dict[str, str]  # Components used in processing
    
    def __post_init__(self):
        """Initialize empty dictionaries if not provided."""
        if not self.translations:
            self.translations = {}
        if not self.glossaries:
            self.glossaries = {}
        if not self.source_components:
            self.source_components = {}


@dataclass 
class WorkflowState:
    """
    State model for the processing workflow.
    """
    request: ProcessingRequest
    result: ProcessingResult
    current_step: str = "initialized"
    errors: list[str] = None
    
    def __post_init__(self):
        """Initialize empty errors list if not provided."""
        if self.errors is None:
            self.errors = []
