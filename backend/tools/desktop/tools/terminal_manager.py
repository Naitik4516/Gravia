from __future__ import annotations

import os
import time
import re
import threading
import subprocess
from dataclasses import dataclass, field
from shutil import which
from typing import Dict, List, Optional, Tuple, Literal


def _is_windows() -> bool:
	return os.name == "nt"


def _default_shell() -> Literal["pwsh", "powershell", "cmd", "bash"]:
	# Prefer PowerShell Core if available on Windows, else Windows PowerShell, else cmd
	if _is_windows():
		if which("pwsh") or which("pwsh.exe"):
			return "pwsh"
		if which("powershell") or which("powershell.exe"):
			return "powershell"
		return "cmd"
	# Non-Windows: prefer bash
	return "bash"


def _build_command(shell: Optional[str], command: str) -> List[str]:
	"""Build the subprocess command line for the selected shell.

	Accepts:
	- shell: "pwsh", "powershell", "cmd", "bash", or an absolute path to an executable.
	- command: the raw command string to run inside the shell.
	"""
	s = (shell or _default_shell()).lower()

	# Direct path to a shell
	if os.path.isabs(shell or "") or (shell and shell.endswith(".exe")):
		# At this point shell is a non-empty string due to the condition above
		return [shell or "", command]

	if s in ("pwsh", "powershell"):
		exe = "pwsh.exe" if s == "pwsh" else "powershell.exe"
		return [exe, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", command]
	if s == "cmd":
		exe = "cmd.exe" if _is_windows() else "sh"
		return [exe, "/C" if _is_windows() else "-c", command]
	if s == "bash":
		exe = "bash"
		return [exe, "-lc", command]

	# Fallback to system default if an unknown label was provided
	ds = _default_shell()
	return _build_command(ds, command)


def _default_block_patterns() -> List[re.Pattern]:
	"""Dangerous command patterns blocked by default.
	Patterns are case-insensitive and aim to catch destructive or privileged operations.
	"""
	patterns: List[str] = [
		r"\bshutdown\b|\breboot\b|\bpoweroff\b|\bhalt\b",
		r"\bformat\b|\bmkfs\b|\bchkdsk\b /f",
		r"\bdd\s+if=|\bdd\s+of=",
		r"rm\s+-rf\s+/|rm\s+-rf\s+\\|rd\s+/s\s+/q\s+\\",
		r"\brmdir\b\s+/s\s+/q",
		r"\bdel\b\s+/f\s+/s\s+/q\s+",
		r"\bdiskpart\b|\bbcdedit\b",
		r"\bnet\s+user\b|\buserdel\b|\bnetsh\b",
		r"\breg\s+delete\b",
		r":\(\)\{\s*:\|:&\s*\};:",  # fork bomb
		r"\bchmod\b\s+\d{3}\s+/(\s|$)",
		r"\bchown\b\s+-R\s+root:\w+\s+/",
		r"\bmount\b|\bumount\b",
		r"\bwget\b.*\|\s*sh\b|\bcurl\b.*\|\s*sh\b",
		r"\bschtasks\b\s+/delete\b|\bsc\b\s+delete\b",
	]
	return [re.compile(p, re.IGNORECASE) for p in patterns]


def _compile_extra_blocklist(extra: Optional[List[str]]) -> List[re.Pattern]:
	compiled: List[re.Pattern] = []
	if not extra:
		return compiled
	for item in extra:
		try:
			compiled.append(re.compile(item, re.IGNORECASE))
		except re.error:
			# Treat as literal substring if not a valid regex
			compiled.append(re.compile(re.escape(item), re.IGNORECASE))
	return compiled


def _is_blocked(command: str, extra_blocklist: Optional[List[str]] = None) -> Tuple[bool, str]:
	for pat in _default_block_patterns() + _compile_extra_blocklist(extra_blocklist):
		if pat.search(command):
			return True, f"Command blocked by policy: matches pattern '{pat.pattern}'"
	return False, ""


@dataclass
class TerminalSession:
	pid: int
	process: subprocess.Popen
	command: str
	shell: str
	start_time: float = field(default_factory=time.time)
	stdout_buf: str = ""
	stderr_buf: str = ""
	out_off: int = 0
	err_off: int = 0
	lock: threading.Lock = field(default_factory=threading.Lock)
	out_thread: Optional[threading.Thread] = None
	err_thread: Optional[threading.Thread] = None

	def is_running(self) -> bool:
		return self.process.poll() is None

	def append_stdout(self, data: str) -> None:
		with self.lock:
			self.stdout_buf += data

	def append_stderr(self, data: str) -> None:
		with self.lock:
			self.stderr_buf += data

	def read_new(self) -> Tuple[str, str]:
		with self.lock:
			out = self.stdout_buf[self.out_off :]
			err = self.stderr_buf[self.err_off :]
			self.out_off = len(self.stdout_buf)
			self.err_off = len(self.stderr_buf)
		return out, err


class TerminalManager:
	def __init__(self) -> None:
		self._sessions: Dict[int, TerminalSession] = {}
		self._sessions_lock = threading.Lock()

	def _start_reader_threads(self, session: TerminalSession) -> None:
		def reader(stream, append_fn):
			try:
				# Read in reasonably sized chunks to preserve partial lines
				while True:
					data = stream.readline()
					if not data:
						break
					append_fn(data)
			except Exception as e:
				append_fn(f"\n[reader-error] {e}\n")
			finally:
				try:
					stream.close()
				except Exception:
					pass

		# stdout thread
		session.out_thread = threading.Thread(
			target=reader, args=(session.process.stdout, session.append_stdout), daemon=True
		)
		session.out_thread.start()

		# stderr thread
		session.err_thread = threading.Thread(
			target=reader, args=(session.process.stderr, session.append_stderr), daemon=True
		)
		session.err_thread.start()

	def _register_session(self, proc: subprocess.Popen, command: str, shell: str) -> TerminalSession:
		sess = TerminalSession(pid=proc.pid, process=proc, command=command, shell=shell)
		with self._sessions_lock:
			self._sessions[sess.pid] = sess
		self._start_reader_threads(sess)
		return sess

	def _launch_process(self, shell: Optional[str], command: str) -> Tuple[subprocess.Popen, str]:
		cmd = _build_command(shell, command)

		# Validate executable presence
		exe = cmd[0]
		if not which(exe) and not os.path.isabs(exe):
			raise FileNotFoundError(f"Shell executable not found: {exe}")

		# Text mode with UTF-8 ensures robust decoding
		proc = subprocess.Popen(
			cmd,
			stdout=subprocess.PIPE,
			stderr=subprocess.PIPE,
			stdin=subprocess.DEVNULL,
			bufsize=1,
			universal_newlines=True,
			encoding="utf-8",
			errors="replace",
			creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP if _is_windows() else 0),
		)
		return proc, cmd[0]

	def execute_command(
		self,
		command: str,
		timeout_s: int = 60,
		shell: Optional[str] = None,
		background: bool = False,
		blocked_commands: Optional[List[str]] = None,
		startup_timeout_s: float = 0.2,
	) -> Dict[str, object]:
		"""Execute a command with optional timeout and background mode.

		Returns dict with keys:
		- pid: int
		- is_running: bool
		- stdout: str
		- stderr: str
		- returncode: Optional[int]
		- timeout: bool (True if still running after timeout in foreground mode)

		Parameters:
		- timeout_s: Max seconds to wait in foreground mode before returning with timeout=True.
		- background: If True, return immediately (after a very short startup window) with PID and any initial output.
		- startup_timeout_s: Only used when background=True. Small window to collect initial output before returning. Defaults to 0.2s.
		"""

		is_blocked, reason = _is_blocked(command, blocked_commands)
		if is_blocked:
			raise PermissionError(reason)

		proc, resolved_shell = self._launch_process(shell or _default_shell(), command)
		sess = self._register_session(proc, command, resolved_shell)

		# No foreground deadline tracking needed for background path; foreground uses wait(timeout_s)

		def collect_now() -> Tuple[str, str]:
			# Give reader threads a tiny slice for immediate data
			time.sleep(0.02)
			out, err = sess.read_new()
			return out, err

		# Background: collect initial output until timeout then return
		if background:
			# Use a very short window just to allow process startup and capture any immediate output.
			# This must NOT use the foreground timeout value.
			end = time.time() + max(0.0, float(startup_timeout_s))
			while time.time() < end:
				time.sleep(0.03)
			out, err = collect_now()
			return {
				"pid": sess.pid,
				"is_running": sess.is_running(),
				"stdout": out,
				"stderr": err,
				"returncode": None if sess.is_running() else sess.process.returncode,
				"timeout": False,
			}

		# Foreground (blocking up to timeout)
		try:
			proc.wait(timeout=max(0.01, timeout_s))
			# Give threads time to flush remaining lines
			time.sleep(0.05)
			out, err = sess.read_new()
			return {
				"pid": sess.pid,
				"is_running": False,
				"stdout": out,
				"stderr": err,
				"returncode": proc.returncode,
				"timeout": False,
			}
		except subprocess.TimeoutExpired:
			# Do not kill; leave running in background and return initial output
			out, err = collect_now()
			return {
				"pid": sess.pid,
				"is_running": True,
				"stdout": out,
				"stderr": err,
				"returncode": None,
				"timeout": True,
			}

	def read_output(self, pid: int) -> Dict[str, object]:
		with self._sessions_lock:
			sess = self._sessions.get(pid)
		if not sess:
			raise ValueError(f"No session found for PID {pid}")
		out, err = sess.read_new()
		return {
			"pid": pid,
			"is_running": sess.is_running(),
			"stdout": out,
			"stderr": err,
			"returncode": None if sess.is_running() else sess.process.returncode,
		}

	def force_terminate(self, pid: int) -> bool:
		with self._sessions_lock:
			sess = self._sessions.get(pid)
		if not sess:
			return False
		try:
			if _is_windows():
				# Send CTRL-BREAK equivalent to process group when possible, else kill
				try:
					sess.process.terminate()
				except Exception:
					pass
				# Ensure exit
				time.sleep(0.3)
				if sess.is_running():
					sess.process.kill()
			else:
				sess.process.terminate()
				try:
					sess.process.wait(timeout=1.0)
				except subprocess.TimeoutExpired:
					sess.process.kill()
			return True
		finally:
			# Cleanup if finished
			if not sess.is_running():
				with self._sessions_lock:
					self._sessions.pop(pid, None)

	def list_active_sessions(self) -> List[Dict[str, object]]:
		now = time.time()
		items: List[Dict[str, object]] = []
		with self._sessions_lock:
			pids = list(self._sessions.keys())
		for pid in pids:
			sess = self._sessions.get(pid)
			if not sess:
				continue
			items.append(
				{
					"pid": pid,
					"command": sess.command,
					"shell": sess.shell,
					"seconds_running": max(0.0, now - sess.start_time),
					"is_running": sess.is_running(),
				}
			)
		return items


_TERMINAL_MANAGER_SINGLETON: Optional[TerminalManager] = None


def get_terminal_manager() -> TerminalManager:
	global _TERMINAL_MANAGER_SINGLETON
	if _TERMINAL_MANAGER_SINGLETON is None:
		_TERMINAL_MANAGER_SINGLETON = TerminalManager()
	return _TERMINAL_MANAGER_SINGLETON


