import getpass
import os
from langchain_anthropic import ChatAnthropic
import logging
from typing import Dict, List, Optional, Tuple,TypedDict,Literal,Any
from pydantic import BaseModel, Field


llm = ChatAnthropic(model="claude-3-7-sonnet-latest",max_tokens=8000)


logger = logging.getLogger("tibetan_translator.processors.ucca")
from langchain_core.prompts import prompt
from langgraph.graph import StateGraph, START, END
from IPython.display import Image, display
import json


    
class UCCANode(BaseModel):
    id: str = Field(description="Unique identifier for the node")
    type: str = Field(description="Node type (e.g., Parallel Scenes, Participants, Process, etc.)")
    text: str = Field(description="Text span covered by this node")
    english_text: str = Field(description="Literal English translation of the node, Words not in the source text are put in square brackets [ ]")
    implicit: str = Field(
    description='"Clarifies implied or contextually understood content that is not explicitly stated in the original text but necessary for comprehension; empty string '' if content is explicitly stated"'
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
    source: str
    sanskrit: str
    language: str
    feedback_history: List[str]
    commentary1: str
    commentary2: str
    commentary3: str
    itteration: int  
    format_iteration: int  
    source_ucca: List[UCCAGraph]  
    latest_structured_suggestions: List[ActionableSuggestion]
    grade: str
class Feedback(BaseModel):
    grade: Literal["bad", "okay", "good", "great"] = Field(
        description="Evaluate UCCA graph quality",
    )
    feedback: str = Field(
        description="Detailed feedback on improving UCCA graph based on commentary interpretation",
    )


def route_ucca(state: State):
    """Route based on UCCA graph quality."""
    if state["grade"] == "great":
        return "Accepted"
    elif state["itteration"] >= 1:  # Changed condition
        return "Accepted"
    else:
        return "Rejected + Feedback"

def ucca_evaluator(state: State):
    """Evaluates the LATEST UCCA graph based on commentaries."""

    # Ensure there is a graph to evaluate
    if state["itteration"] >= 1:  # Check if already at max iterations
        return {
            "itteration": state["itteration"]
        }
    if not state.get("source_ucca"):
        print("Warning: ucca_evaluator called with no source_ucca in state.")
        return {
            "grade": "bad",
            "feedback_history": state.get("feedback_history", []) + ["Error: No UCCA graph to evaluate."],
            "itteration": state.get("itteration", 0)  # Preserve iteration count
        }

    # Always evaluate the latest graph
    latest_ucca_graph = state["source_ucca"][-1]
  # Perform the evaluation
    prompt_text = get_source_ucca_refinement_prompt( # Renamed 'prompt' to 'prompt_text' to avoid conflict
        source_text=state["source"],
        current_ucca_analysis=latest_ucca_graph,
        commentaries=[state["commentary1"], state["commentary2"], state["commentary3"]],
        sanskrit=state["sanskrit"],
        language=state["language"]
    )

    # Perform the evaluation
    try:
        structured_eval_result = llm.with_structured_output(StructuredFeedback).invoke(prompt_text)
        grade = structured_eval_result.grade
        overall_summary = structured_eval_result.overall_summary
        specific_suggestions_list = structured_eval_result.specific_suggestions # Assign to a new var

        # Format feedback for string history
        suggestions_text_parts = []
        if specific_suggestions_list: # Use the new var
            suggestions_text_parts.append("Specific Suggestions:")
            for i, sugg in enumerate(specific_suggestions_list): # Use the new var
                sugg_text = f"  {i+1}. Type: {sugg.suggestion_type}\n"
                if sugg.target_node_ids:
                    sugg_text += f"     Nodes: {', '.join(sugg.target_node_ids)}\n"
                sugg_text += f"     Description: {sugg.description}\n"
                if sugg.relevant_commentary_snippets:
                    sugg_text += f"     Commentary: {'; '.join(sugg.relevant_commentary_snippets)}\n"
                suggestions_text_parts.append(sugg_text)
        
        feedback_details_for_history = f"Summary: {overall_summary}\n" + "\n".join(suggestions_text_parts)

    except Exception as e:
        print(f"Error during UCCA evaluation: {str(e)}")
        grade = "bad"
        feedback_details_for_history = f"Evaluation failed due to error: {str(e)}. No structured feedback available."
        specific_suggestions_list = [] # Ensure it's an empty list on error

    current_iteration = state.get("itteration", 0)
    feedback_entry = f"Iteration {current_iteration} - Grade: {grade}\n{feedback_details_for_history}"
    updated_feedback_history = state.get("feedback_history", []) + [feedback_entry]

    return {
        "grade": grade,
        "feedback_history": updated_feedback_history,
        "latest_structured_suggestions": specific_suggestions_list, # Add this to the returned state
        "itteration": current_iteration
    }
    
def ucca_graph_to_text(ucca_graph: UCCAGraph) -> str:
    """
    Convert a UCCA graph to a readable text representation with hierarchical indentation.
    
    Args:
        ucca_graph: The UCCA graph to convert
        
    Returns:
        A string representation of the graph with proper indentation
    """
    if not ucca_graph or not hasattr(ucca_graph, 'nodes') or not hasattr(ucca_graph, 'root_id'):
        return "Invalid UCCA graph structure"
    
    # Create a mapping of node IDs to nodes for easy access
    node_map = {node.id: node for node in ucca_graph.nodes}
    
    # Function to recursively build the text representation
    def build_node_text(node_id, depth=0):
        if node_id not in node_map:
            return f"{'  ' * depth}|- [Missing Node: {node_id}]\n"
            
        node = node_map[node_id]
        indent = '  ' * depth
        node_text = f"{indent}|- [{node.id}] Type: {node.type} - \"{node.text[:40]}{'...' if len(node.text) > 40 else ''}\"\n"
        
        # Recursively add child nodes
        for child_id in node.children:
            node_text += build_node_text(child_id, depth + 1)
            
        return node_text
    
    # Start building from the root node
    result = f"UCCA Graph (Root ID: {ucca_graph.root_id})\n"
    result += build_node_text(ucca_graph.root_id)
    
    # Add a summary at the end
    result += f"\nTotal nodes: {len(ucca_graph.nodes)}"
    
    return result

# Example of how to use this function in your workflow:
def display_ucca_graph(state: State):
    """Function to display the latest UCCA graph in a readable format"""
    if state.get("source_ucca") and len(state["source_ucca"]) > 0:
        latest_graph = state["source_ucca"][-1]
        print(ucca_graph_to_text(latest_graph))
    else:
        print("No UCCA graph available in state")
def ucca_generator(state: State):
    """Generate improved translation based on commentary and feedback."""
    previous_feedback = "\n".join(state["feedback_history"]) if state["feedback_history"] else "No prior feedback."
    current_iteration = state.get("itteration", 0)

    if state.get("feedback_history"):
        # Get the most recent feedback only
        latest_feedback = state["feedback_history"][-1] if state["feedback_history"] else "No feedback yet."
        prompt = f"""
SYSTEM: You are a UCCA graph refinement expert tasked with producing a corrected semantic representation. You must address ALL issues mentioned in the feedback and create a complete, valid graph structure.

# INPUT
1. Source Text: {state['source']}
2. Feedback to Address: {latest_feedback}
3. Current UCCA Graph Structure: {ucca_graph_to_text(state['source_ucca'][-1])}

# REQUIREMENTS
- You MUST generate a COMPLETE, VALID JSON structure with ALL nodes fully specified
- Address EVERY issue mentioned in the feedback
- Maintain proper parent-child relationships throughout the graph
- Ensure all nodes have correct structure: id, type, text, english_text, parent_id, children, and descriptor fields
- Do not use abbreviations, ellipses ("..."), or shortcuts of any kind
- Format the JSON with proper indentation for readability
- Every single node from the original graph must be included (modified as needed) or explicitly replaced



# CRITICAL
DO NOT use ellipses or placeholders in your output. The ENTIRE graph must be explicitly defined with ALL nodes fully specified.
SERIOUS SYSTEM FAILURE will occur if you use "..." or other shortcuts in your JSON.
This is a production system where incomplete output will cause catastrophic compute costs.
Parrent Id cannot be NONE or NULL, root node can have an empty string as parrent node ("")
"""
        
        try:
            msg = llm.invoke(prompt)
            uccagraph = llm.with_structured_output(UCCAGraph).invoke(msg.content)
            return {
                "source_ucca": state["source_ucca"] + [uccagraph],
                "itteration": current_iteration + 1
            }
        except Exception as e:
            print(f"Error during UCCA generation: {str(e)}")
            try:
                msg = llm.invoke(prompt)
                uccagraph = llm.with_structured_output(UCCAGraph).invoke(msg.content)
                return {
                    "source_ucca": state["source_ucca"] + [uccagraph],
                    "itteration": current_iteration + 1
                }
            except Exception as e:
                print(f"Error during UCCA generation: {str(e)}")
 
    else:
        prompt = get_ucca_generation_prompt(    
            text= state["source"],
            language= "Tibetan"
        )
        try:
            msg = llm.invoke(prompt)
            uccagraph = llm.with_structured_output(UCCAGraph).invoke(msg.content)
        except Exception as e:
            print(f"Error during UCCA generation: {str(e)}")
            try:
                msg = llm.invoke(prompt)
                uccagraph = llm.with_structured_output(UCCAGraph).invoke(msg.content)
            except Exception as e:
                print(f"Error during UCCA generation: {str(e)}")

        return {"source_ucca": [uccagraph], "itteration": 0}
def get_ucca_generation_prompt(text: str, language: str = "Tibetan") -> str:
    """Generate a prompt for creating a UCCA graph from text with clearer structural guidance."""
    return f"""
SYSTEM: You are an expert linguistic analyzer specialized in Universal Conceptual Cognitive Annotation (UCCA) for Tibetan Buddhist texts. Your task is to create precise UCCA semantic graph structures that capture the nuanced meaning of these texts while providing English translations.

# WHAT IS UCCA?
UCCA (Universal Conceptual Cognitive Annotation) is a cross-linguistically applicable semantic representation scheme that captures the main semantic relationships in text through directed acyclic graphs (DAGs). For Tibetan Buddhist texts, this approach helps reveal the conceptual framework and philosophical insights embedded in the original language.

# INPUT TEXT
You will analyze the following Tibetan Buddhist text:
{text}
# OUTPUT FORMAT REQUIREMENTS
You MUST generate a valid JSON structure following this Pydantic model:
```json
class UCCANode(BaseModel):
    id: str = Field(description="Unique identifier for the node")
    type: str = Field(description="Node type (e.g., Parallel Scenes, Participants, Process, etc.)")
    text: str = Field(description="Text span covered by this node")
    english_text: str = Field(description="Literal English translation of the node, Words not in the source text are put in square brackets [ ]")
    parent_id: str = Field(description="ID of parent node", default="")
    children: List[str] = Field(description="IDs of child nodes", default_factory=list)
    implicit: str = Field(
    description='"Clarifies implied or contextually understood content that is not explicitly stated in the original text but necessary for comprehension; empty string '' if content is explicitly stated"'
)
    descriptor: str = Field(description="Descriptor of the node")
```

# FORMATTING RULES
Each node MUST have non-null values for all fields: id, type, text, english_text, parent_id, descriptor, and children
parent_id must be empty string "" for root node (NEVER null or missing)
"children" MUST be a list of strings (use empty list [] if no children)
"descriptor" MUST provide a concise explanation of the semantic function of the node
"english_text" MUST provide an accurate translation of the Tibetan text segment
Every node referenced in children lists MUST exist in the nodes list
Use descriptive IDs that reflect the hierarchical structure (e.g., "1", "1.1", "1.2", "2")

# UCCA NODE TYPES FOR TIBETAN BUDDHIST TEXTS
Parallel Scenes - Multiple scenes that occur in parallel or statements presented together
- MUST always have child Scenes
- Usually contains a Linker that connects the parallel elements
Example descriptor: "Parallel teachings on impermanence and suffering"
Common in Buddhist texts when listing the stages of meditation or parallel attributes

Scene - A self-contained unit representing a situation or statement
Example descriptor: "Teaching on the nature of emptiness"
Used to represent individual statements or situations within parallel structures

Participant - Entities that participate in a scene
MUST use one of these subcategories:
- Participant-Agent: Entity that initiates or performs an action
  Example descriptor: "The sage who is explaining the distinction"
- Participant-Patient: Entity that receives or is affected by an action
  Example descriptor: "The concept being analyzed"
- Participant-Location: Entity that specifies where something occurs
  Example descriptor: "The place where meditation is practiced"
- Participant-Goal: Entity that represents the purpose or aim
  Example descriptor: "The enlightenment being sought"
- Participant-Experiencer: Entity that perceives or experiences
  Example descriptor: "The practitioner experiencing insight"
- Participant-Recipient: Entity that receives something
  Example descriptor: "The student receiving instruction"

Process - The main action or event in a scene
Example descriptor: "The act of meditation" or "The process of realizing emptiness"
Common for verbs of practice, realization, or spiritual development

State - A stative situation or condition in a scene
Example descriptor: "The state of enlightenment" or "The nature of mind"
Frequent in descriptions of meditative states or qualities of enlightenment

Adverbial - Modifies how a process occurs
Example descriptor: "How the practice should be performed"
Often describes the manner of practice or approach to dharma

Center - The primary concept being elaborated on
Example descriptor: "The central teaching being explained"
Used for core concepts that receive further elaboration

Linker - Words that connect scenes or participants
Example descriptor: "Connection between practices" or "Transition to next teaching"
Found in transitions between sections of teachings

Relator - Relates two entities
Example descriptor: "Relationship between teacher and student"
Common in descriptions of lineage relationships or doctrinal connections

Elaborator - Provides additional information about an entity
Example descriptor: "Further detail about the meditative state"
Used for explanatory passages or commentary on main concepts

Quantity - Expresses numerical information
Example descriptor: "Number of bardos" or "Count of perfections"
Common in enumerations of Buddhist categories (e.g., Four Noble Truths)

Ground - Reference point for spatial or temporal relations
Example descriptor: "Foundation for practice" or "Context of teaching"
Used for setting the context of teachings or practices

Function - Grammatical function words
Example descriptor: "Grammatical marker without independent meaning"
Used for Tibetan grammatical particles and function words

# IMPLICIT NODES
For concepts that are conceptually present but not explicitly stated in the text, use the appropriate node type with "Implicit" prefix:
- Implicit Participant-Agent: Implied agent not explicitly mentioned
  Example descriptor: "Implied teacher who is giving the instruction"
- Implicit Participant-Patient: Implied patient not explicitly mentioned
  Example descriptor: "Implied concept being analyzed"
- Implicit Process: Implied action not explicitly stated
  Example descriptor: "Implied process of contemplation"
- Implicit State: Implied condition not explicitly mentioned
  Example descriptor: "Implied state of understanding"
- Implicit Relator: Implied relationship not explicitly stated
  Example descriptor: "Implied connection between concepts"
- Implicit Linker: Implied connection not explicitly marked
  Example descriptor: "Implied transition between teachings"

# ANNOTATION GUIDELINES FOR TIBETAN BUDDHIST TEXTS
Special Considerations
- Segment according to meaning units rather than grammatical sentences
- Analysis should follow conceptual boundaries even if it means splitting grammatical sentences
- Account for the non-linear structure of many Buddhist texts
- Be attentive to technical Buddhist terminology and preserve their specific meanings
- Recognize rhetorical devices common in Buddhist texts like repetition, enumeration, and rhetorical questions
- Consider the hierarchical nature of Buddhist philosophical expositions
- Note that pronouns may be implicit rather than explicit in Tibetan
- Always include appropriate Implicit nodes when concepts are understood but not stated explicitly

Text Segmentation Approach
- First identify the main philosophical points or teachings (scenes) based on meaning, not syntax
- For each scene, identify the central concept (Process or State)
- Identify all participants with their specific subtypes (Participant-Agent, Participant-Patient, etc.)
- Pay special attention to relationships between concepts (Relator)
- Mark modifiers that qualify how practices should be performed (Adverbial, Elaborator)
- Create appropriate Implicit nodes for any unstated but necessary concepts

Common Structures in Buddhist Texts
- Lists of attributes: Often under a Parallel Scenes node with parallel structures and Linkers
- Cause-effect relationships: Often involve a Process leading to a State
- Teacher-student dialogues: Typically scenes with clear Participant-Agent and Participant-Recipient
- Conceptual definitions: Usually a State with Elaborators
- Meditation instructions: Often Processes with Adverbials

# EXAMPLE ANNOTATION
For a hypothetical Tibetan Buddhist text segment about meditation:
  "nodes":
Here's the JSON content in text format without any curly braces:
"nodes": [
"id": "0",
"type": "Scene",
"text": "སྔོན་ཆད་མ་བྱུང་བ་ཡང་འདིར་བརྗོད་མེད། །",
"english_text": "[I] also have nothing to say here that wasn't said before",
"parent_id": "",
"children": ["1", "2", "3", "4", "5", "6", "7"],
"implicit": "",
"descriptor": "Statement about not having new content to express"
,
"id": "1",
"type": "Implicit Participant-Agent",
"text": "",
"english_text": "[I]",
"parent_id": "0",
"children": [],
"implicit": "The speaker or author who has nothing new to say",
"descriptor": "Implied author or speaker who is making the statement"
,
"id": "2",
"type": "Process",
"text": "བརྗོད་མེད",
"english_text": "have nothing to say",
"parent_id": "0",
"children": [],
"implicit": "",
"descriptor": "The process of not expressing or stating something"
,
"id": "3",
"type": "Participant-Location",
"text": "འདིར",
"english_text": "here",
"parent_id": "0",
"children": [],
"implicit": "",
"descriptor": "The contextual location where nothing new is being said"
,
"id": "4",
"type": "Linker",
"text": "ཡང",
"english_text": "also",
"parent_id": "0",
"children": [],
"implicit": "",
"descriptor": "Connecting the current statement to previous statements or context"
,
"id": "5",
"type": "Participant-Patient",
"text": "སྔོན་ཆད་མ་བྱུང་བ",
"english_text": "that wasn't said before",
"parent_id": "0",
"children": ["6", "7"],
"implicit": "",
"descriptor": "The content that is not being expressed because it isn't new"
,
"id": "6",
"type": "State",
"text": "མ་བྱུང་བ",
"english_text": "wasn't [said]",
"parent_id": "5",
"children": [],
"implicit": "",
"descriptor": "The state of something not having occurred or been expressed"
,
"id": "7",
"type": "Adverbial",
"text": "སྔོན་ཆད",
"english_text": "before",
"parent_id": "5",
"children": [],
"implicit": "",
"descriptor": "Temporal specification indicating previous time"
],      
# VALIDATION CHECKLIST
Before submitting your annotation, verify:
✓ Every node has a non-null parent_id (except root node which has "")
✓ Every node has a meaningful descriptor that explains its semantic function
✓ Every node has an accurate english_text translation
✓ All node IDs referenced in children arrays exist in the nodes list
✓ No circular references in the parent-child relationships
✓ The root_id refers to a valid node in the nodes list
✓ All fields have appropriate data types
✓ All text spans together cover the complete input text
✓ The graph is connected (no isolated nodes)
✓ Translations maintain the philosophical nuance of the original Tibetan
✓ Appropriate Participant subtypes are used (Agent, Patient, Location, Goal, Experiencer, Recipient)
✓ Parallel Scenes always have child Scenes and usually contain a Linker
✓ Implicit nodes use the proper composite tag format (e.g., "Implicit Participant-Agent")
✓ Analysis follows meaning boundaries rather than grammatical sentences

# COMMON ERRORS TO AVOID
- Segmenting solely by grammatical sentences rather than meaning units
- Creating Parallel Scenes without child Scenes or without a Linker
- Misinterpreting technical Buddhist terminology
- Providing overly literal translations that miss philosophical context
- Failing to recognize rhetorical structures common in Buddhist texts
- Creating descriptors that are too vague to be useful
- Missing implicit participants or processes that are understood in context
- Imposing Western philosophical frameworks on Tibetan Buddhist concepts
- Using general "Participant" type without specifying the subtype
- Using "Implicit" as a standalone type instead of the proper composite format 
Generate the complete UCCA graph JSON that strictly follows these requirements for the given Tibetan Buddhist text.

CRITICAL
DO NOT use ellipses or placeholders in your output. The ENTIRE graph must be explicitly defined with ALL nodes fully specified.
SERIOUS SYSTEM FAILURE will occur if you use "..." or other shortcuts in your JSON.
This is a production system where incomplete output will cause catastrophic compute costs.
Parent Id cannot be NONE or NULL, root node can have an empty string as parent node
"""

def get_source_ucca_refinement_prompt(
    source_text: str, # The Tibetan Buddhist text
    current_ucca_analysis: UCCAGraph, # The initial UCCA parse results for the source
    commentaries: list[str],
    sanskrit:str = "", # Commentaries specifically explaining the source text
    language: str = "                                  " # Language for the refinement suggestions
) -> str:
    """Generate a prompt to give feedback on the current UCCA graph based on commentaries."""
    
    # Format commentaries
    formatted_commentaries = "\n".join(f"- {c}" for c in commentaries if c)
    if not formatted_commentaries:
        formatted_commentaries = "None provided."
    
    # Handle different formats of current_ucca_analysis
    if isinstance(current_ucca_analysis, list) and current_ucca_analysis:
        current_ucca =ucca_graph_to_text(current_ucca_analysis[-1])
    else:
        current_ucca = ucca_graph_to_text(current_ucca_analysis)
    
    return f"""SYSTEM: You are an expert UCCA (Universal Conceptual Cognitive Annotation) graph refiner specializing in Tibetan Buddhist texts. Your task is to evaluate and provide feedback on semantic graphs that represent the meaning structure of Tibetan texts and their English translations while maintaining strict structural integrity.

# WHAT IS UCCA?
UCCA is a semantic representation framework that captures the meaning of text through directed acyclic graphs, where nodes represent meaningful units and edges represent semantic relationships. In this Tibetan-to-English translation system, UCCA graphs serve as an intermediate representation that preserves semantic structure across languages.

# YOUR ROLE
You are evaluating an existing UCCA graph against scholarly commentaries. Your goal is to identify ways to improve the graph's semantic accuracy while maintaining its structural validity. You must not create new content but rather ensure the existing content is properly represented.

# INPUT COMPONENTS
1. **Source Text (Tibetan Buddhist)**: 
   {source_text}

2. **Current UCCA Graph**: 
   {current_ucca}

3. **Scholarly Commentaries**:
   {formatted_commentaries}

4. **Sanskrit**:
   {sanskrit}


# EVALUATION CRITERIA

## Grading Scale (Must choose exactly one)
- **bad**: Critical semantic misrepresentations that distort the meaning of the text
- **okay**: Functional but with notable gaps or misrepresentations in semantic structure
- **good**: Mostly accurate with minor improvements needed for optimal representation
- **great**: Excellent semantic representation that accurately reflects the text's meaning structure

## Assessment Areas
1. **Semantic Accuracy** (Most Important)
   - Do the node types correctly represent the semantic roles in the text?
   - Are the relationships between concepts accurately captured?
   - Does the graph align with the interpretations provided in the commentaries and sanskrit text?

2. **Structural Completeness**
   - Are all key semantic elements from the source text represented?
   - Are important relationships mentioned in commentaries captured?
   - Is the granularity appropriate (neither too detailed nor too coarse)?

3. **Hierarchical Organization**
   - Are parent-child relationships semantically valid?
   - Is the scope of each node (what text it covers) appropriate?
   - Does the hierarchy reflect the proper emphasis and subordination in the text?

4. **Technical Validity**
   - Are all node IDs unique and properly referenced?
   - Do all nodes have valid parent_id values?
   - Are there any orphaned nodes or circular references?

# CONSTRAINTS
- **IMPORTANT**: Do NOT suggest adding nodes for concepts that aren't in the source text, even if mentioned in commentaries and Sanskrit text
- Commentaries should inform semantic interpretation, not add content
- Maintain the basic structure unless it fundamentally misrepresents the text
- Focus on semantic accuracy rather than stylistic preferences

# FEEDBACK FORMAT
Your feedback must be specific, actionable, and reference particular nodes or relationships. For each issue:

Node ID(s): <specific node ID(s)>

Current Problem:
Clearly describe the exact issue with the current representation or annotation.

Suggested Correction:
Provide a precise, actionable correction or adjustment for the identified issue.

Reference Commentary:
Cite the exact Tibetan text that directly supports your suggested correction. Ensure the reference precisely matches the context or semantic nuance relevant to your suggestion.



EVALUATION PROCESS

First, understand the source text and its structure, if the structure itself is bad you can suggest changing the whole things, you have full flexibily
Carefully review the current UCCA graph for completeness and accuracy
Compare the graph to insights from the commentaries
Identify specific improvements that would better align the graph with the text's meaning as clarified by commentaries 
Important!! English text should be literal translation or exact translation only
Suggest implicit for evey node types if the commentary supports it, not just type Implicit or related 
Assess the overall quality using the grading scale
Provide detailed, actionable feedback prioritizing the most important issues


Remember: The goal is to refine the semantic representation while maintaining strict adherence to UCCA principles and the content of the original text 

CRITICAL
DO NOT use ellipses or placeholders in your output. The ENTIRE graph must be explicitly defined with ALL nodes fully specified.
SERIOUS SYSTEM FAILURE will occur if you use "..." or other shortcuts in your JSON and also If the relevant commentary snippets are not exactly in one of the commentaries (string matched)
This is a production system where incomplete output will cause catastrophic compute costs.
Parent Id cannot be NONE or NULL, root node can have an empty string as parent node
"""




optimizer_builder = StateGraph(State)

optimizer_builder.add_node("ucca_generator", ucca_generator)
optimizer_builder.add_node("ucca_evaluator", ucca_evaluator)

optimizer_builder.add_edge(START, "ucca_generator")
optimizer_builder.add_edge("ucca_generator", "ucca_evaluator")

optimizer_builder.add_conditional_edges(
    "ucca_evaluator",
    route_ucca,
    {
        "Accepted": END,
        "Rejected + Feedback": "ucca_generator"
    }
) 

optimizer_workflow = optimizer_builder.compile()