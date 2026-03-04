"""
joltax_cli/config.py
Configuration management for the JolTax CLI.
Handles loading and saving of the user configuration file.
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any

# Set up logging for the module
logger = logging.getLogger(__name__)

DEFAULT_CONFIG_DIR: Path = Path.home() / ".config" / "joltax"
DEFAULT_CONFIG_FILE: Path = DEFAULT_CONFIG_DIR / "config.yaml"
DEFAULT_CACHE_DIR: Path = DEFAULT_CONFIG_DIR / "cache"

def load_config() -> Dict[str, Any]:
    """
    Loads configuration from the default config file.
    
    If the config file does not exist, it creates a default one.
    Ensures that essential keys like 'cache_dir' are present.

    Returns:
        Dict[str, Any]: The configuration dictionary.
    """
    if not DEFAULT_CONFIG_FILE.exists():
        return create_default_config()
    
    try:
        with open(DEFAULT_CONFIG_FILE, "r") as f:
            config = yaml.safe_load(f)
            if config is None:
                config = {}
    except (yaml.YAMLError, OSError) as e:
        logger.error(f"Failed to load config file: {e}")
        config = {}
            
    # Ensure cache directory is present in config
    if "cache_dir" not in config:
        config["cache_dir"] = str(DEFAULT_CACHE_DIR)
        save_config(config)
        
    return config

def save_config(config: Dict[str, Any]) -> None:
    """
    Saves the configuration dictionary to the default config file.

    Args:
        config: The configuration dictionary to save.
    """
    try:
        DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(DEFAULT_CONFIG_FILE, "w") as f:
            yaml.safe_dump(config, f)
    except OSError as e:
        logger.error(f"Failed to save config file: {e}")

def create_default_config() -> Dict[str, Any]:
    """
    Creates a default configuration file and returns the default config dict.

    Returns:
        Dict[str, Any]: The default configuration dictionary.
    """
    config = {
        "cache_dir": str(DEFAULT_CACHE_DIR)
    }
    save_config(config)
    # Also ensure the default cache dir exists
    try:
        Path(config["cache_dir"]).mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.error(f"Failed to create default cache directory: {e}")
    return config

def get_cache_dir() -> Path:
    """
    Returns the cache directory path from the configuration.
    
    Ensures the directory exists before returning.

    Returns:
        Path: The path to the taxonomy cache directory.
    """
    config = load_config()
    cache_dir = Path(config["cache_dir"])
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.error(f"Failed to create cache directory {cache_dir}: {e}")
    return cache_dir
