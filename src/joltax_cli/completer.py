"""
joltax_cli/completer.py
Custom completer for the JolTax shell.
Handles command and taxonomy name auto-completion.
"""

from typing import Iterable, List, Optional
from prompt_toolkit.completion import Completer, Completion, CompleteEvent
from prompt_toolkit.document import Document

from .loader import TaxonomyLoader

class JolTaxCompleter(Completer):
    """
    A custom completer for the JolTax interactive shell.
    Provides suggestions for commands and dynamic arguments like taxonomy names.
    
    Attributes:
        loader (TaxonomyLoader): The loader used to fetch available taxonomies.
        commands (List[str]): The list of top-level shell commands.
        current_ranks (List[str]): The taxonomic ranks available in the loaded tree.
    """

    def __init__(self, loader: TaxonomyLoader):
        """
        Initializes the completer with a taxonomy loader.

        Args:
            loader: The loader instance for listing available caches.
        """
        self.loader: TaxonomyLoader = loader
        self.commands: List[str] = [
            "use", "build", "summary", "annotate", "find", "lineage", "help", "exit", "quit"
        ]
        self.current_ranks: List[str] = []

    def set_available_ranks(self, ranks: List[str]) -> None:
        """
        Updates the list of available ranks for the currently loaded taxonomy.

        Args:
            ranks: A list of rank names from the active JolTree.
        """
        self.current_ranks = ranks

    def get_completions(self, document: Document, complete_event: CompleteEvent) -> Iterable[Completion]:
        """
        Generates completions based on the user's current input.

        Args:
            document: The input document representing the user's input line.
            complete_event: The event that triggered the completion.

        Yields:
            Completion: A suggestion for the user.
        """
        text_before_cursor: str = document.text_before_cursor
        parts: List[str] = text_before_cursor.split()
        
        # 1. Complete top-level commands if we are at the beginning of the line
        if len(parts) == 0 or (len(parts) == 1 and not text_before_cursor.endswith(" ")):
            word_to_complete: str = parts[0] if parts else ""
            for cmd in self.commands:
                if cmd.startswith(word_to_complete.lower()):
                    yield Completion(cmd, start_position=-len(word_to_complete))
            return
            
        # 2. Command-specific completions
        command: str = parts[0].lower()
        
        # Complete 'use <name>'
        if command == "use" and len(parts) <= 2:
            word_to_complete: str = parts[1] if len(parts) == 2 else ""
            if not text_before_cursor.endswith(" ") or len(parts) == 1:
                # Provide taxonomy names from the cache
                taxonomies: List[str] = self.loader.list_available_taxonomies()
                for tax in taxonomies:
                    if tax.startswith(word_to_complete):
                        yield Completion(tax, start_position=-len(word_to_complete))
                        
        # Potential future completions for ranks or other arguments
        # if command in ("annotate", "lineage") and self.current_ranks: ...
