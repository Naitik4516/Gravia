import os
import psutil
import signal

def list_processes():
    """Lists running processes using psutil for cross-platform compatibility."""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_info']):
        try:
            processes.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return processes

def kill_process(pid: int):
    """Kills a process by PID."""
    try:
        proc = psutil.Process(pid)
        proc.send_signal(signal.SIGTERM) # More graceful than SIGKILL
        return True
    except psutil.NoSuchProcess:
        raise ValueError(f"Process with PID {pid} not found.")
    except psutil.AccessDenied:
        raise PermissionError(f"Permission denied to kill process with PID {pid}.")