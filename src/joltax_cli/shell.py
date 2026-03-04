"""
joltax_cli/shell.py
Interactive shell implementation for JolTax.
Handles the REPL loop, command parsing, and output management.
"""

import sys
import logging
from typing import Optional, List, Union, Any
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm

from .loader import TaxonomyLoader, JolTree
from .formatter import format_dataframe, format_lineage, format_find_results
from .completer import JolTaxCompleter
from .config import setup_wizard, DEFAULT_CONFIG_DIR, load_config, save_config

# Set up logging for the module
logger = logging.getLogger(__name__)

class JolTaxShell:
    """
    The main interactive shell for exploring JolTax taxonomies.
    
    Attributes:
        loader (TaxonomyLoader): The loader for fetching and building taxonomies.
        completer (JolTaxCompleter): The auto-completer for the shell.
        session (PromptSession): The prompt-toolkit session for managing input.
        console (Console): The Rich console for styled output.
        current_tree (Optional[JolTree]): The currently active taxonomy tree.
        current_name (Optional[str]): The name of the currently active taxonomy.
    """

    def __init__(self, loader: TaxonomyLoader):
        """
        Initializes the shell with a taxonomy loader and persistent history.

        Args:
            loader: The loader instance for managing taxonomy data.
        """
        self.loader: TaxonomyLoader = loader
        self.completer: JolTaxCompleter = JolTaxCompleter(loader)
        
        # Path for persistent history
        history_path = DEFAULT_CONFIG_DIR / "history"
        
        self.session: PromptSession = PromptSession(
            history=FileHistory(str(history_path)),
            completer=self.completer
        )
        self.console: Console = Console()
        self.current_tree: Optional[JolTree] = None
        self.current_name: Optional[str] = None

    def get_prompt(self) -> str:
        """
        Generates the dynamic shell prompt based on the loaded taxonomy.

        Returns:
            str: The prompt string.
        """
        if self.current_name:
            return f"joltax({self.current_name})> "
        return "joltax> "

    def run(self) -> None:
        """
        Starts the main interactive shell loop.
        
        Handles user input, dispatches commands, and catches exceptions.
        """
        self.console.print("[bold blue]JolTax-CLI Interactive Shell[/bold blue]")
        self.console.print("Type 'help' for commands, 'exit' or Ctrl+D to quit.")

        # Auto-load the last used taxonomy from config
        config = load_config()
        last_tax = config.get("last_taxonomy")
        if last_tax:
            # Check if it actually exists in cache before trying to load it
            if last_tax in self.loader.list_available_taxonomies():
                self.console.print(f"Auto-loading last used taxonomy: [cyan]{last_tax}[/cyan]")
                self.handle_use([last_tax], silent=True)

        while True:
            try:
                user_input: str = self.session.prompt(self.get_prompt()).strip()
                if not user_input:
                    continue

                parts: List[str] = user_input.split()
                command: str = parts[0].lower()
                args: List[str] = parts[1:]

                if command in ("exit", "quit"):
                    break
                elif command == "help":
                    self.show_help()
                elif command == "use":
                    self.handle_use(args)
                elif command == "build":
                    self.handle_build(args)
                elif command == "remove":
                    self.handle_remove(args)
                elif command == "summary":
                    self.handle_summary()
                elif command == "annotate":
                    self.handle_annotate(args)
                elif command == "find":
                    self.handle_find(args)
                elif command == "lineage":
                    self.handle_lineage(args)
                elif command == "config":
                    self.handle_config()
                else:
                    self.console.print(f"[red]Unknown command: {command}[/red]")

            except KeyboardInterrupt:
                continue
            except EOFError:
                break
            except Exception as e:
                self.console.print(f"[red]Error:[/red] {e}")
                logger.exception("An unexpected error occurred in the shell loop.")

        self.console.print("Goodbye!")

    def show_help(self) -> None:
        """Displays a formatted table of available commands."""
        table = Table(title="Available Commands", box=None)
        table.add_column("Command", style="cyan")
        table.add_column("Description", style="white")
        table.add_row("use <name>", "Load a taxonomy from the cache directory.")
        table.add_row("build <name> <dir> [names_dmp]", "Build and save a taxonomy from NCBI DMP files.")
        table.add_row("remove <name>", "Permanently delete a cached taxonomy from the disk.")
        table.add_row("summary", "Show summary information for the currently loaded taxonomy.")
        table.add_row("annotate <id>...", "Pretty-print canonical ranks for one or more tax IDs.")
        table.add_row("find <query>", "Fuzzy search for tax IDs by name.")
        table.add_row("lineage <id>", "Display the lineage of a tax ID as a visual tree.")
        table.add_row("config", "Re-run the setup wizard to configure the cache directory.")
        table.add_row("help", "Show this help message.")
        table.add_row("exit / quit", "Exit the interactive shell.")
        self.console.print(table)

    def _ensure_loaded(self) -> bool:
        """
        Helper to check if a taxonomy is currently loaded.

        Returns:
            bool: True if loaded, False otherwise.
        """
        if not self.current_tree:
            self.console.print("[yellow]No taxonomy loaded. Use 'use <name>' first.[/yellow]")
            return False
        return True

    def handle_build(self, args: List[str]) -> None:
        """
        Handles the 'build' command to create a new taxonomy cache.

        Args:
            args: Command arguments [name, path, optional_names_path].
        """
        if len(args) < 2:
            self.console.print(
                "[yellow]Usage: build <name> <tax_dir> OR build <name> <nodes.dmp> <names.dmp>[/yellow]"
            )
            return
            
        name: str = args[0]
        arg1: str = args[1]
        arg2: Optional[str] = args[2] if len(args) > 2 else None
        
        with self.console.status(f"[bold green]Building taxonomy cache '{name}'... This may take a moment."):
            try:
                tax_path = self.loader.build_taxonomy(name, arg1, arg2)
                self.console.print(
                    f"[green]Successfully built and saved taxonomy '{name}' to {tax_path}.[/green]"
                )
                self.console.print(f"You can now load it using: [cyan]use {name}[/cyan]")
            except Exception as e:
                self.console.print(f"[red]Error building taxonomy:[/red] {e}")
                logger.error(f"Build failed for taxonomy '{name}': {e}")

    def handle_use(self, args: List[str], silent: bool = False) -> None:
        """
        Handles the 'use' command to switch taxonomies.

        Args:
            args: Command arguments [name]. If empty, lists available taxonomies.
            silent: If True, suppresses non-error output (used for auto-load).
        """
        if not args:
            taxonomies: List[str] = self.loader.list_available_taxonomies()
            if not taxonomies:
                self.console.print("[yellow]No taxonomies found in cache.[/yellow]")
            else:
                self.console.print("Available taxonomies:")
                for tax in taxonomies:
                    self.console.print(f"  - {tax}")
            return

        name: str = args[0]
        if not silent:
            self.console.print(f"Loading taxonomy '{name}'...")
        
        tree = self.loader.load_taxonomy(name)
        if tree:
            self.current_tree = tree
            self.current_name = name
            # Update completer with ranks from the new taxonomy
            ranks: List[str] = getattr(tree, 'available_ranks', [])
            self.completer.set_available_ranks(ranks)
            
            # Save as last used taxonomy in config
            config = load_config()
            config["last_taxonomy"] = name
            save_config(config)
            
            if not silent:
                self.console.print(f"[green]Successfully loaded '{name}'.[/green]")

    def handle_remove(self, args: List[str]) -> None:
        """
        Handles the 'remove' command to delete a taxonomy from the cache.

        Args:
            args: Command arguments [name].
        """
        if not args:
            self.console.print("[yellow]Usage: remove <name>[/yellow]")
            return

        name: str = args[0]
        
        # Check if it exists first
        taxonomies = self.loader.list_available_taxonomies()
        if name not in taxonomies:
            self.console.print(f"[red]Error:[/red] Taxonomy '{name}' not found in cache.")
            return

        # Confirm deletion
        if not Confirm.ask(f"Are you sure you want to [bold red]permanently delete[/bold red] '{name}'?"):
            self.console.print("Operation cancelled.")
            return

        try:
            if self.loader.remove_taxonomy(name):
                self.console.print(f"[green]Successfully removed '{name}' from cache.[/green]")
                
                # Clear last_taxonomy from config if it was the one removed
                config = load_config()
                if config.get("last_taxonomy") == name:
                    config.pop("last_taxonomy", None)
                    save_config(config)

                # If the removed taxonomy was currently loaded, reset the state
                if self.current_name == name:
                    self.current_tree = None
                    self.current_name = None
                    self.completer.set_available_ranks([])
                    self.console.print("[yellow]The currently loaded taxonomy has been removed. State reset.[/yellow]")
            else:
                self.console.print(f"[red]Error:[/red] Could not find taxonomy '{name}' to remove.")
        except Exception as e:
            self.console.print(f"[red]Error removing taxonomy:[/red] {e}")
            logger.error(f"Remove failed for taxonomy '{name}': {e}")

    def handle_summary(self) -> None:
        """Handles the 'summary' command to show info about the active taxonomy."""
        if not self._ensure_loaded():
            return

        self.console.print(f"[bold underline]Taxonomy Summary: {self.current_name}[/bold underline]")
        
        # Access actual properties of JolTree if available
        ranks: List[str] = getattr(self.current_tree, 'available_ranks', [])
        self.console.print(f"Available ranks: [cyan]{', '.join(ranks)}[/cyan]")
        
        if hasattr(self.current_tree, 'node_count'):
            self.console.print(f"Node count: {self.current_tree.node_count}")

    def handle_annotate(self, args: List[str]) -> None:
        """
        Handles the 'annotate' command for mass-lookup of tax IDs.

        Args:
            args: One or more taxonomic IDs.
        """
        if not self._ensure_loaded():
            return
        if not args:
            self.console.print("[yellow]Usage: annotate <tax_id> [tax_id...][/yellow]")
            return

        try:
            # Convert string IDs to integers (or leave as strings if JolTree supports both)
            tax_ids: List[Union[int, str]] = [int(arg) if arg.isdigit() else arg for arg in args]
            df = self.current_tree.annotate(tax_ids)
            
            table = format_dataframe(df, title=f"Annotation for {', '.join(map(str, tax_ids))}")
            with self.console.pager():
                self.console.print(table)
        except Exception as e:
            self.console.print(f"[red]Error during annotation:[/red] {e}")
            logger.error(f"Annotation failed: {e}")

    def handle_find(self, args: List[str]) -> None:
        """
        Handles the 'find' command for fuzzy name search.

        Args:
            args: The query string parts.
        """
        if not self._ensure_loaded():
            return
        if not args:
            self.console.print("[yellow]Usage: find <query>[/yellow]")
            return

        query: str = " ".join(args)
        try:
            if not hasattr(self.current_tree, 'find'):
                self.console.print("[red]The find method is not available in the current JolTree version.[/red]")
                return
                
            df = self.current_tree.find(query)
            table = format_find_results(df)
            with self.console.pager():
                self.console.print(table)
        except Exception as e:
            self.console.print(f"[red]Error during search:[/red] {e}")
            logger.error(f"Search failed for query '{query}': {e}")

    def handle_lineage(self, args: List[str]) -> None:
        """
        Handles the 'lineage' command to show the path to root.

        Args:
            args: A single taxonomic ID.
        """
        if not self._ensure_loaded():
            return
        if not args:
            self.console.print("[yellow]Usage: lineage <tax_id>[/yellow]")
            return

        tax_id: Union[int, str] = int(args[0]) if args[0].isdigit() else args[0]
        try:
            if not hasattr(self.current_tree, 'lineage'):
                self.console.print("[red]The lineage method is not available in the current JolTree version.[/red]")
                return
                
            df = self.current_tree.lineage(tax_id)
            tree_vis = format_lineage(df, tax_id)
            self.console.print(tree_vis)
        except Exception as e:
            self.console.print(f"[red]Error fetching lineage:[/red] {e}")
            logger.error(f"Lineage lookup failed for ID '{tax_id}': {e}")

    def handle_config(self) -> None:
        """Handles the 'config' command to re-run the setup wizard."""
        setup_wizard(force=True)
        # Refresh the loader's cache dir in case it changed
        from .config import get_cache_dir
        self.loader.cache_dir = get_cache_dir()
