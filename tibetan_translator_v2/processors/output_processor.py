import json
import logging
from typing import Dict, List, Any
from pathlib import Path
from datetime import datetime
from ..models import ProcessingResult, TranslationResult, GlossaryEntry

logger = logging.getLogger(__name__)


class OutputProcessor:
    """
    Processes and formats output from the translation pipeline.
    """
    
    def __init__(self, output_dir: str = "output"):
        """
        Initialize the output processor.
        
        Args:
            output_dir: Directory to save output files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        logger.info(f"Initialized OutputProcessor with output directory: {output_dir}")
    
    def format_translation_output(self, translation: TranslationResult) -> Dict[str, Any]:
        """
        Format a translation result for output.
        
        Args:
            translation: TranslationResult to format
            
        Returns:
            Dictionary with formatted translation data
        """
        return {
            "language": translation.language,
            "format_matched": translation.format_matched,
            "plaintext_translation": translation.plaintext_translation,
            "translation": translation.translation,
            "generated_at": datetime.now().isoformat()
        }
    
    def format_glossary_output(self, glossary_entries: List[GlossaryEntry]) -> List[Dict[str, str]]:
        """
        Format glossary entries for output.
        
        Args:
            glossary_entries: List of GlossaryEntry objects
            
        Returns:
            List of dictionaries with formatted glossary data
        """
        return [
            {
                "tibetan_term": entry.tibetan_term,
                "translation": entry.translation,
                "context": entry.context,
                "commentary_reference": entry.commentary_reference,
                "category": entry.category,
                "entity_category": entry.entity_category
            }
            for entry in glossary_entries
        ]
    
    def save_processing_result(self, result: ProcessingResult, request_id: str = None) -> str:
        """
        Save the complete processing result to files.
        
        Args:
            result: ProcessingResult to save
            request_id: Optional request ID for file naming
            
        Returns:
            Path to the saved output directory
        """
        if request_id is None:
            request_id = result.request_id
        
        # Create output directory for this request
        request_dir = self.output_dir / f"request_{request_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        request_dir.mkdir(exist_ok=True)
        
        try:
            # Save summary file
            self._save_summary(result, request_dir)
            
            # Save translations by language
            for language, translation in result.translations.items():
                if translation is not None:
                    self._save_translation(translation, request_dir, language)
            
            # Save glossaries by language
            for language, glossary in result.glossaries.items():
                if glossary:
                    self._save_glossary(glossary, request_dir, language)
            
            # Save source components used
            self._save_source_components(result.source_components, request_dir)
            
            logger.info(f"Successfully saved processing result to: {request_dir}")
            return str(request_dir)
            
        except Exception as e:
            logger.error(f"Error saving processing result: {e}")
            raise
    
    def _save_summary(self, result: ProcessingResult, output_dir: Path):
        """Save processing summary."""
        summary = {
            "request_id": result.request_id,
            "generated_at": datetime.now().isoformat(),
            "languages_processed": list(result.translations.keys()),
            "successful_translations": [
                lang for lang, trans in result.translations.items() 
                if trans is not None
            ],
            "glossary_entries_count": {
                lang: len(entries) for lang, entries in result.glossaries.items()
            },
            "source_components": list(result.source_components.keys())
        }
        
        summary_file = output_dir / "summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
    
    def _save_translation(self, translation: TranslationResult, output_dir: Path, language: str):
        """Save translation for a specific language."""
        translation_data = self.format_translation_output(translation)
        
        # Save as JSON
        json_file = output_dir / f"translation_{language.lower().replace(' ', '_')}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(translation_data, f, indent=2, ensure_ascii=False)
        
        # Save plaintext version
        plaintext_file = output_dir / f"plaintext_{language.lower().replace(' ', '_')}.txt"
        with open(plaintext_file, 'w', encoding='utf-8') as f:
            f.write(translation.plaintext_translation)
        
        # Save scholarly translation
        translation_file = output_dir / f"scholarly_{language.lower().replace(' ', '_')}.txt"
        with open(translation_file, 'w', encoding='utf-8') as f:
            f.write(translation.translation)
    
    def _save_glossary(self, glossary_entries: List[GlossaryEntry], output_dir: Path, language: str):
        """Save glossary for a specific language."""
        glossary_data = self.format_glossary_output(glossary_entries)
        
        # Save as JSON
        json_file = output_dir / f"glossary_{language.lower().replace(' ', '_')}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(glossary_data, f, indent=2, ensure_ascii=False)
        
        # Save as formatted text
        text_file = output_dir / f"glossary_{language.lower().replace(' ', '_')}.txt"
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(f"Glossary for {language}\n")
            f.write("=" * (len(language) + 12) + "\n\n")
            
            for entry in glossary_entries:
                f.write(f"Tibetan: {entry.tibetan_term}\n")
                f.write(f"Translation: {entry.translation}\n")
                f.write(f"Context: {entry.context}\n")
                f.write(f"Reference: {entry.commentary_reference}\n")
                f.write(f"Category: {entry.category}\n")
                if entry.entity_category:
                    f.write(f"Entity Category: {entry.entity_category}\n")
                f.write("-" * 50 + "\n\n")
    
    def _save_source_components(self, components: Dict[str, str], output_dir: Path):
        """Save the source components used in processing."""
        components_file = output_dir / "source_components.json"
        with open(components_file, 'w', encoding='utf-8') as f:
            json.dump(components, f, indent=2, ensure_ascii=False)
        
        # Save individual component files
        for component_name, content in components.items():
            component_file = output_dir / f"component_{component_name}.txt"
            with open(component_file, 'w', encoding='utf-8') as f:
                f.write(content)
    
    def create_consolidated_output(self, result: ProcessingResult) -> Dict[str, Any]:
        """
        Create a consolidated output dictionary with all results.
        
        Args:
            result: ProcessingResult to consolidate
            
        Returns:
            Dictionary with all results consolidated
        """
        output = {
            "request_id": result.request_id,
            "generated_at": datetime.now().isoformat(),
            "translations": {},
            "glossaries": {},
            "source_components": result.source_components
        }
        
        # Format translations
        for language, translation in result.translations.items():
            if translation is not None:
                output["translations"][language] = self.format_translation_output(translation)
            else:
                output["translations"][language] = None
        
        # Format glossaries
        for language, glossary in result.glossaries.items():
            output["glossaries"][language] = self.format_glossary_output(glossary)
        
        return output
    
    def export_to_json(self, result: ProcessingResult, filename: str = None) -> str:
        """
        Export the complete result to a single JSON file.
        
        Args:
            result: ProcessingResult to export
            filename: Optional filename (will be generated if not provided)
            
        Returns:
            Path to the exported JSON file
        """
        if filename is None:
            filename = f"translation_result_{result.request_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        output_file = self.output_dir / filename
        consolidated_output = self.create_consolidated_output(result)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(consolidated_output, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Exported complete result to: {output_file}")
        return str(output_file) 