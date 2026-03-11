import polars as pl
from unittest.mock import MagicMock, PropertyMock
from joltax_cli.shell import JolTaxShell
from joltax_cli.loader import TaxonomyLoader

def test_shell_commands():
    # Mock JolTree
    mock_tree = MagicMock()
    mock_tree.available_ranks = ["domain", "species"]
    mock_tree.parents = [0] * 1000
    mock_tree.top_rank = "domain"
    
    # Mock summary property
    type(mock_tree).summary = PropertyMock(return_value={
        "node_count": 1000,
        "top_rank": "domain",
        "build_time": "2026-03-01",
        "source_nodes": "nodes.dmp",
        "source_names": "names.dmp",
        "package_version": "0.2.0",
        "max_depth": 5,
        "ranks_present": 2
    })
    
    def mock_annotate(ids):
        # New format with t_ prefix
        return pl.DataFrame({
            "t_id": ids,
            "t_domain": ["Eukaryota"] * len(ids),
            "t_phylum": ["Chordata"] * len(ids),
            "t_scientific_name": [f"Name_{i}" for i in ids],
            "t_rank": ["rank"] * len(ids)
        })
    mock_tree.annotate.side_effect = mock_annotate
    
    mock_tree.search_name.return_value = pl.DataFrame({
        "tax_id": [1, 2],
        "matched_name": ["Match1", "Match2"],
        "scientific_name": ["SciMatch1", "SciMatch2"],
        "rank": ["genus", "species"],
        "score": [100.0, 90.0]
    })
    mock_tree.get_lineage.return_value = [1, 10, 123]

    # Mock Loader
    mock_loader = MagicMock(spec=TaxonomyLoader)
    mock_loader.list_available_taxonomies.return_value = ["mock_tax"]
    mock_loader.load_taxonomy.return_value = mock_tree

    # Initialize Shell
    shell = JolTaxShell(mock_loader)
    
    # We can't easily run the actual shell loop in a non-interactive test, 
    # but we can test the handlers directly.
    
    print("Testing 'use' command...")
    shell.handle_use(["mock_tax"])
    assert shell.current_name == "mock_tax"
    assert shell.current_tree == mock_tree
    
    print("Testing 'summary' command...")
    shell.handle_summary()
    
    print("Testing 'annotate' command...")
    shell.handle_annotate(["123"])
    mock_tree.annotate.assert_called_with([123])
    
    print("Testing 'find' command...")
    shell.handle_find(["query"])
    mock_tree.search_name.assert_called()
    
    print("Testing 'lineage' command...")
    shell.handle_lineage(["123"])
    mock_tree.get_lineage.assert_called_with(123)
    mock_tree.annotate.assert_called()
    
    print("All tests passed!")

if __name__ == "__main__":
    test_shell_commands()
