"""
joltax_cli/config.py
Configuration management for the JolTax CLI.
Handles loading, saving, and the initial setup wizard for user configuration.
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from rich.console import Console
from rich.prompt import Prompt, Confirm

# Set up logging for the module
logger = logging.getLogger(__name__)

DEFAULT_CONFIG_DIR: Path = Path.home() / ".joltax-cli"
DEFAULT_CONFIG_FILE: Path = DEFAULT_CONFIG_DIR / "config.yaml"
DEFAULT_CACHE_DIR: Path = DEFAULT_CONFIG_DIR / "cache"

def validate_cache_dir(path: Path) -> bool:
    """
    Validates if a directory can be used as a cache.
    Checks if it exists or can be created, and if it's writable.

    Args:
        path: The directory path to validate.

    Returns:
        bool: True if valid, False otherwise.
    """
    try:
        # Check if it exists or can be created
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
        
        # Check if writable by creating a temporary file
        temp_file = path / ".joltax_write_test"
        temp_file.touch()
        temp_file.unlink()
        return True
    except (OSError, PermissionError) as e:
        logger.error(f"Cache directory validation failed for {path}: {e}")
        return False

def setup_wizard(force: bool = False) -> Dict[str, Any]:
    """
    Runs an interactive setup wizard to configure the cache directory.
    
    Informs the user about cache size and asks for confirmation or a new path.

    Args:
        force: If True, skips the check for 'setup_complete' and runs anyway.

    Returns:
        Dict[str, Any]: The updated configuration dictionary.
    """
    console = Console()
    # Load raw config without triggering the wizard recursively
    config = _load_raw_config()
    
    if config.get("setup_complete") and not force:
        return config

    console.print("\n[bold blue]Welcome to JolTax-CLI![/bold blue]")
    console.print(
        "JolTax uses [bold]vectorized binary caches[/bold] to provide high-performance "
        "taxonomy exploration. These caches (e.g., NCBI) can be quite large, "
        "potentially taking up [yellow]several gigabytes[/yellow] of disk space."
    )
    
    current_cache = Path(config.get("cache_dir", str(DEFAULT_CACHE_DIR)))
    console.print(f"\nCurrent cache directory: [cyan]{current_cache}[/cyan]")
    
    if Confirm.ask("Are you okay with this location?"):
        new_cache = current_cache
    else:
        while True:
            path_str = Prompt.ask("Enter a new absolute path for the cache directory")
            new_cache = Path(path_str).expanduser().resolve()
            
            if validate_cache_dir(new_cache):
                break
            else:
                console.print(f"[red]Error:[/red] Cannot use '{new_cache}'. Please check permissions or path validity.")

    config["cache_dir"] = str(new_cache)
    config["setup_complete"] = True
    save_config(config)
    
    console.print(f"[green]Configuration saved![/green] Cache will be stored in: [cyan]{new_cache}[/cyan]\n")
    return config

def _load_raw_config() -> Dict[str, Any]:
    """Internal helper to load config without triggering the wizard."""
    if not DEFAULT_CONFIG_FILE.exists():
        return {
            "cache_dir": str(DEFAULT_CACHE_DIR),
            "setup_complete": False
        }
    
    try:
        with open(DEFAULT_CONFIG_FILE, "r") as f:
            config = yaml.safe_load(f)
            return config if config is not None else {}
    except (yaml.YAMLError, OSError):
        return {}

def load_config() -> Dict[str, Any]:
    """
    Loads configuration from the default config file.
    
    Triggers the setup wizard if 'setup_complete' is missing.

    Returns:
        Dict[str, Any]: The configuration dictionary.
    """
    config = _load_raw_config()
            
    # Ensure cache directory is present in config
    if "cache_dir" not in config:
        config["cache_dir"] = str(DEFAULT_CACHE_DIR)
        save_config(config)
        
    if not config.get("setup_complete"):
        config = setup_wizard()
        
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
    Creates a default configuration file.

    Returns:
        Dict[str, Any]: The default configuration dictionary.
    """
    config = {
        "cache_dir": str(DEFAULT_CACHE_DIR),
        "setup_complete": False
    }
    save_config(config)
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
