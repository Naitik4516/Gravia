from typing import Any, Dict, Optional, Literal
from agno.tools import Toolkit
from utils.data_handler import settings

from .tools import (
    sys_info,
    terminal_manager as tm,
    filesystem,
    process
)

terminal_manager = tm.get_terminal_manager()

class DesktopTools(Toolkit):
    """
    Toolkit for desktop-related operations.
    
    Provides methods for executing commands, reading/writing files, managing processes, and more.
    """
    
    def __init__(self, **kwargs):
        super().__init__(
            name="desktop_tools", 
            tools=[
                self.execute_command, self.read_output, self.force_terminate, self.list_sessions,
                self.list_processes, self.kill_process, self.read_file, self.write_file,
                self.list_directory, self.create_directory, self.move_file, self.search_files,
                self.get_file_info, self.get_sys_info
            ],
            **kwargs
        )
    

    async def execute_command(self, command: str, timeout_s: int = 60, shell: Optional[str] = None, background: bool = False, blocked_commands: Optional[list[str]] = None) -> Dict[str, Any]:
        """
        Executes a terminal command.

        The command can be run in the foreground or background. If the command does not complete within the timeout, it will continue running in the background, and its output can be retrieved later using `read_output`.

        Args:
            command (str): The command to execute.
            timeout_s (int): The number of seconds to wait for initial output before returning. async defaults to 60.
            shell (Optional[str]): The shell to use (e.g., 'bash', 'zsh', 'powershell', 'pwsh'). async defaults to the value in the server configuration.

        Returns:
            Dict[str, Any]: A dictionary containing the process ID (pid), a boolean 'is_blocked' indicating if the command is still running, and any initial output.
        """
        try:
            # Default to PowerShell on Windows if shell not provided
            # Default shell and blocklist from settings when not provided
            resolved_shell = shell or settings.get("default_shell", None) or None
            resolved_blocked = blocked_commands if blocked_commands is not None else settings.get("blocked_commands", [])

            result = terminal_manager.execute_command(
                command=command,
                timeout_s=timeout_s,
                shell=resolved_shell,  # terminal_manager will pick sensible default if None
                background=background,
                blocked_commands=resolved_blocked,
            )
            return {"status": "success", "result": result}
        except Exception as e:
            return {"status": "error", "error_message": str(e)}

    async def read_output(self, pid: int) -> Dict[str, Any]:
        """
        Reads new output from a running or completed terminal session.

        Use this tool to get updates from commands started with `execute_command` that are still running, or to get the final output from a command that has finished.

        Args:
            pid (int): The process ID of the command, obtained from `execute_command`.

        Returns:
            Dict[str, Any]: A dictionary containing the new output and a boolean 'is_running' indicating if the process is still active.
        """
        try:
            result = terminal_manager.read_output(pid)
            return {"status": "success", "result": result}
        except Exception as e:
            return {"status": "error", "error_message": str(e)}

    async def force_terminate(self, pid: int) -> Dict[str, Any]:
        """
        Forcibly terminates a running terminal session by its process ID.
        """
        try:
            success = terminal_manager.force_terminate(pid)
            if success:
                return {"status": "success", "result": f"Successfully initiated termination of session {pid}."}
            else:
                return {"status": "error", "error_message": f"No active session found for PID {pid}."}
        except Exception as e:
            return {"status": "error", "error_message": str(e)}

    async def list_sessions(self) -> Dict[str, Any]:
        """
        Lists all active, long-running terminal sessions.
        """
        try:
            sessions = terminal_manager.list_active_sessions()
            if not sessions:
                return {"status": "success", "result": "No active sessions."}
            return {"status": "success", "result": sessions}
        except Exception as e:
            return {"status": "error", "error_message": str(e)}

    async def list_processes(self) -> Dict[str, Any]:
        """
        Lists all running system processes with details like PID, name, CPU, and memory usage.
        """
        try:
            return {"status": "success", "result": process.list_processes()}
        except Exception as e:
            return {"status": "error", "error_message": str(e)}

    async def kill_process(self, pid: int) -> Dict[str, Any]:
        """
        Terminates a running process by its PID.
        """
        try:
            process.kill_process(pid)
            return {"status": "success", "result": f"Successfully sent termination signal to process {pid}."}
        except Exception as e:
            return {"status": "error", "error_message": str(e)}

    async def read_file(self, path: str, offset: int = 0, length: Optional[int] = None) -> Dict[str, Any]:
        """
        Reads content from a local file. Supports line-based pagination.

        For local files, a negative offset will read from the end of the file (e.g., offset=-100 reads the last 100 lines).

        Args:
            path (str): The local file path to read from.
            offset (int): The starting line number (0-indexed). Negative for tail behavior. async defaults to 0.
            length (Optional[int]): The maximum number of lines to read. async defaults to the 'fileReadLineLimit' from config.

        Returns:
            Dict[str, Any]: A dictionary containing the file's content.
        """
        try:
            content = filesystem.read_file(path, offset, length)
            return {"status": "success", "result": content}
        except Exception as e:
            return {"status": "error", "error_message": str(e)}

    async def write_file(self, path: str, content: str, mode: Literal['rewrite', 'append'] = 'rewrite') -> Dict[str, Any]:
        """
        Writes content to a local file.

        Can either overwrite the entire file or append to the end of it.

        Args:
            path (str): The path of the file to write to.
            content (str): The content to write into the file.
            mode (Literal['rewrite', 'append']): The write mode. 'rewrite' overwrites the file, 'append' adds to it. async defaults to 'rewrite'.

        Returns:
            Dict[str, Any]: A dictionary with a confirmation message.

        """
        try:
            filesystem.write_file(path, content, mode)
            message = f"Successfully wrote to {path}." if mode == 'rewrite' else f"Successfully appended to {path}."
            return {"status": "success", "result": message}
        except Exception as e:
            return {"status": "error", "error_message": str(e)}

    async def list_directory(self, path: str) -> Dict[str, Any]:
        """
        Gets a detailed listing of files and subdirectories at a given path.

        Prefixes entries with `[DIR]` for directories and `[FILE]` for files.

        Args:
            path (str): The directory path to inspect.

        Returns:
            Dict[str, Any]: A list of strings, where each string is an entry in the directory.
        """
        try:
            return {"status": "success", "result": filesystem.list_directory(path)}
        except Exception as e:
            return {"status": "error", "error_message": str(e)}

    async def create_directory(self, path: str) -> Dict[str, Any]:
        """
        Creates a new directory. Ensures all parent directories exist.

        Args:
            path (str): The full path of the directory to create.

        Returns:
            Dict[str, Any]: A dictionary with a confirmation message.
        """
        try:
            filesystem.create_directory(path)
            return {"status": "success", "result": f"Directory '{path}' created or already exists."}
        except Exception as e:
            return {"status": "error", "error_message": str(e)}

    async def move_file(self, source: str, destination: str) -> Dict[str, Any]:
        """
        Moves or renames a file or directory.

        Args:
            source (str): The original path of the file/directory.
            destination (str): The new path for the file/directory.

        Returns:
            Dict[str, Any]: A dictionary with a confirmation message.
        """
        try:
            filesystem.move_file(source, destination)
            return {"status": "success", "result": f"Successfully moved '{source}' to '{destination}'."}
        except Exception as e:
            return {"status": "error", "error_message": str(e)}

    async def search_files(self, path: str, pattern: str) -> Dict[str, Any]:
        """

        Finds files by name within a directory using case-insensitive substring matching.

        Args:
            path (str): The root directory to start the search from.
            pattern (str): The case-insensitive substring to match in file names.

        Returns:
            Dict[str, Any]: A list of file paths that match the pattern.
        """
        try:
            return {"status": "success", "result": filesystem.search_files(path, pattern)}
        except Exception as e:
            return {"status": "error", "error_message": str(e)}

    async def get_file_info(self, path: str) -> Dict[str, Any]:
        """
        Retrieves detailed metadata about a file or directory.

        Information includes size, creation/modification times, and line count for text files.

        Args:
            path (str): The path to the file or directory.

        Returns:
            Dict[str, Any]: A dictionary containing the file's metadata.
        """
        try:
            return {"status": "success", "result": filesystem.get_file_info(path)}
        except Exception as e:
            return {"status": "error", "error_message": str(e)}
        
    async def get_sys_info(self):
        """
        Retrieves system information such as CPU, RAM, OS, storage/drives, displays, GPU and inferred PC type.
        Returns:
            Dict[str, Any]: A dictionary containing system metrics.
        """
        async for info in sys_info.get_pc_info():
            yield info


  
