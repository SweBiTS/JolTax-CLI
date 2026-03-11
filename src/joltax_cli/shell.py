"""
joltax_cli/shell.py
Interactive shell implementation for JolTax.
Handles the REPL loop, command parsing, and output management.
"""

import os
import sys
import logging
import psutil
from typing import Optional, List, Union, Any
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.lexers import PygmentsLexer
from pygments.lexers.shell import BashLexer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.prompt import Confirm

from .loader import TaxonomyLoader, JolTree
from .formatter import format_dataframe, format_lineage, format_find_results
from .completer import JolTaxCompleter
from .config import setup_wizard, DEFAULT_CONFIG_DIR, load_config, save_config, console

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
            completer=self.completer,
            lexer=PygmentsLexer(BashLexer),
            bottom_toolbar=self._get_bottom_toolbar
        )
        # Use the shared console instance from config.py
        self.console: Console = console
        self.current_tree: Optional[JolTree] = None
        self.current_name: Optional[str] = None

    def _get_bottom_toolbar(self) -> HTML:
        """
        Generates the content for the bottom toolbar with live metrics.
        Uses terminal width for alignment and professional colors.

        Returns:
            HTML: The formatted toolbar content.
        """
        try:
            cols, _ = os.get_terminal_size()
        except OSError:
            cols = 80

        # Metrics
        process = psutil.Process()
        mem_mb = process.memory_info().rss / (1024 * 1024)
        mem_str = f"MEM: {mem_mb:.1f} MB"

        # Content segments (unformatted for length calculation)
        tax_name = self.current_name or "None"
        left_text = f" TAX: {tax_name} "
        mid_text = " EXIT: Ctrl+D "
        right_text = f" {mem_str} "

        # Calculate padding
        total_len = len(left_text) + len(mid_text) + len(right_text)
        if cols > total_len:
            pad_1 = (cols // 2) - len(left_text) - (len(mid_text) // 2)
            pad_2 = cols - len(left_text) - pad_1 - len(mid_text) - len(right_text)
            padding_1 = " " * max(0, pad_1)
            padding_2 = " " * max(0, pad_2)
        else:
            padding_1 = " | "
            padding_2 = " | "

        # Formatted segments
        left_fmt = f'<style fg="ansiblue">TAX:</style> <style fg="ansicyan">{tax_name}</style>'
        mid_fmt = f'<style fg="ansiblue">EXIT:</style> <style fg="ansicyan">Ctrl+D</style>'
        right_fmt = f'<style fg="ansiblue">MEM:</style> <style fg="ansicyan">{mem_mb:.1f} MB</style>'

        return HTML(f"{left_fmt}{padding_1}{mid_fmt}{padding_2}{right_fmt}")

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
        self.console.print("Type 'help' for commands, 'exit' or Ctrl+D to quit.\n")

        # Auto-load the last used taxonomy from config
        config = load_config()
        last_tax = config.get("last_taxonomy")
        
        if last_tax and last_tax in self.loader.list_available_taxonomies():
            self.handle_use([last_tax], silent=True)
            self.console.print(f"[bold green]Status:[/bold green] Active taxonomy: [bold cyan]{last_tax}[/bold cyan]")
        else:
            available_count = len(self.loader.list_available_taxonomies())
            self.console.print("[bold yellow]Status:[/bold yellow] No taxonomy loaded.")
            if available_count > 0:
                self.console.print(f"        {available_count} taxonomies available in cache. Use '[bold]use[/bold]' to load one.")
            else:
                self.console.print("        Cache is empty. Use '[bold]build[/bold]' to create your first taxonomy.")
        
        self.console.print("") # Trailing newline for spacing

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
        
        # Check if taxonomy already exists
        tax_path = self.loader.cache_dir / name
        if tax_path.exists():
            if not Confirm.ask(
                f"[yellow]Warning:[/yellow] Taxonomy '[bold]{name}[/bold]' already exists. "
                "Do you want to [bold red]overwrite[/bold red] it?"
            ):
                self.console.print("Build cancelled.")
                return

        with self.console.status(f"[bold green]Building taxonomy cache '{name}'..."):
            try:
                tax_path = self.loader.build_taxonomy(name, arg1, arg2)
                self.console.print(
                    f"[bold green]✓[/bold green] Successfully built and saved taxonomy '{name}' to {tax_path}."
                )
                self.console.print(f"You can now load it using: [cyan]use {name}[/cyan]")
            except Exception as e:
                self.console.print(f"[red]Error building taxonomy:[/red] {e}")

    def handle_use(self, args: List[str], silent: bool = False) -> None:
        """
        Handles the 'use' command to switch taxonomies.

        Args:
            args: Command arguments [name]. If empty, provides interactive selection.
            silent: If True, suppresses non-error output (used for auto-load).
        """
        taxonomies: List[str] = self.loader.list_available_taxonomies()
        
        if not taxonomies:
            self.console.print("[yellow]No taxonomies found in cache. Use 'build' to create one.[/yellow]")
            return

        name: Optional[str] = None
        
        if not args:
            if silent: return # Don't prompt in silent mode
            
            # Interactive selection if no args provided
            self.console.print("Available taxonomies:")
            for i, tax in enumerate(taxonomies, 1):
                self.console.print(f"  [bold cyan]{i}.[/bold cyan] {tax}")
            
            choice = self.console.input("\n[bold]Select a taxonomy (number or name): [/bold]")
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(taxonomies):
                    name = taxonomies[idx]
            elif choice in taxonomies:
                name = choice
            
            if not name:
                self.console.print("[red]Invalid selection.[/red]")
                return
        else:
            name = args[0]
            if name not in taxonomies:
                self.console.print(f"[red]Error:[/red] Taxonomy '{name}' not found in cache.")
                return

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
                self.console.print(f"[bold green]✓[/bold green] Switched to taxonomy '{name}'.")

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

        summary = self.current_tree.summary
        
        # Provenance Metadata
        build_time = summary.get('build_time', 'Unknown')
        source_nodes = summary.get('source_nodes', 'Unknown')
        source_names = summary.get('source_names', 'Unknown')
        node_count = f"{summary.get('node_count', 0):,}"
        top_rank = summary.get('top_rank', 'domain')
        package_ver = summary.get('package_version', 'Unknown')
        max_depth = summary.get('max_depth', 0)
        
        # Combined Content
        content = (
            f"[bold cyan]Nodes:[/bold cyan] {node_count}\n"
            f"[bold cyan]Top Rank:[/bold cyan] {top_rank}\n"
            f"[bold cyan]Max Depth:[/bold cyan] {max_depth}\n"
            f"[bold cyan]Built At:[/bold cyan] {build_time}\n"
            f"[bold cyan]Nodes Source:[/bold cyan] {source_nodes}\n"
            f"[bold cyan]Names Source:[/bold cyan] {source_names}\n"
            f"[bold cyan]Core Version:[/bold cyan] {package_ver}"
        )
        
        provenance_panel = Panel(content, title="[bold]Provenance & Metadata[/bold]", border_style="blue", expand=True)
        self.console.print(provenance_panel)

        # Available Ranks Panel
        ranks = sorted(getattr(self.current_tree, 'available_ranks', []))
        if ranks:
            rank_str = ", ".join([f"[cyan]{r}[/cyan]" for r in ranks])
            self.console.print(Panel(rank_str, title="[bold]Available Ranks[/bold]", border_style="magenta", padding=(1, 2)))
        
        self.console.print("") # Final newline

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
            if not hasattr(self.current_tree, 'search_name'):
                self.console.print("[red]The search_name method is not available in the current JolTree version.[/red]")
                return
                
            # Use fuzzy search by default for the CLI find command
            df = self.current_tree.search_name(query, fuzzy=True)
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
            if not hasattr(self.current_tree, 'get_lineage'):
                self.console.print("[red]The get_lineage method is not available in the current JolTree version.[/red]")
                return
                
            # get_lineage returns a list of IDs
            lineage_ids = self.current_tree.get_lineage(tax_id)
            if not lineage_ids:
                self.console.print(f"[yellow]No lineage found for ID '{tax_id}'.[/yellow]")
                return

            # Annotate the IDs to get full metadata (names, ranks) for display
            df = self.current_tree.annotate(lineage_ids)
            tree_vis = format_lineage(df, tax_id)
            self.console.print(tree_vis)
        except Exception as e:
            self.console.print(f"[red]Error fetching lineage:[/red] {e}")
            logger.error(f"Lineage lookup failed for ID '{tax_id}': {e}")

    def handle_config(self) -> None:
        """
        Handles the 'config' command to re-run the setup wizard.
        
        Refreshes the loader's configuration after the wizard completes.
        """
        setup_wizard(force=True)
        # Refresh the loader's cache dir in case it changed
        from .config import get_cache_dir
        self.loader.cache_dir = get_cache_dir()
