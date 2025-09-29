from __future__ import annotations

import ast
import base64
import glob
import io
import logging
import mimetypes
import os
import re
import shutil
import time
from contextlib import redirect_stdout
from typing import Any, List, Set, Dict
from dataclasses import dataclass

# Set up logger for the SafeCodeExecutor
logger = logging.getLogger(__name__)

# Configure logging if not already configured
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '[%(asctime)s][%(levelname)s][%(name)s] %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)


@dataclass
class CodeExecutionInput:
    """Input for code execution."""
    code: str


@dataclass 
class CodeExecutionResult:
    """Result of code execution."""
    stdout: str
    stderr: str
    output_files: List['OutputFile']


class OutputFile:
    """A wrapper class to represent a file with name and binary data."""
    
    def __init__(self, name: str, file_path: str):
        self.name = name
        self.file_path = file_path
        
        # Read file data
        with open(file_path, 'rb') as f:
            self.data = f.read()
        
        # Convert file data to base64 string
        self.content = base64.b64encode(self.data).decode('utf-8')
        
        # Get MIME type
        self.mime_type = self._get_mime_type(name)
        # Size in bytes
        self.size = len(self.data)
    
    def _get_mime_type(self, filename: str) -> str:
        """Get MIME type for a file based on its extension."""
        mime_type, _ = mimetypes.guess_type(filename)
        if mime_type is None:
            # Default to application/octet-stream for unknown file types
            mime_type = 'application/octet-stream'
        return mime_type
    
    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable representation for frontend consumption."""
        # Files are saved under artifacts/code_executor_outputfiles
        return {
            "name": self.name,
            "mime_type": self.mime_type,
            "path": self.file_path,
        }

    def __repr__(self):
        return f"OutputFile(name='{self.name}', mime_type='{self.mime_type}')"


class SafeCodeExecutor:
    """A safe code executor that prevents execution of harmful code."""

    # Pre-imported modules (lightweight, commonly used)
    PRE_IMPORTED_MODULES: Set[str] = {
        # Core Python modules (lightweight and commonly used)
        'math', 'datetime', 'json', 'csv', 'random', 'collections',
        'itertools', 'functools',  'statistics', 'time', 're', 
    }
    
    # Whitelist of safe modules (available via import)
    SAFE_MODULES: Set[str] = {
        # Include all pre-imported modules
        *PRE_IMPORTED_MODULES,
        
        # Additional modules available via import
        'urllib.parse',
        
        # Data science and analysis
        'numpy', 'pandas', 'scipy', 'sklearn', 'scikit-learn',
        
        # Visualization
        'matplotlib', 'seaborn', 'plotly', 'bokeh', 'altair',
        
        # Document generation
        'fpdf', 'fpdf2', 'reportlab', 'weasyprint', 'pdfkit', 'yaml', 'pyyaml',
        
        # Image processing
        'PIL', 'Pillow', 'opencv-python', 'cv2', 'imageio', 'skimage',
        
        # HTTP requests (limited)
        'requests', 'urllib3', 'httpx',
        
        # Data formats
        'xlsxwriter', 'openpyxl', 'xlrd', 'h5py', 'tables', 'pytables',
        'sqlalchemy', 'sqlite3',
        
        # Machine learning extensions
        'tensorflow', 'torch', 'pytorch', 'keras', 'xgboost', 'lightgbm',
        'catboost', 'joblib',
        
        # Numerical and scientific computing
        'sympy', 'networkx', 'igraph', 'lxml', 'beautifulsoup4', 'bs4',
        
        # Plotting and charting
        'pygments', 'wordcloud', 'folium'
    }

    # Blacklisted modules and functions
    DANGEROUS_MODULES: Set[str] = {
        'os', 'sys', 'subprocess', 'shutil', 'pathlib',
        'socket', 'urllib.request', 'urllib.error', 'ftplib', 'smtplib',
        'poplib', 'imaplib', 'telnetlib', 'ssl', 'ctypes', 'multiprocessing',
        'threading', 'concurrent', 'importlib', 'pkgutil', 'runpy',
        'code', 'codeop', 'compile', 'exec', 'eval', '__import__'
    }

    DANGEROUS_BUILTINS: Set[str] = {
        'exec', 'eval', 'compile', 'input', 'raw_input',
        'file', 'execfile', 'reload', 'vars', 'locals', 'globals', 'dir',
        'getattr', 'setattr', 'delattr', 'hasattr'
    }

    def __init__(self, **data):
        """Initializes the SafeCodeExecutor."""
        super().__init__(**data)
        logger.info("SafeCodeExecutor initialized")

    def get_pre_imported_modules(self) -> Set[str]:
        """Get the list of modules that are pre-imported and available without explicit import."""
        return self.PRE_IMPORTED_MODULES.copy()

    def get_available_modules(self) -> Set[str]:
        """Get the list of all modules available for import."""
        return self.SAFE_MODULES.copy()

    def _is_code_safe(self, code: str) -> tuple[bool, str]:
        """Analyze code for potentially dangerous operations."""
        logger.debug(f"Analyzing code safety for {len(code)} characters of code")
        
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            logger.warning(f"Syntax error in code analysis: {e}")
            return False, f"Syntax error: {e}"

        for node in ast.walk(tree):
            # Check for imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in self.DANGEROUS_MODULES:
                        logger.warning(f"Blocked dangerous module import: {alias.name}")
                        return False, f"Dangerous module import: {alias.name}"
                    
                    # Check if module or its parent is in safe modules
                    module_parts = alias.name.split('.')
                    is_safe = False
                    for i in range(len(module_parts)):
                        parent_module = '.'.join(module_parts[:i+1])
                        if parent_module in self.SAFE_MODULES:
                            is_safe = True
                            break
                    
                    if not is_safe:
                        logger.warning(f"Blocked unauthorized module import: {alias.name}")
                        return False, f"Unauthorized module import: {alias.name}"
                    logger.debug(f"Allowed safe module import: {alias.name}")
            
            elif isinstance(node, ast.ImportFrom):
                if node.module in self.DANGEROUS_MODULES:
                    logger.warning(f"Blocked dangerous module import: {node.module}")
                    return False, f"Dangerous module import: {node.module}"
                
                if node.module:
                    # Check if module or its parent is in safe modules
                    module_parts = node.module.split('.')
                    is_safe = False
                    for i in range(len(module_parts)):
                        parent_module = '.'.join(module_parts[:i+1])
                        if parent_module in self.SAFE_MODULES:
                            is_safe = True
                            break
                    
                    if not is_safe:
                        logger.warning(f"Blocked unauthorized module import: {node.module}")
                        return False, f"Unauthorized module import: {node.module}"
                    logger.debug(f"Allowed safe module import: {node.module}")
            
            # Check for dangerous function calls
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in self.DANGEROUS_BUILTINS:
                        logger.warning(f"Blocked dangerous builtin function: {node.func.id}")
                        return False, f"Dangerous builtin function: {node.func.id}"
                elif isinstance(node.func, ast.Attribute):
                    # Check for dangerous attribute access patterns
                    if node.func.attr in ['system', 'popen', 'spawn', 'exec']:
                        logger.warning(f"Blocked dangerous method call: {node.func.attr}")
                        return False, f"Dangerous method call: {node.func.attr}"
            
            # Check for attribute access that could be dangerous
            elif isinstance(node, ast.Attribute):
                if node.attr.startswith('_'):
                    logger.warning(f"Blocked private attribute access: {node.attr}")
                    return False, f"Private attribute access not allowed: {node.attr}"

        logger.info("Code passed safety analysis")
        return True, ""

    def _detect_output_files(self, working_dir: str = ".") -> List[str]:
        """Detect files that were likely created during code execution."""
        logger.debug("Detecting output files")
        
        common_output_patterns = [
            "*.pdf", "*.png", "*.jpg", "*.jpeg", "*.gif", "*.bmp", "*.svg",
            "*.csv", "*.xlsx", "*.xls", "*.txt", "*.json", "*.xml", "*.html",
            "*.mp3", "*.wav", "*.mp4", "*.avi", "*.mov", "*.docx", "*.pptx"
        ]
        
        output_files = []
        current_time = time.time()
        
        for pattern in common_output_patterns:
            files = glob.glob(os.path.join(working_dir, pattern))
            for file_path in files:
                try:
                    # Check if file was created/modified in the last 30 seconds
                    file_stat = os.stat(file_path)
                    if (current_time - file_stat.st_mtime) < 30:  # 30 seconds threshold
                        output_files.append(file_path)
                        logger.debug(f"Detected output file: {file_path}")
                except OSError:
                    continue
        
        return output_files

    def _ensure_artifact_directory(self) -> str:
        """Ensure the artifact directory exists and return its path."""
        artifact_dir = os.path.join("artifacts", "code_executor_outputfiles")
        os.makedirs(artifact_dir, exist_ok=True)
        return artifact_dir

    def _create_safe_globals(self, code: str) -> dict[str, Any]:
        logger.debug("Creating safe globals environment")

        safe_builtins = {
            'print', 'len', 'range', 'list', 'dict', 'set', 'tuple', 'str',
            'int', 'float', 'bool', 'type', 'isinstance', 'issubclass',
            'min', 'max', 'sum', 'abs', 'round', 'sorted', 'reversed',
            'enumerate', 'zip', 'map', 'filter', 'all', 'any', 'chr', 'ord',
            'hex', 'oct', 'bin', 'repr', 'ascii', 'format', 'slice', 'open'
        }

        # Create restricted builtins
        restricted_builtins: Dict[str, Any] = {}
        import builtins
        for name in safe_builtins:
            if hasattr(builtins, name):
                restricted_builtins[name] = getattr(builtins, name)

        # Create a custom __import__ function that blocks dangerous imports
        def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
            # Check if the module is in dangerous modules
            if name in self.DANGEROUS_MODULES:
                raise ImportError(
                    f"Import of '{name}' is not allowed for security reasons"
                )

            # Check if module or its parent is in safe modules
            module_parts = name.split('.')
            is_safe = False
            for i in range(len(module_parts)):
                parent_module = '.'.join(module_parts[: i + 1])
                if parent_module in self.SAFE_MODULES:
                    is_safe = True
                    break

            if not is_safe:
                raise ImportError(f"Import of '{name}' is not authorized")

            # Use the original __import__ if safe
            return builtins.__import__(name, globals, locals, fromlist, level)

        # Add the safe __import__ function
        restricted_builtins['__import__'] = safe_import

        globals_: Dict[str, Any] = {'__builtins__': restricted_builtins}

        # Add __name__ if needed for if __name__ == '__main__' pattern
        if re.search(r"if\s+__name__\s*==\s*['\"]__main__['\"]", code):
            globals_['__name__'] = '__main__'

        # Pre-import only lightweight, commonly used modules for better performance
        pre_imported_count = 0
        for module_name in self.PRE_IMPORTED_MODULES:
            try:
                # Only add top-level module
                top_module = module_name.split('.')[0]
                if top_module not in globals_:
                    globals_[top_module] = __import__(top_module)
                    pre_imported_count += 1
            except Exception:
                # Ignore modules that fail to import
                continue

        logger.debug(
            f"Created safe globals with {len(restricted_builtins)} allowed builtins and {pre_imported_count} pre-imported modules"
        )
        return globals_

    async def execute_code(self, code: str) -> Dict[str, Any]:
        """Execute Python code securely and return a JSON-friendly payload.
        Uses cases:
        - For generating graph
        - For data manipulation and analysis
        - Complex mathematical computations
        - Image processing and manipulation
        - Document processing and analysis. For example, extracting text from PDFs or analyzing CSV files or exporting data as PDFs, docx, xlxs, txt, etc.
        - and more.

        Returns a dict with:
        - stdout: str
        - stderr: str
        - files: List[{ name, mime_type, path }]

        There are some pre-imported modules available for use. You don't need to import them explicitly. They are:
        - math, datetime, time, json, csv, random, collections, itertools, functools, statistics, re
        """

        start_time = time.time()
        code_length = len(code)
        logger.info(
            f"Starting code execution for {code_length} characters of code"
        )

        # First, check if the code is safe
        is_safe, error_msg = self._is_code_safe(code)
        if not is_safe:
            logger.error(
                f"Code execution blocked due to security violation: {error_msg}"
            )
            return {
                "stdout": (
                    "ERROR: Code execution blocked due to security violation:\n"
                    f"{error_msg}\n\nPlease modify your code to avoid security risks and try again."
                ),
                "stderr": f"Security violation: {error_msg}",
                "files": [],
            }

        logger.debug("Code Input: %s \n ----", code)

        # Capture files that exist before execution
        existing_files: Set[str] = set()
        try:
            patterns = [
                "*.pdf",
                "*.png",
                "*.jpg",
                "*.jpeg",
                "*.gif",
                "*.bmp",
                "*.svg",
                "*.csv",
                "*.xlsx",
                "*.xls",
                "*.txt",
                "*.json",
                "*.xml",
                "*.html",
                "*.mp3",
                "*.wav",
                "*.mp4",
                "*.avi",
                "*.mov",
                "*.docx",
                "*.pptx",
            ]
            for pattern in patterns:
                existing_files.update(glob.glob(pattern))
        except Exception:
            # Ignore errors in file listing
            pass

        # Execute the code
        output: str = ""
        error: str = ""
        output_files: List[OutputFile] = []

        try:
            logger.debug("Creating safe execution environment")
            globals_ = self._create_safe_globals(code)
            locals_: Dict[str, Any] = {}
            stdout = io.StringIO()

            logger.debug("Executing code in safe environment")
            execution_start = time.time()
            with redirect_stdout(stdout):
                exec(code, globals_, locals_)
            execution_time = time.time() - execution_start

            output = stdout.getvalue()
            logger.info(
                f"Code executed successfully in {execution_time:.3f}s, output length: {len(output)} characters"
            )

            # Detect new files created during execution
            new_files = self._detect_output_files()
            created_files = [f for f in new_files if f not in existing_files]

            if created_files:
                logger.info(
                    f"Detected {len(created_files)} new output files: {created_files}"
                )

                # Ensure artifact directory exists
                artifact_dir = self._ensure_artifact_directory()

                for file_path in created_files:
                    try:
                        filename = os.path.basename(file_path)

                        # Copy file to artifact directory
                        artifact_file_path = os.path.join(artifact_dir, filename)
                        shutil.copy2(file_path, artifact_file_path)

                        # Delete the original file after copying
                        try:
                            os.remove(file_path)
                            logger.debug(f"Deleted original file: {file_path}")
                        except Exception as remove_error:
                            logger.warning(
                                f"Failed to delete original file {file_path}: {remove_error}"
                            )

                        # Create OutputFile object
                        try:
                            artifact_file = OutputFile(
                                name=filename, file_path=artifact_file_path
                            )
                            output_files.append(artifact_file)
                            logger.debug(
                                f"Successfully created OutputFile for: {filename}"
                            )
                        except Exception as file_error:
                            logger.warning(
                                f"Failed to create OutputFile for {filename}: {file_error}"
                            )
                            # Continue without adding to output_files, but file is still copied to artifacts

                        logger.info(f"Saved output file to: {artifact_file_path}")
                    except Exception as file_error:
                        logger.error(
                            f"Error processing output file '{file_path}': {file_error}"
                        )

        except Exception as e:
            error = str(e)
            logger.error(f"Code execution failed with error: {error}")
            # Put the error in stdout so the agent clearly sees it as an execution failure
            output = (
                "ERROR: Code execution failed with the following error:\n"
                f"{error}\n\nPlease check your code and try again."
            )

        total_time = time.time() - start_time
        logger.info(f"Code execution completed in {total_time:.3f}s total time")

        # Build JSON-serializable payload for frontend consumption
        payload: Dict[str, Any] = {
            "stdout": output,
            "stderr": error,
            "files": [f.to_dict() for f in output_files],
        }

        logger.debug("code_execution_result: %s", payload)
        return payload

