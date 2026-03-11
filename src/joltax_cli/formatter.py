"""
joltax_cli/formatter.py
Handles the formatting of taxonomic data for console display.
Uses the Rich library to create tables and tree visualizations.
"""

import polars as pl
from rich.table import Table
from rich.tree import Tree
from typing import List, Union, Dict, Any

def format_dataframe(df: pl.DataFrame, title: str = "Results") -> Table:
    """
    Converts a Polars DataFrame into a Rich Table for pretty printing.
    Strips 't_' prefix from column names for cleaner display.

    Args:
        df: The Polars DataFrame containing the data.
        title: The title to display above the table.

    Returns:
        Table: A Rich Table instance ready for printing.
    """
    table = Table(title=title, show_header=True, header_style="bold magenta")
    
    # Add columns from the DataFrame (strip t_ prefix if present)
    for col in df.columns:
        display_name = str(col)
        if display_name.startswith("t_"):
            display_name = display_name[2:].replace("_", " ").title()
        table.add_column(display_name)
        
    # Add rows from the DataFrame
    for row in df.iter_rows():
        table.add_row(*[str(val) if val is not None else "[dim]None[/dim]" for val in row])
        
    return table

def format_lineage(lineage_df: pl.DataFrame, target_id: Union[int, str]) -> Tree:
    """
    Converts a lineage DataFrame into a Rich Tree for visual representation.
    
    The tree starts from the root and descends to the target taxonomic node.

    Args:
        lineage_df: A DataFrame containing the path from root to target.
        target_id: The tax_id of the target node.

    Returns:
        Tree: A Rich Tree instance visualizing the lineage.
    """
    if lineage_df.is_empty():
        return Tree(f"[red]No lineage found for {target_id}[/red]")
        
    # Flexible column detection favoring the new t_ prefix
    def get_row_data(row):
        name = row.get('t_scientific_name') or row.get('scientific_name') or row.get('name') or "Unknown"
        rank = row.get('t_rank') or row.get('rank') or "unclassified"
        tid = row.get('t_id') or row.get('tax_id') or "Unknown"
        return name, rank, tid

    root_row: Dict[str, Any] = lineage_df.row(0, named=True)
    name, rank, tid = get_row_data(root_row)
    
    root_node = Tree(
        f"{name} ([cyan]{rank}[/cyan]) [dim]{tid}[/dim]"
    )
    
    current_node = root_node
    # Iterate through subsequent nodes to build the hierarchy
    for i in range(1, len(lineage_df)):
        row: Dict[str, Any] = lineage_df.row(i, named=True)
        name, rank, tid = get_row_data(row)
        current_node = current_node.add(
            f"{name} ([cyan]{rank}[/cyan]) [dim]{tid}[/dim]"
        )
        
    return root_node

def format_find_results(df: pl.DataFrame) -> Table:
    """
    Formats the fuzzy search results into a pretty table.

    Args:
        df: The DataFrame containing search matches.

    Returns:
        Table: A formatted Rich Table of the search results.
    """
    return format_dataframe(df, title="Search Results")
