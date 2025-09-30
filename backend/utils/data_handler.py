import json
import os
from typing import Dict, Any, Literal, Optional
from datetime import datetime
from schemas import Profile, SettingsItem

DATA_DIR = "data"
USER_FILE = os.path.join(DATA_DIR, "user.json")
SETTINGS_CONFIG_FILE = os.path.join(DATA_DIR, "settings.json")


def load_json(file):
    if not os.path.exists(file):
        return None
    try:
        with open(file, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return None


class DataHandlerBase:
    """Base class for data handling operations"""

    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        self.data = self.load_data()
        # callbacks to notify subscribers after data changes
        self._callbacks = []

        if not self.data:
            return None

    def load_data(self) -> dict:
        """Load data from JSON file"""
        return load_json(self.file_path) or {}

    def save_data(self, data: Dict[str, Any]) -> None:
        """Save data to JSON file"""
        with open(self.file_path, "w") as f:
            json.dump(data, f, indent=4)
        
        self.data = self.load_data()

        # Notify registered callbacks about the updated data
        for cb in getattr(self, "_callbacks", []):
            try:
                cb(self.data)
            except Exception:
                # Best-effort notify; don't fail the save if a callback errors
                continue

    def get(self, key: str, default=None):
        """Get a specific data field"""
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> bool:
        """Set a specific data field"""
        if self.data is None:
            return False
        self.data[key] = value
        self.save_data(self.data)
        return True

    def register_callback(self, func):
        """Register a callback to be invoked after the data is saved.

        The callback will be called with a single argument: the freshly loaded
        data dict.
        """
        if not hasattr(self, "_callbacks"):
            self._callbacks = []
        self._callbacks.append(func)


class UserDataHandler(DataHandlerBase):
    """Centralized handler for user data operations"""

    user_exists: bool = False

    def __init__(self) -> None:
        super().__init__(USER_FILE)
        if self.data and "id" in self.data:
            self.user_exists = True

    def update_last_active(self) -> bool:
        """Update user's last active timestamp"""
        if not self.data:
            return False

        current_time = datetime.now().isoformat()
        self.data.setdefault("profile", {})["last_active"] = current_time
        self.save_data(self.data)
        return True

    @property
    def profile(self) -> Profile:
        """Get user profile information"""
        return Profile(**self.data.get("profile", {}))

    def save_profile(self, profile: Profile) -> bool:
        """Save user profile information"""
        self.data["profile"] = profile.model_dump()
        self.save_data(self.data)
        return True


class SettingsHandler(DataHandlerBase):
    """Handler for settings configuration structure"""

    CATEGORIES = [
        "integrations",
        "general",
        "personalization",
        "configuration",
        "safety_and_security",
        "keyboard_shortcuts",
        "conversation"
    ]

    def __init__(self) -> None:
        super().__init__(SETTINGS_CONFIG_FILE)

    def get(self, key: str, default: Optional[Any] = None):
        if self.data is None:
            if default is not None:
                return default
            raise ValueError(f"Setting '{key}' not found")
        for _, items in self.data.items():
            for item in items:
                if item["key"] == key:
                    return item["value"]
        if default is not None:
            return default
        raise ValueError(f"Setting '{key}' not found")

    def set(self, key: str, value: Any) -> bool:
        if self.data is None:
            return False
        for _, items in self.data.items():
            for item in items:
                if item["key"] == key:
                    item["value"] = value
                    self.save_data(self.data)
                    return True
        return False

    def set_category(self, category: str, data) -> bool:
        if self.data is None:
            return False
        
        if isinstance(data, list):
            self.data[category] = data
        elif isinstance(data, dict):
            for key, value in data.items():
                for item in self.data.get(category, []):
                    if item["key"] == key:
                        item["value"] = value
                        break
        else:
            return False
        
        self.save_data(self.data)
        return True

    def get_category(self, category):
        if self.data is None:
            return []
        return self.data.get(category, [])
    
    def __getattr__(self, category: Literal["integrations", "general", "personalization", "configuration", "safety_and_security", "keyboard_shortcuts", "conversation"]):
        if category in self.CATEGORIES:
            return [SettingsItem(**item) for item in self.data.get(category, [])]
        raise AttributeError(f"'SettingsHandler' object has no attribute '{category}'")


class IntegrationsHandler():
    """Handler for integrations data operations"""

    def __init__(self) -> None:
        self.file_path = SETTINGS_CONFIG_FILE
        self.data = self.load_data()
        self._callbacks = []

    def load_data(self) -> dict:
        """Load data from JSON file"""
        if data := load_json(self.file_path):
            return data.get("integrations", {})
        return {}

    def register_callback(self, func):
        """Register a callback to be invoked after the integrations data is saved.

        The callback will be called with a single argument: the freshly loaded
        data dict.
        """
        self._callbacks.append(func)

    def save_data(self, data: Dict[str, Any]) -> None:
        """Save integrations data to the settings file"""
        # Load the full settings data
        full_data = load_json(self.file_path) or {}
        # Update the integrations part
        full_data["integrations"] = data
        # Save the full data
        with open(self.file_path, "w") as f:
            json.dump(full_data, f, indent=4)
        
        # Reload and notify callbacks
        self.data = self.load_data()
        for cb in self._callbacks:
            try:
                cb(self.data)
            except Exception:
                continue

    def get(self, key: str, default=None) -> Optional[Dict[str, str]]:
        result = next((item for item in self.data if item["key"] == key), None)
        if result:
            return result if type(result) is dict else None
        return default


settings = SettingsHandler()
user = UserDataHandler()
integrations = IntegrationsHandler()


