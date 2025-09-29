from typing import Literal, Optional, List
from pydantic import BaseModel, Field



class AdditionalInfo(BaseModel):
    location: Optional[str] = None
    bio: Optional[str] = None
    dob: Optional[str] = None
    gender: Optional[Literal["Male", "Female", "Other"]] = None

class Profile(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    additional_info: Optional[AdditionalInfo] = None


# class Preferences(BaseModel):
#     response_tone: Optional[Literal["formal", "informal", "friendly", "professional"]] = "friendly"
#     preferred_length: Optional[Literal["short", "medium", "long", "detailed"]] = "medium"
#     preferred_language: Optional[str] = None
#     humor_level: Optional[Literal["serious", "slightly humorous", "balanced", "funny", "very humorous"]] = "balanced"
#     preferred_name: Optional[str] = None
#     additional_notes: Optional[str] = None

class SettingsItem(BaseModel):
    label: str
    key: str
    value: Optional[object]
    type: Literal["boolean", "string", "text", "select", "combobox", "number", "list", "password", "shortcut", "integration"]
    description: Optional[str] = None
    options: Optional[List[str] | str] = None
    min: Optional[float] = None
    max: Optional[float] = None
    auth_id: Optional[str] = None  # For integration type
    parent: Optional[str] = None  # For hierarchical settings
    condition_type: Optional[Literal["equals", "not_equals", "in", "not_in"]] = None
    condition: Optional[object] = None 

class SettingsCategory(BaseModel):
    category: str
    settings: List[SettingsItem]

# Tool Filter Service Data Models
class ToolArgument(BaseModel):
    name: str
    type: str
    description: str
    is_required: bool

class ParsedTool(BaseModel):
    tool_name: str
    description: str
    arguments: List[ToolArgument]
    # A generated high-level summary for better semantic matching
    semantic_description: str = Field(..., description="A concise, high-quality description focused on the tool's core purpose.")
    # A blob of text with all keywords for efficient search
    keyword_corpus: str = Field(..., description="A comprehensive text blob including name, description, args, and keywords for high recall.")

class Conversation(BaseModel):
    auto_send_transcription: bool = Field(default=False, description="Automatically send transcription after speech-to-text.")