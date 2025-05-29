from typing import List, Optional, TypedDict, Literal, Any
from pydantic import BaseModel, Field, ValidationError

class UCCANode(BaseModel):
    id: str = Field(description="Unique identifier for the node")
    type: str = Field(description="Node type (e.g., Parallel Scenes, Participants, Process, etc.)")
    text: str = Field(description="Text span covered by this node")
    english_text: str = Field(description="Literal English translation of the node, Words not in the source text are put in square brackets [ ]")
    implicit: str = Field(
        description='Clarifies implied or contextually understood content that is not explicitly stated in the original text but necessary for comprehension; use an empty string if content is explicitly stated.'
    )
    parent_id: str = Field(description="ID of parent node", default="")
    children: List[str] = Field(description="IDs of child nodes", default_factory=list)
    descriptor: str = Field(description="Descriptor of the node")

class UCCAGraph(BaseModel):
    nodes: List[UCCANode] = Field(description="List of UCCA nodes in the graph")
    root_id: str = Field(description="ID of the root node")

class ActionableSuggestion(BaseModel):
    suggestion_type: str = Field(description="Type of corrective action suggested (e.g., 'SPLIT_NODE', 'MERGE_NODES', 'CHANGE_NODE_TYPE', 'ADD_RELATION', 'MODIFY_RELATION_LABEL', 'ADD_IMPLICIT_CONTENT')")
    target_node_ids: Optional[List[str]] = Field(default_factory=list, description="IDs of the UCCA nodes primarily affected by this suggestion. Can be empty if the suggestion is general.")
    description: str = Field(description="Detailed explanation of the suggestion and its rationale.")
    relevant_commentary_snippets: Optional[List[str]] = Field(default_factory=list, description="List of exact text spans copied verbatim from the commentary that directly support this suggestion. These must match the commentary word-for-word without modification.")

class StructuredFeedback(BaseModel):
    grade: Literal["bad", "okay", "good", "great"] = Field(
        description="Overall quality grade of the UCCA graph."
    )
    overall_summary: str = Field(
        description="A brief textual summary of the evaluation, highlighting key strengths and weaknesses."
    )
    specific_suggestions: List[ActionableSuggestion] = Field(
        default_factory=list,
        description="A list of specific, actionable suggestions for improvement. This list can be empty if the grade is 'great' or no specific changes are needed."
    )

class State(TypedDict):
    """
    Defines the structure of the state that flows through the UCCA generation graph/workflow.
    """
    input_text: str
    ucca_graph_json_str: Optional[str] # To store raw JSON output from LLM
    ucca_graph: Optional[UCCAGraph] # To store the parsed UCCA graph
    error_message: Optional[str]
