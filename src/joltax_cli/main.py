"""
joltax_cli/main.py
Main entry point for the JolTax CLI application.
Initializes the configuration, loader, and starts the interactive shell.
"""

import sys
import logging
from rich.logging import RichHandler
from .loader import TaxonomyLoader
from .config import load_config, console
from .shell import JolTaxShell

# Configure global logging with RichHandler using the shared console
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console, rich_tracebacks=True, show_path=False)],
    force=True
)

def main() -> None:
    """
    Initializes and runs the JolTax CLI interactive shell.
    """
    try:
        # Load configuration to ensure it and the cache directory exist
        load_config()
        
        # Initialize the taxonomy loader and shell
        loader = TaxonomyLoader()
        shell = JolTaxShell(loader)
        
        # Start the REPL
        shell.run()
    except KeyboardInterrupt:
        print("\nInterrupted by user. Exiting.")
        sys.exit(0)
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
