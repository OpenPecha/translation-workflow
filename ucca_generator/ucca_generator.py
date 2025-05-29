import logging
import json
from .models import State, UCCAGraph # UCCANode, ActionableSuggestion, StructuredFeedback (if used directly)
from .workflow import generate_ucca_graph_step, llm # logger as workflow_logger

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ucca_generator.main")
# workflow_specific_logger = logging.getLogger("ucca_generator.workflow") # If you want to control its level separately

def run_ucca_generation_pipeline(input_text: str) -> State:
    """
    Main function to orchestrate UCCA generation for a given text.
    """
    logger.info(f"Starting UCCA generation pipeline for input: \"{input_text[:100]}...\"")
    # workflow_specific_logger.info(f"Using LLM: {llm.model_name if hasattr(llm, 'model_name') else 'ChatAnthropic'}")

    initial_state: State = {
        "input_text": input_text,
        "ucca_graph_json_str": None,
        "ucca_graph": None,
        "error_message": None
    }

    try:
        final_state = generate_ucca_graph_step(initial_state)
        
        if final_state['ucca_graph']:
            logger.info(f"UCCA graph generated successfully. Root ID: {final_state['ucca_graph'].root_id}")
            logger.info(f"Number of nodes: {len(final_state['ucca_graph'].nodes)}")
            # For detailed output, uncomment below (can be very verbose)
            # logger.debug(f"Generated UCCA Graph: {final_state['ucca_graph'].model_dump_json(indent=2)}")
        elif final_state['error_message']:
            logger.error(f"UCCA generation failed: {final_state['error_message']}")
            if final_state['ucca_graph_json_str']:
                 logger.error(f"Problematic LLM JSON string: {final_state['ucca_graph_json_str']}")
        else:
            logger.warning("UCCA generation completed with no graph and no specific error message.")

    except Exception as e:
        logger.error(f"Critical error during UCCA generation pipeline: {e}", exc_info=True)
        # Update state with this critical error if possible, though it's outside the step
        initial_state['error_message'] = f"Pipeline critical error: {e}" # Or final_state if it exists
        return initial_state # Return the state with error

    logger.info("UCCA generation pipeline finished.")
    return final_state

if __name__ == "__main__":
    # Configure logging level for detailed output during testing
    # logging.getLogger("ucca_generator.workflow").setLevel(logging.DEBUG) # Enable debug for workflow
    
    sample_texts = [
        "The old house stood on a hill overlooking the town.",
        "She quickly ate the delicious cake."
        # "བྱ་ཁུ་བྱུག་སོས་ཀའི་དུས་སུ་ཡོང་།" # Tibetan example
    ]
    
    for i, text in enumerate(sample_texts):
        logger.info(f"\n--- Running UCCA Generation for Sample {i+1} ---")
        logger.info(f"Input Text: \"{text}\"")
        result_state = run_ucca_generation_pipeline(text)
        
        if result_state['ucca_graph']:
            print(f"\nSuccessfully generated UCCA graph for: \"{text}\"")
            print(f"Root ID: {result_state['ucca_graph'].root_id}")
            print(f"Nodes: {len(result_state['ucca_graph'].nodes)}")
            # print("Nodes details:")
            # for node in result_state['ucca_graph'].nodes:
            #     print(f"  ID: {node.id}, Type: {node.type}, Text: '{node.text}'")
        elif result_state['error_message']:
            print(f"\nFailed to generate UCCA graph for: \"{text}\"")
            print(f"Error: {result_state['error_message']}")
        
        # print(f"Full result state: {json.dumps(result_state, default=lambda o: o.model_dump() if isinstance(o, UCCAGraph) else str(o), indent=2)}")
        print("---------------------------------------\n")

    # Example of creating a model instance directly (for testing models.py)
    # try:
    #     node = UCCANode(id="node_example", type="Process", text="jumps", english_text="jumps", implicit="", descriptor="action")
    #     logger.info(f"Created UCCANode for testing: {node.model_dump_json(indent=2)}")
    # except Exception as e:
    #     logger.error(f"Error creating UCCANode instance for testing: {e}", exc_info=True)

