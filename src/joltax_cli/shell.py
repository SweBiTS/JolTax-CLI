"""
joltax_cli/shell.py
Interactive shell implementation for JolTax.
Handles the REPL loop, command parsing, and output management.
"""

import sys
import logging
from typing import Optional, List, Union, Any
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from rich.console import Console
from rich.table import Table

from .loader import TaxonomyLoader, JolTree
from .formatter import format_dataframe, format_lineage, format_find_results
from .completer import JolTaxCompleter

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
        Initializes the shell with a taxonomy loader.

        Args:
            loader: The loader instance for managing taxonomy data.
        """
        self.loader: TaxonomyLoader = loader
        self.completer: JolTaxCompleter = JolTaxCompleter(loader)
        self.session: PromptSession = PromptSession(
            history=InMemoryHistory(),
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
                elif command == "summary":
                    self.handle_summary()
                elif command == "annotate":
                    self.handle_annotate(args)
                elif command == "find":
                    self.handle_find(args)
                elif command == "lineage":
                    self.handle_lineage(args)
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
        table.add_row("summary", "Show summary information for the currently loaded taxonomy.")
        table.add_row("annotate <id>...", "Pretty-print canonical ranks for one or more tax IDs.")
        table.add_row("find <query>", "Fuzzy search for tax IDs by name.")
        table.add_row("lineage <id>", "Display the lineage of a tax ID as a visual tree.")
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

    def handle_use(self, args: List[str]) -> None:
        """
        Handles the 'use' command to switch taxonomies.

        Args:
            args: Command arguments [name]. If empty, lists available taxonomies.
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
        self.console.print(f"Loading taxonomy '{name}'...")
        tree = self.loader.load_taxonomy(name)
        if tree:
            self.current_tree = tree
            self.current_name = name
            # Update completer with ranks from the new taxonomy
            ranks: List[str] = getattr(tree, 'available_ranks', [])
            self.completer.set_available_ranks(ranks)
            self.console.print(f"[green]Successfully loaded '{name}'.[/green]")

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
