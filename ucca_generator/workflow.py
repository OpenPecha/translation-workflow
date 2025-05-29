import logging
import json
from langchain_anthropic import ChatAnthropic
from pydantic import ValidationError

# Import models for schema generation and State typing
from .models import State, UCCANode, UCCAGraph

# LLM Initialization
llm = ChatAnthropic(model="claude-3-sonnet-latest", max_tokens=8192) # Max tokens for Claude 3 Sonnet is 8192

# Logger Setup
logger = logging.getLogger("ucca_generator.workflow")

# Generate Pydantic model schemas to include in the prompt
UCCA_NODE_SCHEMA_JSON = json.dumps(UCCANode.model_json_schema(), indent=2)
UCCA_GRAPH_SCHEMA_JSON = json.dumps(UCCAGraph.model_json_schema(), indent=2)

UCCA_GENERATION_PROMPT_TEMPLATE = f"""
You are an expert in UCCA (Universal Conceptual Cognitive Annotation) parsing.
Your task is to parse the given input text and generate a UCCA graph in JSON format.
The input text may contain Tibetan script and its English translation, or just Tibetan script.
If only Tibetan is provided, infer the English translation for the 'english_text' field in each UCCANode.

The output JSON MUST strictly adhere to the following Pydantic model schemas:

UCCAGraph Schema:
{UCCA_GRAPH_SCHEMA_JSON}

UCCANode Schema (referenced within UCCAGraph nodes list):
{UCCA_NODE_SCHEMA_JSON}

Key instructions for UCCANode fields:
- 'id': A unique string identifier for each node (e.g., "N1", "N2").
- 'type': The semantic type of the node (e.g., "Parallel Scene", "Participant", "Process", "State", "Adverbial", "Center", "Elaborator").
- 'text': The exact Tibetan text span this node covers. If not applicable or if the node is purely structural/implicit, use an empty string or a conceptual placeholder.
- 'english_text': A literal English translation of the 'text'. Words not in the source text (e.g., implied elements) should be in square brackets [ ].
- 'implicit': Clarify implied or contextually understood content not explicitly in the text but necessary for comprehension. Use an empty string if content is explicit.
- 'parent_id': The 'id' of the parent node. The root node of the graph should have an empty string for 'parent_id'.
- 'children': A list of 'id's of child nodes. This should be consistent with 'parent_id' relationships.
- 'descriptor': A brief, human-readable descriptor or label for the node, summarizing its role or content.

Input Text:
{{input_text}}

Generate the UCCA graph as a single JSON object conforming to the UCCAGraph Schema provided above.
Ensure all node 'id's are unique. Ensure 'root_id' in UCCAGraph points to the main root node's 'id'.
Focus on creating a coherent and valid UCCA structure based on the input.
"""

def generate_ucca_graph_step(state: State) -> State:
    logger.info(f"Initiating UCCA graph generation for: {state['input_text'][:70]}...")
    state['processing_log'].append("Starting UCCA graph generation.")

    try:
        formatted_prompt_str = UCCA_GENERATION_PROMPT_TEMPLATE.format(input_text=state['input_text'])
        logger.debug(f"Formatted prompt for LLM (first 500 chars): {formatted_prompt_str[:500]}...")
        
        response = llm.invoke(formatted_prompt_str)
        raw_llm_output = response.content
        logger.info("LLM invocation successful.")
        logger.debug(f"Raw LLM output: {raw_llm_output}")
        # Clean the raw LLM output to extract pure JSON
        cleaned_json_str = raw_llm_output.strip()
        if cleaned_json_str.startswith("```json"):
            # Remove ```json prefix and ``` suffix
            cleaned_json_str = cleaned_json_str[len("```json"):]
            if cleaned_json_str.endswith("```"):
                cleaned_json_str = cleaned_json_str[:-len("```")]
        elif cleaned_json_str.startswith("```"):
            # Remove ``` prefix and ``` suffix (for cases without 'json' marker)
            cleaned_json_str = cleaned_json_str[len("```"):]
            if cleaned_json_str.endswith("```"):
                cleaned_json_str = cleaned_json_str[:-len("```")]
        
        state['ucca_graph_json_str'] = cleaned_json_str.strip() # Store the cleaned JSON string
        
        graph_data = json.loads(cleaned_json_str)
        
        # Validate and parse into UCCAGraph model
        parsed_graph = UCCAGraph(**graph_data)
        state['ucca_graph'] = parsed_graph
        logger.info(f"Successfully parsed LLM output into UCCAGraph with root ID: {parsed_graph.root_id}")

    except json.JSONDecodeError as e:
        logger.error(f"JSONDecodeError parsing LLM output: {e}. LLM output was: {state['ucca_graph_json_str']}")
        state['error_message'] = f"Failed to decode LLM output as JSON: {e}"
    except Exception as e: # Catches Pydantic validation errors and other issues
        logger.error(f"Error processing LLM response or validating UCCA graph: {e}", exc_info=True)
        state['error_message'] = f"Error processing LLM response: {e}"
        if state['ucca_graph_json_str']:
             logger.error(f"LLM output that caused error: {state['ucca_graph_json_str']}")

    return state

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("UCCA Generator workflow module initialized for testing.")
    
    test_input_text = "མི་རྟག་པ་སྒོམ་པ་ལ་དགོས་པ་ཅི་ཡོད། What is the purpose of meditating on impermanence?"
    
    initial_test_state: State = {
        "input_text": test_input_text,
        "ucca_graph_json_str": None,
        "ucca_graph": None,
        "feedback": None,
        "error_message": None,
        "processing_log": []
    }
    
    logger.info(f"Testing with input: {test_input_text}")
    result_state = generate_ucca_graph_step(initial_test_state)
    
    if result_state['ucca_graph']:
        logger.info("UCCA Graph generation successful!")
        logger.info(f"Root ID: {result_state['ucca_graph'].root_id}")
        logger.info(f"Number of nodes: {len(result_state['ucca_graph'].nodes)}")
        # logger.debug(f"Generated Graph: {result_state['ucca_graph'].model_dump_json(indent=2)}") # Can be very verbose
    elif result_state['error_message']:
        logger.error(f"UCCA Graph generation failed: {result_state['error_message']}")
    else:
        logger.warning("UCCA Graph generation finished with no graph and no specific error message.")
    
    logger.info(f"Processing Log: {result_state['processing_log']}")

