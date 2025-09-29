import os
from itertools import islice
from pathlib import Path
from typing import List, Optional
import re
from utils.data_handler import settings as _settings

config = {
    "allowedDirectories": _settings.get("allowed_directories", ["~", "%HOMEDRIVE%", "%temp%"]),
    "fileReadLineLimit": _settings.get("file_read_line_limit", 1000),
    "blockedCommands": _settings.get("blocked_commands", []),
}

# Base directory for non-absolute paths
ARTIFACTS_DIR = (Path.cwd() / "artifacts").resolve()

def _expand_env_vars(path_str: str) -> str:
    """Expand $VAR and %VAR% env variables safely."""
    if not path_str:
        return path_str
    expanded = os.path.expandvars(path_str)

    def repl(match: re.Match) -> str:
        var = match.group(1)
        return os.environ.get(var, match.group(0))
    expanded = re.sub(r"%([^%]+)%", repl, expanded)

    # Normalize drive root like 'C:' -> 'C:\'
    if re.fullmatch(r"[A-Za-z]:", expanded):
        expanded = expanded + os.sep
    return expanded

def _expand_path(path_str: str) -> Path:
    """Expands env vars, user home; resolves to absolute.
    Non-absolute inputs are resolved under ./artifacts by default.
    """
    # 1) expand env vars
    expanded = _expand_env_vars(path_str)
    # 2) expand user home (~)
    expanded = os.path.expanduser(expanded)
    candidate = Path(expanded)

    # 3) resolve relative paths under artifacts
    if not candidate.is_absolute():
        candidate = ARTIFACTS_DIR / candidate

    return candidate.resolve()

def _get_allowed_dirs() -> List[Path]:
    """Expand configured allowed directories and always include artifacts dir."""
    allowed_dirs_str = config.get("allowedDirectories", []) or []
    expanded: List[Path] = []
    for p in allowed_dirs_str:
        try:
            expanded.append(_expand_path(p))
        except Exception:
            # Skip entries that cannot be expanded
            continue
    # Always allow the artifacts directory
    expanded.append(ARTIFACTS_DIR)
    # Deduplicate
    seen = set()
    result: List[Path] = []
    for p in expanded:
        key = str(p)
        if key not in seen:
            seen.add(key)
            result.append(p)
    return result

def _is_path_allowed(resolved_path: Path) -> bool:
    """Checks if a resolved path is within the allowed directories from the config."""
    allowed_dirs = _get_allowed_dirs()
    if not allowed_dirs:
        return True  # If not configured, allow all for safety, though not recommended

    # Check if the path is a child of any allowed directory
    for allowed in allowed_dirs:
        try:
            resolved_path.relative_to(allowed)
            return True
        except ValueError:
            continue
    return False

def validate_path(path_str: str, check_exists: bool = False) -> Path:
    """
    Validates a path for security and existence.
    Returns the resolved Path object if valid, otherwise raises an exception.
    """
    resolved_path = _expand_path(path_str)
    
    if not _is_path_allowed(resolved_path):
        allowed_paths = config.get("allowedDirectories", [])
        raise PermissionError(
            f"Path '{path_str}' is not within the allowed directories: {', '.join(allowed_paths + ['./artifacts'])}"
        )
    
    if check_exists and not resolved_path.exists():
        raise FileNotFoundError(f"Path '{path_str}' does not exist.")

    return resolved_path

def read_file(path_str: str, offset: int = 0, length: Optional[int] = None) -> str:
    """
    Reads file content with support for positive and negative offsets.
    """
    if length is None:
        limit_val = config.get("fileReadLineLimit", 1000)
        try:
            length = int(limit_val)
        except (TypeError, ValueError):  # pragma: no cover
            length = 1000

    valid_path = validate_path(path_str, check_exists=True)
    
    with open(valid_path, 'r', encoding='utf-8', errors='replace') as f:
        if offset >= 0:
            # Positive offset: read from the start
            end_index = offset + (length or 0)
            lines = list(islice(f, offset, end_index))
            header = f"[Reading {len(lines)} lines from line {offset+1}]\n\n"
        else:
            # Negative offset: read from the end (like tail)
            num_lines = abs(offset)
            lines = f.readlines()
            # Ensure we don't go out of bounds
            start_index = max(0, len(lines) - num_lines)
            selected_lines = lines[start_index:]
            lines = selected_lines
            header = f"[Reading last {len(lines)} lines]\n\n"
            
    return header + "".join(lines)



def write_file(path_str: str, content: str, mode: str = 'rewrite'):
    """Writes content to a file, either overwriting or appending."""
    valid_path = validate_path(path_str)
    # Ensure parent directory exists (also creates ./artifacts for relative paths)
    valid_path.parent.mkdir(parents=True, exist_ok=True)
    
    write_mode = 'w' if mode == 'rewrite' else 'a'
    
    with open(valid_path, write_mode, encoding='utf-8') as f:
        f.write(content)

def list_directory(path_str: str) -> List[str]:
    """Lists the contents of a directory."""
    valid_path = validate_path(path_str, check_exists=True)
    if not valid_path.is_dir():
        raise NotADirectoryError(f"'{path_str}' is not a directory.")

    entries = []
    for entry in os.scandir(valid_path):
        prefix = "[DIR] " if entry.is_dir() else "[FILE]"
        entries.append(f"{prefix} {entry.name}")
    return entries

# Other filesystem functions are wrappers around os/shutil
def create_directory(path_str: str):
    validate_path(path_str).mkdir(parents=True, exist_ok=True)

def move_file(source_str: str, dest_str: str):
    import shutil
    source_path = validate_path(source_str, check_exists=True)
    dest_path = validate_path(dest_str)
    shutil.move(str(source_path), str(dest_path))

def get_file_info(path_str: str) -> dict:
    valid_path = validate_path(path_str, check_exists=True)
    stat = valid_path.stat()
    info = {
        "size": stat.st_size,
        "created": stat.st_ctime,
        "modified": stat.st_mtime,
        "is_directory": valid_path.is_dir(),
        "is_file": valid_path.is_file(),
    }
    if info['is_file'] and info['size'] < 10 * 1024 * 1024: # 10MB limit
        try:
            with open(valid_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                info['line_count'] = len(content.splitlines())
        except Exception:
            info['line_count'] = 'Could not determine (binary or encoding issue)'
    return info

def search_files(root_path_str: str, pattern: str) -> List[str]:
    root_path = validate_path(root_path_str, check_exists=True)
    results = []
    for root, _, files in os.walk(root_path):
        for name in files:
            if pattern.lower() in name.lower():
                full_path = Path(root) / name
                # Re-validate each found path for security
                if _is_path_allowed(full_path):
                    results.append(str(full_path))
    return results