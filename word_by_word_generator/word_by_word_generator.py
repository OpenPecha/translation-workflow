import os
from dotenv import load_dotenv
from .models import State
from .workflow import compiled_workflow

# Load environment variables from .env file
load_dotenv()

# Ensure ANTHROPIC_API_KEY is set
if not os.getenv("ANTHROPIC_API_KEY"):
    raise ValueError("ANTHROPIC_API_KEY not found in environment variables. Please set it in your .env file.")

def run_word_by_word_pipeline(tibetan_text: str, ucca_interpretation: str) -> State:
    """
    Runs the word-by-word glossary generation pipeline.
    """
    initial_state: State = {
        "tibetan_text": tibetan_text,
        "ucca_interpretation": ucca_interpretation,
        "glossary": "" # Initialize glossary as empty
    }
    
    print("Starting word-by-word glossary generation pipeline...")
    print(f"Input Tibetan Text: {tibetan_text}")
    print(f"Input UCCA Interpretation: {ucca_interpretation}")
    
    final_state = compiled_workflow.invoke(initial_state)
    
    print("\nPipeline finished.")
    if final_state.get("glossary"):
        print("Generated Glossary:")
        print(final_state["glossary"])
    else:
        print("Glossary generation failed or produced no output.")
        
    return final_state

if __name__ == "__main__":
    # Example Usage
    sample_tibetan_text = "བཀྲ་ཤིས་བདེ་ལེགས།" # "Tashi Delek" - Greetings/Good Fortune
    sample_ucca_interpretation = """
    {
      "nodes": {
        "N1": {"type": "FN", "attributes": {"text": "བཀྲ་ཤིས་བདེ་ལེགས།"}},
        "N2": {"type": "P", "attributes": {"text": "བཀྲ་ཤིས་"}},
        "N3": {"type": "P", "attributes": {"text": "བདེ་ལེགས།"}}
      },
      "edges": [
        {"source": "N1", "target": "N2", "relation": "participant"},
        {"source": "N1", "target": "N3", "relation": "participant"}
      ],
      "root": "N1"
    }
    """ # A very simplistic UCCA example

    print("Running example word-by-word generation:")
    result_state = run_word_by_word_pipeline(sample_tibetan_text, sample_ucca_interpretation)
