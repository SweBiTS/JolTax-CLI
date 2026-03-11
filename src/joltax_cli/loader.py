"""
joltax_cli/loader.py
Logic for listing, building, and loading JolTree instances.
Supports binary cache loading and build from DMP files.
"""

import os
import logging
from pathlib import Path
from typing import List, Optional, Union

# Set up logging for the module
logger = logging.getLogger(__name__)

def _check_joltax_version(version_str: str) -> bool:
    """Helper to check if joltax version is >= 0.2.0."""
    try:
        parts = [int(p) for p in version_str.split('.')]
        return parts[0] >= 1 or (parts[0] == 0 and parts[1] >= 2)
    except (ValueError, IndexError):
        return False

try:
    from joltax import JolTree, __version__ as joltax_version
    if not _check_joltax_version(joltax_version):
        raise ImportError(f"Incompatible joltax version: {joltax_version}. Required: >= 0.2.0")
except ImportError as e:
    import polars as pl
    import numpy as np

    # If it's a version mismatch, re-raise to inform the user
    if "Incompatible joltax version" in str(e):
        raise

    # A simple mock to allow basic CLI testing without the backend installed
    class JolTree:
        """
        Mock JolTree for environments without the joltax library.
        Provides stubs for essential methods and returns dummy data.
        """
        def __init__(self, tax_dir: Optional[str] = None, nodes: Optional[str] = None, 
                     names: Optional[str] = None, path: Optional[str] = None):
            self.path = path or tax_dir or nodes
            self.available_ranks = ["domain", "phylum", "class", "order", "family", "genus", "species"]
            self.parents = [0] * 1000 # To simulate node count
            self.top_rank = "domain"
            self._build_time = "2026-03-01 12:00:00"
            self._source_nodes = nodes or "nodes.dmp"
            self._source_names = names or "names.dmp"
            
        @classmethod
        def load(cls, path: str) -> 'JolTree':
            """Stubs JolTree.load()"""
            return cls(path=path)

        def save(self, directory: str) -> None:
            """Stubs JolTree.save()"""
            os.makedirs(directory, exist_ok=True)
            import pickle
            with open(os.path.join(directory, "metadata.pkl"), "wb") as f:
                pickle.dump({"rank_names": self.available_ranks, "top_rank": self.top_rank}, f)
            
        def annotate(self, ids: List[Union[int, str]]) -> pl.DataFrame:
            """Stubs JolTree.annotate()"""
            # Ensure we return rows in the order of input IDs for lineage support
            return pl.DataFrame({
                "t_id": ids,
                "t_domain": ["Eukarya"] * len(ids),
                "t_phylum": ["Chordata"] * len(ids),
                "t_scientific_name": [f"Name_{i}" for i in ids],
                "t_rank": ["species"] * len(ids)
            })
            
        def search_name(self, query: str, fuzzy: bool = False, limit: int = 10, score_cutoff: float = 60.0) -> pl.DataFrame:
            """Stubs JolTree.search_name()"""
            return pl.DataFrame({
                "tax_id": [1, 2, 3],
                "matched_name": [f"Result for {query} 1", f"Result for {query} 2", f"Result for {query} 3"],
                "scientific_name": [f"Sci Name {i}" for i in range(1, 4)],
                "rank": ["genus", "species", "species"],
                "score": [100.0, 90.0, 80.0]
            })
            
        def get_lineage(self, tax_id: Union[int, str]) -> List[int]:
            """Stubs JolTree.get_lineage()"""
            return [1, 10, 100, int(tax_id) if str(tax_id).isdigit() else 1000]

        @property
        def summary(self) -> dict:
            """Returns a summary of the tree's metadata and provenance."""
            return {
                "node_count": len(self.parents),
                "top_rank": self.top_rank,
                "build_time": self._build_time,
                "source_nodes": self._source_nodes,
                "source_names": self._source_names,
                "package_version": "0.2.0-mock",
                "max_depth": 5,
                "ranks_present": len(self.available_ranks)
            }

from .config import get_cache_dir

class TaxonomyLoader:
    """
    Handles the discovery, construction, and instantiation of JolTree taxonomies.
    
    Attributes:
        cache_dir (Path): The directory where binary taxonomy caches are stored.
    """

    def __init__(self):
        """Initializes the loader with the configured cache directory."""
        self.cache_dir: Path = get_cache_dir()

    def list_available_taxonomies(self) -> List[str]:
        """
        Scans the cache directory for available taxonomy binary folders.

        Returns:
            List[str]: A list of directory names in the cache folder.
        """
        taxonomies: List[str] = []
        if not self.cache_dir.exists():
            return taxonomies
            
        for item in self.cache_dir.iterdir():
            if item.is_dir():
                taxonomies.append(item.name)
        return sorted(taxonomies)

    def load_taxonomy(self, name: str) -> Optional['JolTree']:
        """
        Loads a JolTree instance from the cache directory by its name.

        Args:
            name: The directory name of the taxonomy to load.

        Returns:
            Optional[JolTree]: The loaded tree instance, or None if loading fails.
        """
        tax_path = self.cache_dir / name
        if not tax_path.exists():
            logger.error(f"Taxonomy '{name}' not found in cache directory ({self.cache_dir}).")
            return None
        
        try:
            tree = JolTree.load(str(tax_path))
            return tree
        except Exception as e:
            logger.error(f"Error loading taxonomy '{name}': {e}")
            return None

    def build_taxonomy(self, name: str, arg1: str, arg2: Optional[str] = None) -> Path:
        """
        Builds a new taxonomy from NCBI DMP files and saves it to the cache.

        Args:
            name: The name to give to the new taxonomy cache.
            arg1: Either the path to a tax_dir or the path to nodes.dmp.
            arg2: The path to names.dmp if arg1 was nodes.dmp.

        Returns:
            Path: The path to the newly created taxonomy directory.

        Raises:
            Exception: If the build or save process fails.
        """
        tax_path = self.cache_dir / name
        try:
            if arg2:
                tree = JolTree(nodes=arg1, names=arg2)
            else:
                tree = JolTree(tax_dir=arg1)
                
            tree.save(str(tax_path))
            return tax_path
        except Exception as e:
            logger.error(f"Failed to build taxonomy '{name}': {e}")
            raise

    def remove_taxonomy(self, name: str) -> bool:
        """
        Deletes a taxonomy cache directory from the disk.

        Args:
            name: The name of the taxonomy to remove.

        Returns:
            bool: True if deleted successfully, False if it didn't exist.
        """
        import shutil
        tax_path = self.cache_dir / name
        if not tax_path.exists():
            return False
        
        try:
            shutil.rmtree(tax_path)
            return True
        except OSError as e:
            logger.error(f"Failed to delete taxonomy '{name}': {e}")
            raise
