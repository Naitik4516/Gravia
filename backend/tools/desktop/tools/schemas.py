from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class GetConfigArgs(BaseModel):
    pass

class SetConfigValueArgs(BaseModel):
    key: str
    value: str | int | bool | List[str]

class ExecuteCommandArgs(BaseModel):
    command: str
    timeout_s: int = Field(60, description="Timeout in seconds for initial output.")
    shell: Optional[str] = None
    background: bool = Field(False, description="Run command in background (long-running).")
    blocked_commands: Optional[List[str]] = Field(None, description="Additional user-provided blocklist patterns (regex or substrings).")

class ReadOutputArgs(BaseModel):
    pid: int

class ForceTerminateArgs(BaseModel):
    pid: int

class ListSessionsArgs(BaseModel):
    pass

class ListProcessesArgs(BaseModel):
    pass

class KillProcessArgs(BaseModel):
    pid: int

class ReadFileArgs(BaseModel):
    path: str
    is_url: bool = False
    offset: int = 0
    length: Optional[int] = None

class WriteFileArgs(BaseModel):
    path: str
    content: str
    mode: Literal['rewrite', 'append'] = 'rewrite'

class CreateDirectoryArgs(BaseModel):
    path: str

class ListDirectoryArgs(BaseModel):
    path: str

class MoveFileArgs(BaseModel):
    source: str
    destination: str

class SearchFilesArgs(BaseModel):
    path: str
    pattern: str

class GetFileInfoArgs(BaseModel):
    path: str

class SearchCodeArgs(BaseModel):
    path: str
    pattern: str
    file_pattern: Optional[str] = None
    ignore_case: bool = True
    max_results: int = 1000
    include_hidden: bool = False
    context_lines: int = 0

class EditBlockArgs(BaseModel):
    file_path: str
    old_string: str
    new_string: str
    expected_replacements: int = 1