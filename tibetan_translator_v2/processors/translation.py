from typing import List
from tibetan_translator.models import State, Translation_extractor
from tibetan_translator.prompts import (
    get_translation_evaluation_prompt,
    get_translation_improvement_prompt,
    get_initial_translation_prompt,
    get_translation_prompt
)
from tibetan_translator.utils import (
    llm, 
    llm_thinking, 
    get_translation_extraction_prompt, 
    get_plain_translation_prompt, 
    get_enhanced_translation_prompt
)
from tibetan_translator.config import MAX_TRANSLATION_ITERATIONS


def generate_translation_text_node(state: State) -> State:
    """Generates the full translation text (including UCCA, etc.) using the main prompt."""


    prompt_input = PROMPT_TEMPLATE.format(
        source=state['source'],
        ucca_formatted=state['ucca'],
        glossary=state['glossary_text']
    )
    raw_output_content = ""

    for attempt in range(MAX_RETRIES):
        try:
            logging.info(f"Attempt {attempt + 1}/{MAX_RETRIES} to generate translation text.")
            response = llm_thinking.invoke(prompt_input)
            
            current_attempt_content = ""
            if isinstance(response, list): # Handle 'thinking' enabled response
                for chunk in response:
                    if isinstance(chunk, dict) and chunk.get('type') == 'text':
                        current_attempt_content = chunk.get('text', '')
                        break 
            elif hasattr(response, 'content'): # Standard AIMessage
                if isinstance(response.content, list) and len(response.content) > 0:
                    for item_content in response.content:
                        if isinstance(item_content, dict) and item_content.get('type') == 'text':
                            current_attempt_content = item_content.get('text', '')
                            break
                    if not current_attempt_content and isinstance(response.content[0], str):
                        current_attempt_content = response.content[0]
                elif isinstance(response.content, str):
                    current_attempt_content = response.content
            else:
                current_attempt_content = str(response)

            if current_attempt_content.strip():
                raw_output_content = current_attempt_content
                logging.info("Successfully generated non-empty translation text.")
                break # Success
            else:
                logging.warning(f"LLM attempt {attempt + 1}/{MAX_RETRIES} generated empty content.")
        
        except Exception as e:
            logging.error(f"LLM invocation attempt {attempt + 1}/{MAX_RETRIES} failed with error: {e}")
        
        if attempt < MAX_RETRIES - 1:
            logging.info("Retrying translation text generation after a short delay...")
            time.sleep(1) # Simple backoff
        else: # All retries failed
            logging.error("LLM generated empty content or failed after multiple attempts.")
            raise RuntimeError("LLM failed to generate translation text after multiple attempts.")

    return { "raw_translation_output": raw_output_content}