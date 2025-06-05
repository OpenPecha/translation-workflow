import logging
import uuid
from typing import Dict, List, Optional
from ..models import (
    MultiLevelTreeInput, ProcessingRequest, ProcessingResult, 
    WorkflowState, TranslationResult, GlossaryEntry
)
from .input_processor import InputProcessor
from .content_generator import ContentGenerator
from .output_processor import OutputProcessor

logger = logging.getLogger(__name__)


class TranslationPipeline:
    """
    Main pipeline for processing multi-level tree input and generating translations.
    """
    
    def __init__(self, llm_client=None, output_dir: str = "output"):
        """
        Initialize the translation pipeline.
        
        Args:
            llm_client: LLM client for content generation
            output_dir: Directory for output files
        """
        self.input_processor = InputProcessor()
        self.content_generator = ContentGenerator(llm_client)
        self.output_processor = OutputProcessor(output_dir)
        self.llm_client = llm_client
        
        logger.info("Initialized TranslationPipeline v2")
    
    def process_file(
        self, 
        input_file: str, 
        target_languages: List[str],
        source_text: Optional[str] = None,
        save_output: bool = True
    ) -> ProcessingResult:
        """
        Process a multi-level-tree.jsonl file.
        
        Args:
            input_file: Path to the input JSONL file
            target_languages: List of target languages for translation
            source_text: Optional source text if available separately
            save_output: Whether to save output files
            
        Returns:
            ProcessingResult with all translations and glossaries
        """
        request_id = str(uuid.uuid4())
        logger.info(f"Starting pipeline processing for request {request_id}")
        
        try:
            # Step 1: Load and validate input
            logger.info("Step 1: Loading input data")
            input_data = self.input_processor.load_from_jsonl(input_file)
            
            validation_errors = self.input_processor.validate_input(input_data)
            if validation_errors:
                logger.warning(f"Input validation issues: {validation_errors}")
            
            # Step 2: Create processing request
            logger.info("Step 2: Creating processing request")
            request = self.input_processor.create_processing_request(
                input_data, target_languages, source_text
            )
            
            # Step 3: Process the request
            result = self.process_request(request, request_id)
            
            # Step 4: Save output if requested
            if save_output:
                logger.info("Step 4: Saving output")
                output_path = self.output_processor.save_processing_result(result, request_id)
                logger.info(f"Output saved to: {output_path}")
            
            logger.info(f"Pipeline processing completed for request {request_id}")
            return result
            
        except Exception as e:
            logger.error(f"Pipeline processing failed for request {request_id}: {e}")
            raise
    
    def process_request(self, request: ProcessingRequest, request_id: str = None) -> ProcessingResult:
        """
        Process a translation request.
        
        Args:
            request: ProcessingRequest to process
            request_id: Optional request ID
            
        Returns:
            ProcessingResult with translations and glossaries
        """
        if request_id is None:
            request_id = str(uuid.uuid4())
        
        # Initialize result
        result = ProcessingResult(
            request_id=request_id,
            translations={},
            glossaries={},
            source_components={}
        )
        
        # Create workflow state
        state = WorkflowState(request=request, result=result)
        
        try:
            # Step 1: Prepare input components
            state.current_step = "preparing_components"
            logger.info(f"Preparing input components for request {request_id}")
            
            components = self.input_processor.prepare_components(request.input_data)
            result.source_components = components
            
            # Step 2: Generate content for all languages
            state.current_step = "generating_content"
            logger.info(f"Generating content for {len(request.target_languages)} languages")
            
            # Use source text from request if available, otherwise use glossary as fallback
            source_text = request.source_text or components.get('glossary', '')
            
            content_results = self.content_generator.generate_all_content(
                source_text=source_text,
                components=components,
                target_languages=request.target_languages
            )
            
            # Step 3: Update result with generated content
            state.current_step = "finalizing_results"
            result.translations = content_results['translations']
            result.glossaries = content_results['glossaries']
            
            # Count successful translations
            successful_languages = [
                lang for lang, trans in result.translations.items() 
                if trans is not None
            ]
            
            logger.info(f"Successfully processed {len(successful_languages)} of {len(request.target_languages)} languages")
            
            state.current_step = "completed"
            return result
            
        except Exception as e:
            state.current_step = "failed"
            state.errors.append(str(e))
            logger.error(f"Request processing failed at step '{state.current_step}': {e}")
            raise
    
    def process_input_data(
        self,
        input_data: MultiLevelTreeInput,
        target_languages: List[str],
        source_text: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> ProcessingResult:
        """
        Process input data directly (without file loading).
        
        Args:
            input_data: MultiLevelTreeInput object
            target_languages: List of target languages
            source_text: Optional source text
            request_id: Optional request ID
            
        Returns:
            ProcessingResult with translations and glossaries
        """
        if request_id is None:
            request_id = str(uuid.uuid4())
        
        logger.info(f"Processing input data directly for request {request_id}")
        
        # Create request
        request = ProcessingRequest(
            input_data=input_data,
            target_languages=target_languages,
            source_text=source_text
        )
        
        return self.process_request(request, request_id)
    
    def set_llm_client(self, llm_client):
        """
        Set the LLM client for the pipeline.
        
        Args:
            llm_client: The LLM client to use
        """
        self.llm_client = llm_client
        self.content_generator.set_llm_client(llm_client)
        logger.info("LLM client set for pipeline")
    
    def get_pipeline_status(self, state: WorkflowState) -> Dict:
        """
        Get the current status of pipeline processing.
        
        Args:
            state: WorkflowState to check
            
        Returns:
            Dictionary with status information
        """
        return {
            "request_id": state.result.request_id,
            "current_step": state.current_step,
            "target_languages": state.request.target_languages,
            "completed_translations": len([
                t for t in state.result.translations.values() if t is not None
            ]),
            "total_languages": len(state.request.target_languages),
            "errors": state.errors,
            "has_errors": len(state.errors) > 0
        }
    
    def create_simple_pipeline(self, llm_client) -> 'TranslationPipeline':
        """
        Create a simple pipeline instance with minimal configuration.
        
        Args:
            llm_client: LLM client to use
            
        Returns:
            Configured TranslationPipeline instance
        """
        pipeline = TranslationPipeline(llm_client=llm_client)
        return pipeline


# Convenience function for quick processing
def process_multilevel_tree_file(
    input_file: str,
    target_languages: List[str],
    llm_client,
    source_text: Optional[str] = None,
    output_dir: str = "output"
) -> ProcessingResult:
    """
    Convenience function to process a multi-level tree file quickly.
    
    Args:
        input_file: Path to input JSONL file
        target_languages: List of target languages
        llm_client: LLM client for content generation
        source_text: Optional source text
        output_dir: Output directory
        
    Returns:
        ProcessingResult with all translations
    """
    pipeline = TranslationPipeline(llm_client=llm_client, output_dir=output_dir)
    return pipeline.process_file(
        input_file=input_file,
        target_languages=target_languages,
        source_text=source_text
    ) 