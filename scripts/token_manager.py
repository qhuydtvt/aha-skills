#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path
from typing import Optional

class TokenManager:
    """Manages retrieving and providing sensitive authentication tokens safely without logging or printing values."""

    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            base_dir = Path(__file__).resolve().parent.parent
            config_path = base_dir / "configs" / "config.json"
        self._config_path = Path(config_path)

    def get_token_env_var_name(self) -> Optional[str]:
        """Retrieves the environment variable name configured for the token."""
        if not self._config_path.exists():
            return None
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            return config.get("token_env_var")
        except Exception:
            return None

    def get_token(self) -> Optional[str]:
        """Retrieves the token from the configured environment variable.
        
        CRITICAL: Never print, log, or expose the returned token string to stdout/stderr.
        """
        env_var_name = self.get_token_env_var_name()
        if not env_var_name:
            return None
        return os.environ.get(env_var_name)

    def is_token_available(self) -> bool:
        """Checks whether a non-empty token is present without exposing its value."""
        token = self.get_token()
        return bool(token and len(token.strip()) > 0)


if __name__ == "__main__":
    manager = TokenManager()
    if manager.is_token_available():
        env_var = manager.get_token_env_var_name()
        print(f"[SUCCESS] TokenManager: Token environment variable '{env_var}' is available and valid.")
    else:
        print("[WARNING] TokenManager: Token is unavailable or not set in environment.")
