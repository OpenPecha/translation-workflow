from typing import List
from tibetan_translator.models import KeyPoint, State, Translation_extractor, CommentaryPoints
from tibetan_translator.prompts import (
    get_key_points_extraction_prompt,
    get_commentary_translation_prompt,
    get_translation_prompt,
    
)
from tibetan_translator.utils import llm, llm_thinking, get_combined_commentary_prompt, create_source_analysis



def extract_commentary_key_points(commentary: str) -> List[KeyPoint]:
    """Extract key points from commentary with structured output."""
    prompt = get_key_points_extraction_prompt(commentary)
    result = llm.with_structured_output(CommentaryPoints).invoke(prompt)
    return result.points


def commentary_translator_1(state: State):
    """Translate first commentary with expertise focus."""
    if not state['commentary1']:
        return {"commentary1": None, "commentary1_translation": None}
    
    # Pass the target language to the commentary translation prompt
    prompt = get_commentary_translation_prompt(
        state['sanskrit'], 
        state['source'], 
        state['commentary1'],
        language=state.get('language', 'English')
    )
    # commentary_1 = llm.invoke(prompt)
    # commentary_1_ = llm.with_structured_output(Translation_extractor).invoke(get_translation_prompt(state['commentary1'], commentary_1.content))
    return {"commentary1": state['commentary1'], "commentary1_translation": state['commentary1']}


def commentary_translator_2(state: State):
    """Translate second commentary with philosophical focus."""
    if not state['commentary2']:
        return {"commentary2": None, "commentary2_translation": None}
    
    # Pass the target language to the commentary translation prompt
    prompt = get_commentary_translation_prompt(
        state['sanskrit'], 
        state['source'], 
        state['commentary2'],
        language=state.get('language', 'English')
    )
    # commentary_2 = llm.invoke(prompt)
    # commentary_2_ = llm.with_structured_output(Translation_extractor).invoke(get_translation_prompt(state['commentary2'], commentary_2.content))
    return {"commentary2": state['commentary2'], "commentary2_translation": state['commentary2']}


def commentary_translator_3(state: State):
    """Translate third commentary with traditional focus."""
    if not state['commentary3']:
        return {"commentary3": None, "commentary3_translation": None}
    
    # Pass the target language to the commentary translation prompt
    prompt = get_commentary_translation_prompt(
        state['sanskrit'], 
        state['source'], 
        state['commentary3'],
        language=state.get('language', 'English')
    )
    # commentary_3 = llm.invoke(prompt)
    # commentary_3_ = llm.with_structured_output(Translation_extractor).invoke(get_translation_prompt(state['commentary3'], commentary_3.content))
    return {"commentary3": state['commentary3'], "commentary3_translation": state['commentary3']}


def process_ucca(state: State):
    """Loads the UCCA data into the state for the aggregator."""
    return {"ucca": state.get("ucca", "")}

def process_word_by_word(state: State):
    """Loads the word-by-word translation into the state for the aggregator."""
    return {"word_by_word": state.get("word_by_word", "")}

def process_multilevel_summary(state: State):
    """Loads the multi-level summary into the state for the aggregator."""
    return {"multilevel_summary": state.get("multilevel_summary", "")}

def aggregator(state: State):
    """
    Combine UCCA, word-by-word, and summary into a new commentary.
    """
    # Combine the new inputs into a single string for the prompt
    combined_inputs = (
        f"UCCA Analysis:\n{state.get('ucca', 'Not available.')}\n\n"
        f"Word-by-Word Translation:\n{state.get('word_by_word', 'Not available.')}\n\n"
        f"Multi-Level Summary:\n{state.get('multilevel_summary', 'Not available.')}\n\n"
    )
    
    language = state.get('language', 'English')
    
    # Create the prompt for combining the inputs
    prompt_messages = get_combined_commentary_prompt(
        source_text=state['source'], 
        commentaries=combined_inputs,
        has_commentaries=True,
        language=language
    )
    
    # Use the thinking LLM for analysis
    response = llm_thinking.invoke(prompt_messages)
    
    commentary_content = ""
    if hasattr(response, 'content'):
        if isinstance(response.content, list) and len(response.content) > 1 and 'text' in response.content[1]:
            commentary_content = response.content[1]['text']
        else:
            commentary_content = str(response.content)
    else:
        commentary_content = str(response)
    
    return {"combined_commentary": commentary_content}