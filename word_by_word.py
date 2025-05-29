from langchain_anthropic import ChatAnthropic
import logging
from typing import Dict, List, Optional, Tuple,TypedDict,Literal,Any
from pydantic import BaseModel, Field
import os

llm = ChatAnthropic(model="claude-3-7-sonnet-latest",max_tokens=8000)
GLOSSING_PROMPT_TEMPLATE = """Create a word-by-word disambiguated gloss for the following Tibetan text using the provided UCCA semantic interpretation. The gloss should:

1. **Format**: Present as a markdown list with one entry per word/morpheme
2. **Structure**: Each entry should contain:
   - The Tibetan word/morpheme
   - Its disambiguated translation based on the semantic context
   - Clarifications in square brackets including:
     - Grammatical analysis (case, tense, etc.)
     - Root word and meaning
     - Contextual interpretation informed by the UCCA analysis
     - Semantic role from the UCCA structure

3. **Integration**: Use the UCCA semantic interpretation to inform your translation choices, but present clarifications in natural language without referencing UCCA terminology

## Example Output

For the input 'འདོད་པའི་དཔེས་':
```markdown
- འདོད་པའི་ : which are accepted [Genitive of `འདོད་པ་`: to desire, accept, assert; here (the illustrative examples) which are accepted, agreed-upon; functions as Adverbial modifier in UCCA structure]
- དཔེས་ : through examples [Instrumental of `དཔེ་`: example, dṛṣṭānta; by means of a common illustrative example (like a mirage or dream) used to demonstrate the illusory nature of phenomena; part of "the example that is accepted by both sides" per UCCA analysis]
```

## Guidelines

- Prioritize semantic accuracy over literal translation
- When UCCA indicates implicit meanings, incorporate them into your clarifications
- If the UCCA analysis shows specific semantic roles (Agent, Patient, Process, etc.), reference these in your brackets
- For particles and grammatical markers, explain their function in context
- When words have multiple possible meanings, choose the one that best fits the UCCA semantic interpretation

---

**Text to analyze**: {tibetan_text}

**UCCA semantic interpretation**: {ucca_interpretation}

Critical:
Produce only the glossary do not include any additional text.
"""

from typing import TypedDict
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, START, END
class State(TypedDict):
    source: str
    ucca_formatted: str
    glossary: str
class Translation(BaseModel):
    glossary: str=Field(description="Glossary of words and their translations")
def translate(state: State) -> State:
    output = llm.with_structured_output(Translation).invoke(GLOSSING_PROMPT_TEMPLATE.format(tibetan_text=state['source'], ucca_interpretation=state['ucca_formatted']))
    return {"glossary": output.glossary}


optimizer_builder = StateGraph(State)
optimizer_builder.add_node("translate", translate)
optimizer_builder.add_edge(START, "translate")
optimizer_workflow = optimizer_builder.compile()