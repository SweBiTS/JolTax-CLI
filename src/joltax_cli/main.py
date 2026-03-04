"""
joltax_cli/main.py
Main entry point for the JolTax CLI application.
Initializes the configuration, loader, and starts the interactive shell.
"""

import sys
import logging
from .loader import TaxonomyLoader
from .config import load_config
from .shell import JolTaxShell

# Set up global logging for the application
logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d [%H:%M:%S]'
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
