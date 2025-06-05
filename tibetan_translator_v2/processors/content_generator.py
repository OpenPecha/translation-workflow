import json
import logging
from typing import Dict, List, Any
from ..models import TranslationResult, GlossaryEntry
from ..prompts import get_multilevel_translation_prompt, get_glossary_extraction_prompt

logger = logging.getLogger(__name__)


class ContentGenerator:
    """
    Generates translations and glossaries using multilevel analysis.
    """
    
    def __init__(self, llm_client=None):
        """
        Initialize the content generator.
        
        Args:
            llm_client: LLM client for generating content (will be injected)
        """
        self.llm_client = llm_client
        logger.info("Initialized ContentGenerator")
    
    def generate_translation(
        self,
        source_text: str,
        multilevel_summary: str,
        glossary: str,
        ucca_analysis: str,
        target_language: str
    ) -> TranslationResult:
        """
        Generate translation for a specific language.
        
        Args:
            source_text: Original source text
            multilevel_summary: Hierarchical summary text
            glossary: Glossary/word-by-word translation
            ucca_analysis: UCCA linguistic analysis
            target_language: Target language for translation
            
        Returns:
            TranslationResult with translation data
        """
        logger.info(f"Generating translation for language: {target_language}")
        
        # Generate translation prompt
        prompt = get_multilevel_translation_prompt(
            source_text=source_text,
            multilevel_summary=multilevel_summary,
            glossary=glossary,
            ucca_analysis=ucca_analysis,
            target_language=target_language
        )
        
        try:
            # Get translation from LLM
            if self.llm_client is None:
                raise RuntimeError("LLM client not provided")
            
            response = self.llm_client.invoke(prompt)
            
            # Parse JSON response
            translation_data = json.loads(response.content)
            
            # Validate response structure
            required_fields = ['format_matched', 'plaintext_translation', 'translation']
            missing_fields = [field for field in required_fields if field not in translation_data]
            if missing_fields:
                raise ValueError(f"Translation response missing fields: {missing_fields}")
            
            result = TranslationResult(
                language=target_language,
                format_matched=translation_data['format_matched'],
                plaintext_translation=translation_data['plaintext_translation'],
                translation=translation_data['translation']
            )
            
            logger.info(f"Successfully generated translation for {target_language}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse translation JSON for {target_language}: {e}")
            raise ValueError(f"Invalid JSON response from LLM: {e}")
        except Exception as e:
            logger.error(f"Error generating translation for {target_language}: {e}")
            raise
    
    def generate_glossary(
        self,
        source_text: str,
        glossary: str,
        ucca_analysis: str,
        final_translation: str,
        target_language: str
    ) -> List[GlossaryEntry]:
        """
        Generate glossary entries for a translation.
        
        Args:
            source_text: Original source text
            glossary: Glossary/word-by-word translation
            ucca_analysis: UCCA linguistic analysis
            final_translation: The final translation result
            target_language: Target language for glossary
            
        Returns:
            List of GlossaryEntry objects
        """
        logger.info(f"Generating glossary for language: {target_language}")
        
        # Generate glossary prompt
        prompt = get_glossary_extraction_prompt(
            source_text=source_text,
            glossary=glossary,
            ucca_analysis=ucca_analysis,
            final_translation=final_translation,
            language=target_language
        )
        
        try:
            # Get glossary from LLM
            if self.llm_client is None:
                raise RuntimeError("LLM client not provided")
            
            response = self.llm_client.invoke(prompt)
            
            # Parse JSON response
            glossary_data = json.loads(response.content)
            
            # Validate that it's a list
            if not isinstance(glossary_data, list):
                raise ValueError("Glossary response must be a JSON array")
            
            # Convert to GlossaryEntry objects
            glossary_entries = []
            for item in glossary_data:
                # Validate entry structure
                required_fields = [
                    'tibetan_term', 'translation', 'context', 
                    'commentary_reference', 'category', 'entity_category'
                ]
                missing_fields = [field for field in required_fields if field not in item]
                if missing_fields:
                    logger.warning(f"Glossary entry missing fields: {missing_fields}")
                    continue
                
                entry = GlossaryEntry(
                    tibetan_term=item['tibetan_term'],
                    translation=item['translation'],
                    context=item['context'],
                    commentary_reference=item['commentary_reference'],
                    category=item['category'],
                    entity_category=item['entity_category']
                )
                glossary_entries.append(entry)
            
            logger.info(f"Successfully generated {len(glossary_entries)} glossary entries for {target_language}")
            return glossary_entries
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse glossary JSON for {target_language}: {e}")
            raise ValueError(f"Invalid JSON response from LLM: {e}")
        except Exception as e:
            logger.error(f"Error generating glossary for {target_language}: {e}")
            raise
    
    def generate_all_content(
        self,
        source_text: str,
        components: Dict[str, str],
        target_languages: List[str]
    ) -> Dict[str, Any]:
        """
        Generate translations and glossaries for all target languages.
        
        Args:
            source_text: Original source text
            components: Dictionary with glossary, ucca_formatted, multilevel_summary
            target_languages: List of target languages
            
        Returns:
            Dictionary with translations and glossaries for each language
        """
        logger.info(f"Generating content for {len(target_languages)} languages")
        
        results = {
            'translations': {},
            'glossaries': {}
        }
        
        for language in target_languages:
            try:
                # Generate translation
                translation = self.generate_translation(
                    source_text=source_text,
                    multilevel_summary=components['multilevel_summary'],
                    glossary=components['glossary'],
                    ucca_analysis=components['ucca_formatted'],
                    target_language=language
                )
                results['translations'][language] = translation
                
                # Generate glossary
                glossary = self.generate_glossary(
                    source_text=source_text,
                    glossary=components['glossary'],
                    ucca_analysis=components['ucca_formatted'],
                    final_translation=translation.translation,
                    target_language=language
                )
                results['glossaries'][language] = glossary
                
            except Exception as e:
                logger.error(f"Failed to generate content for {language}: {e}")
                # Continue with other languages
                results['translations'][language] = None
                results['glossaries'][language] = []
        
        logger.info("Completed content generation for all languages")
        return results
    
    def set_llm_client(self, llm_client):
        """
        Set the LLM client for content generation.
        
        Args:
            llm_client: The LLM client to use
        """
        self.llm_client = llm_client
        logger.info("LLM client set for ContentGenerator") 