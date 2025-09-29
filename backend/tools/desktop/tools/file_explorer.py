import win32gui
import win32com.client
import pythoncom
from urllib.parse import unquote
import time

# Cache to store the last focused Explorer window
last_explorer_path = None
last_explorer_time = 0
CACHE_TIMEOUT = 10  # Seconds to consider cached path valid

def get_active_explorer_path():
    """Get the path of the most recently active File Explorer window."""
    global last_explorer_path, last_explorer_time
    pythoncom.CoInitialize()
    shell = win32com.client.Dispatch("Shell.Application")
    explorer_windows = []

    # Collect all File Explorer windows
    for window in shell.Windows():
        if window.LocationURL.startswith("file:///"):
            hwnd = window.HWND
            path = unquote(window.LocationURL[len("file:///"):]).replace("/", "\\")
            # Get z-order (higher z-order means more recently active)
            z_order = win32gui.GetWindowLong(hwnd, -8)  # GWL_EXSTYLE
            explorer_windows.append((hwnd, path, z_order))

    if not explorer_windows:
        # Fallback to cached path if within timeout
        if last_explorer_path and (time.time() - last_explorer_time) < CACHE_TIMEOUT:
            return last_explorer_path
        return None

    # Sort by z-order (higher z-order = more recently active)
    explorer_windows.sort(key=lambda x: x[2], reverse=True)
    top_hwnd, top_path, _ = explorer_windows[0]

    # Cache the result
    last_explorer_path = top_path
    last_explorer_time = time.time()
    
    # Verify the window is still open
    if win32gui.IsWindow(top_hwnd):
        return top_path
    return None

def get_active_explorer_selected_paths():
    """Get paths of selected items in the most recently active File Explorer window."""
    global last_explorer_path, last_explorer_time
    pythoncom.CoInitialize()
    shell = win32com.client.Dispatch("Shell.Application")
    explorer_windows = []

    for window in shell.Windows():
        if window.LocationURL.startswith("file:///"):
            hwnd = window.HWND
            path = unquote(window.LocationURL[len("file:///"):]).replace("/", "\\")
            z_order = win32gui.GetWindowLong(hwnd, -8)
            explorer_windows.append((hwnd, window, z_order))

    if not explorer_windows:
        return []  # No fallback for selections; they must be current

    # Sort by z-order
    explorer_windows.sort(key=lambda x: x[2], reverse=True)
    top_hwnd, top_window, _ = explorer_windows[0]

    # Cache the path for future use
    last_explorer_path = unquote(top_window.LocationURL[len("file:///"):]).replace("/", "\\")
    last_explorer_time = time.time()

    if win32gui.IsWindow(top_hwnd):
        return [item.Path for item in top_window.Document.SelectedItems()]
    return []

if __name__ == "__main__":
    path = get_active_explorer_path()
    if path:
        print(f"Active Explorer Path: {path}")
    else:
        print("No active File Explorer window found.")

    selected_paths = get_active_explorer_selected_paths()
    if selected_paths:
        print("Selected Items:")
        for p in selected_paths:
            print(f" - {p}")
    else:
        print("No items selected or no active File Explorer window.")