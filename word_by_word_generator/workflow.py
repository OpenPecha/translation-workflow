from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, START, END
from .models import State, Translation # Relative import

# Initialize the LLM
# TODO: Consider making the model name configurable or passed in
llm = ChatAnthropic(model="claude-3-opus-20240229")

GLOSSING_PROMPT_TEMPLATE = """
You are an expert linguist specializing in Tibetan and UCCA (Universal Conceptual Cognitive Annotation).
Your task is to provide a word-by-word glossary for the given Tibetan text, taking into account its UCCA semantic interpretation.

**Tibetan Text to analyze**: {tibetan_text}

**UCCA semantic interpretation**: {ucca_interpretation}

Critical:
Produce only the glossary do not include any additional text.
"""

def generate_glossary_step(state: State) -> State:
    """
    Generates a word-by-word glossary using the LLM.
    """
    prompt_input = {
        "tibetan_text": state['tibetan_text'],
        "ucca_interpretation": state['ucca_interpretation']
    }
    
    # Using with_structured_output to get a Pydantic model instance
    structured_llm = llm.with_structured_output(Translation)
    translation_output = structured_llm.invoke(GLOSSING_PROMPT_TEMPLATE.format(**prompt_input))
    
    return {
        "tibetan_text": state['tibetan_text'], # Carry over
        "ucca_interpretation": state['ucca_interpretation'], # Carry over
        "glossary": translation_output.glossary
    }

# Define the graph
workflow_builder = StateGraph(State)
workflow_builder.add_node("generate_glossary", generate_glossary_step)
workflow_builder.add_edge(START, "generate_glossary")
workflow_builder.add_edge("generate_glossary", END)

# Compile the graph
compiled_workflow = workflow_builder.compile()
