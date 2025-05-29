from typing import TypedDict
from pydantic import BaseModel, Field

class State(TypedDict):
    tibetan_text: str
    ucca_interpretation: str
    glossary: str

class Translation(BaseModel):
    glossary: str = Field(description="Glossary of words and their translations")
