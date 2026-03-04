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

    Args:
        df: The Polars DataFrame containing the data.
        title: The title to display above the table.

    Returns:
        Table: A Rich Table instance ready for printing.
    """
    table = Table(title=title, show_header=True, header_style="bold magenta")
    
    # Add columns from the DataFrame
    for col in df.columns:
        table.add_column(str(col))
        
    # Add rows from the DataFrame
    for row in df.iter_rows():
        table.add_row(*[str(val) for val in row])
        
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
        
    # Get the first node (root)
    # Expected columns: name, rank, tax_id
    root_row: Dict[str, Any] = lineage_df.row(0, named=True)
    root_node = Tree(
        f"{root_row['name']} ([cyan]{root_row['rank']}[/cyan]) [dim]{root_row['tax_id']}[/dim]"
    )
    
    current_node = root_node
    # Iterate through subsequent nodes to build the hierarchy
    for i in range(1, len(lineage_df)):
        row: Dict[str, Any] = lineage_df.row(i, named=True)
        current_node = current_node.add(
            f"{row['name']} ([cyan]{row['rank']}[/cyan]) [dim]{row['tax_id']}[/dim]"
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
