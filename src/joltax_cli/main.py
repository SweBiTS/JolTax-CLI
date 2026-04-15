"""
joltax_cli/main.py
Main entry point for the JolTax CLI application.
Initializes the configuration, loader, and starts the interactive shell.
"""

import sys
import logging
from rich.logging import RichHandler
from .config import load_config, console

# Configure global logging with RichHandler using the shared console
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(
        console=console, 
        rich_tracebacks=True, 
        show_path=False,
        omit_repeated_times=False
    )],
    force=True
)

def main() -> None:
    """
    Initializes and runs the JolTax CLI interactive shell.
    """
    try:
        # Load configuration to ensure it and the cache directory exist
        load_config()
        
        # Deferred imports to handle version/dependency errors gracefully
        from .loader import TaxonomyLoader
        from .shell import JolTaxShell
        
        # Initialize the taxonomy loader and shell
        loader = TaxonomyLoader()
        shell = JolTaxShell(loader)
        
        # Start the REPL
        shell.run()
    except ImportError as e:
        if "Incompatible joltax version" in str(e):
            print("Incompatible JolTax version, please upgrade.")
        else:
            print(f"Import Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted by user. Exiting.")
        sys.exit(0)
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
