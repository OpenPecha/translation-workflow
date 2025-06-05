import json
import logging
from typing import Dict, Any
from ..models import MultiLevelTreeInput, ProcessingRequest

logger = logging.getLogger(__name__)


class InputProcessor:
    """
    Processes multi-level-tree.jsonl input format.
    Handles glossary, ucca_formatted, and multilevel_summary components.
    """
    
    def __init__(self):
        logger.info("Initialized InputProcessor for multi-level-tree format")
    
    def load_from_jsonl(self, file_path: str) -> MultiLevelTreeInput:
        """
        Load data from multi-level-tree.jsonl file.
        
        Args:
            file_path: Path to the JSONL file
            
        Returns:
            MultiLevelTreeInput object with parsed data
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                line = f.readline().strip()
                if not line:
                    raise ValueError("Empty JSONL file")
                
                data = json.loads(line)
                
                # Validate required fields
                required_fields = ['glossary', 'ucca_formatted', 'multilevel_summary']
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    raise ValueError(f"Missing required fields: {missing_fields}")
                
                return MultiLevelTreeInput(
                    glossary=data['glossary'],
                    ucca_formatted=data['ucca_formatted'],
                    multilevel_summary=data['multilevel_summary']
                )
                
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in file {file_path}: {e}")
            raise ValueError(f"Invalid JSON format: {e}")
        except Exception as e:
            logger.error(f"Error loading file {file_path}: {e}")
            raise
    
    def create_processing_request(
        self, 
        input_data: MultiLevelTreeInput, 
        target_languages: list[str],
        source_text: str = None
    ) -> ProcessingRequest:
        """
        Create a processing request from input data.
        
        Args:
            input_data: The multi-level tree input data
            target_languages: List of target languages for translation
            source_text: Optional source text if available separately
            
        Returns:
            ProcessingRequest object ready for workflow processing
        """
        logger.info(f"Creating processing request for languages: {target_languages}")
        
        return ProcessingRequest(
            input_data=input_data,
            target_languages=target_languages,
            source_text=source_text
        )
    
    def prepare_components(self, input_data: MultiLevelTreeInput) -> Dict[str, str]:
        """
        Prepare the three components for processing.
        
        Args:
            input_data: The multi-level tree input data
            
        Returns:
            Dictionary with prepared components
        """
        components = {
            'glossary': input_data.glossary,
            'ucca_formatted': input_data.ucca_formatted,
            'multilevel_summary': input_data.get_multilevel_summary_text()
        }
        
        logger.info("Prepared input components for processing")
        logger.debug(f"Glossary length: {len(components['glossary'])}")
        logger.debug(f"UCCA formatted length: {len(components['ucca_formatted'])}")
        logger.debug(f"Multilevel summary length: {len(components['multilevel_summary'])}")
        
        return components
    
    def validate_input(self, input_data: MultiLevelTreeInput) -> list[str]:
        """
        Validate the input data and return any validation errors.
        
        Args:
            input_data: The input data to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Check for empty components
        if not input_data.glossary.strip():
            errors.append("Glossary is empty")
        
        if not input_data.ucca_formatted.strip():
            errors.append("UCCA formatted analysis is empty")
        
        if not input_data.multilevel_summary:
            errors.append("Multilevel summary is empty")
        elif not isinstance(input_data.multilevel_summary, dict):
            errors.append("Multilevel summary must be a JSON object")
        
        # Check for reasonable content lengths
        if len(input_data.glossary) < 10:
            errors.append("Glossary appears too short")
        
        if len(input_data.ucca_formatted) < 10:
            errors.append("UCCA formatted analysis appears too short")
        
        if errors:
            logger.warning(f"Input validation found {len(errors)} issues: {errors}")
        else:
            logger.info("Input validation passed")
        
        return errors 