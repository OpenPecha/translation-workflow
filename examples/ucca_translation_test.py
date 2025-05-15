"""
Test script for the UCCA-based translation system.
This example demonstrates the integration of UCCA semantic structure analysis
in the translation workflow.
"""

import os
import sys
import logging
from pprint import pprint

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tibetan_translator.workflow import optimizer_workflow
from tibetan_translator.models import UCCAGraph, UCCANode

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ucca_test")

# Sample Tibetan text to translate with a known UCCA structure
sample_text = """
ཇི་ལྟར་མཐོང་ཐོས་ཤེས་པ་དག །འདིར་ནི་དགག་པར་བྱ་མིན་ཏེ། །
བདེན་པར་རྟོག་པ་འདིར་ནི་བཟློག་བྱ་ཡིན། །སྡུག་བསྔལ་རྒྱུར་གྱུར་པ། །
"""

# Create a sample UCCA graph to test the integration
sample_ucca_graph = UCCAGraph(
    nodes=[
        UCCANode(id="0", type="ROOT", text=sample_text, parent_id="", children=["1"]),
        UCCANode(id="1", type="H", text=sample_text, parent_id="0", children=["2", "7"]),
        UCCANode(id="2", type="H1", text="ཇི་ལྟར་མཐོང་ཐོས་ཤེས་པ་དག །འདིར་ནི་དགག་པར་བྱ་མིན་ཏེ། །", parent_id="1", children=["3", "5"]),
        UCCANode(id="3", type="A", text="ཇི་ལྟར་མཐོང་ཐོས་ཤེས་པ་དག", parent_id="2", children=["4"]),
        UCCANode(id="4", type="D", text="དག", parent_id="3", children=[]),
        UCCANode(id="5", type="S", text="འདིར་ནི་དགག་པར་བྱ་མིན་ཏེ།", parent_id="2", children=["6"]),
        UCCANode(id="6", type="D", text="མིན", parent_id="5", children=[]),
        UCCANode(id="7", type="H2", text="བདེན་པར་རྟོག་པ་འདིར་ནི་བཟློག་བྱ་ཡིན། །སྡུག་བསྔལ་རྒྱུར་གྱུར་པ། །", parent_id="1", children=["8", "10", "12"]),
        UCCANode(id="8", type="A", text="བདེན་པར་རྟོག་པ", parent_id="7", children=["9"]),
        UCCANode(id="9", type="D", text="བདེན་པར", parent_id="8", children=[]),
        UCCANode(id="10", type="C", text="འདིར་ནི", parent_id="7", children=["11"]),
        UCCANode(id="11", type="D", text="ནི", parent_id="10", children=[]),
        UCCANode(id="12", type="A", text="སྡུག་བསྔལ་རྒྱུར་གྱུར་པ།", parent_id="7", children=["13"]),
        UCCANode(id="13", type="R", text="རྒྱུར་གྱུར་པ།", parent_id="12", children=[]),
    ],
    root_id="0"
)

# Sample English commentary to provide context
sample_commentary = """
This verse from a Madhyamaka text distinguishes between conventional perception and conceptual clinging.

The first part states that direct perceptions (seeing, hearing, and knowing) are not what is being negated in the Madhyamaka analysis. These conventional experiences are accepted as valid on the conventional level.

The second part clarifies that what is actually being negated is the conceptual imputation of inherent existence (true existence) onto phenomena, which is identified as the root cause of suffering in the Buddhist understanding of reality.

This distinction is crucial in Madhyamaka philosophy, which accepts conventional reality while rejecting inherent existence.
"""

def test_ucca_translation():
    """Test the UCCA-based translation system."""
    logger.info("Starting UCCA-based translation test")
    
    # Prepare input data for the workflow
    input_data = {
        "source": sample_text,
        "sanskrit": "",  # No Sanskrit source for this example
        "language": "English",
        "commentary1": "",
        "commentary2": "",
        "commentary3": sample_commentary,  # Using our sample commentary
        "key_points": [],
        "translation": [],
        "feedback_history": [],
        "format_feedback_history": [],
        "itteration": 0,
        "format_iteration": 0,
        "formated": False,
        "commentary1_translation": "",
        "commentary2_translation": "",
        "commentary3_translation": sample_commentary,
        "source_ucca": sample_ucca_graph,  # Pre-loaded UCCA graph
    }
    
    # Run the workflow
    logger.info("Invoking translation workflow with UCCA structure")
    result = optimizer_workflow.invoke(input_data)
    
    # Extract and print the results
    logger.info("Translation completed")
    logger.info("=== Final Translation ===")
    if result.get("translation") and len(result["translation"]) > 0:
        print(result["translation"][-1])
    
    logger.info("=== UCCA Analysis Results ===")
    if result.get("ucca_comparison") and len(result["ucca_comparison"]) > 0:
        final_comparison = result["ucca_comparison"][-1]
        print(f"Final UCCA match score: {final_comparison.match_score:.2f}")
        print(f"Semantically equivalent: {final_comparison.is_equivalent}")
        
        # If there were issues, print them
        if final_comparison.missing_nodes:
            print(f"Missing semantic elements: {', '.join(final_comparison.missing_nodes)}")
        if final_comparison.extra_nodes:
            print(f"Extra semantic elements: {', '.join(final_comparison.extra_nodes)}")
        if final_comparison.relationship_errors:
            print(f"Relationship errors: {', '.join(final_comparison.relationship_errors)}")
    
    logger.info("=== Glossary ===")
    if result.get("glossary"):
        for entry in result["glossary"][:5]:  # Show first 5 entries
            print(f"- {entry.tibetan_term} → {entry.translation}")
    
    return result

if __name__ == "__main__":
    result = test_ucca_translation()
    
    # Save results for further analysis if needed
    logger.info("Test completed. Results are available for analysis.")