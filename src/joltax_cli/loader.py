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

try:
    from joltax import JolTree
except ImportError:
    import polars as pl
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
            self.node_count = 1000
            
        @classmethod
        def load(cls, path: str) -> 'JolTree':
            """Stubs JolTree.load()"""
            return cls(path=path)

        def save(self, directory: str) -> None:
            """Stubs JolTree.save()"""
            os.makedirs(directory, exist_ok=True)
            with open(os.path.join(directory, "metadata.pkl"), "w") as f:
                f.write("mock metadata")
            
        def annotate(self, ids: List[Union[int, str]]) -> pl.DataFrame:
            """Stubs JolTree.annotate()"""
            return pl.DataFrame({
                "tax_id": ids,
                "name": [f"Name_{i}" for i in ids],
                "rank": ["species"] * len(ids),
                "domain": ["Eukarya"] * len(ids)
            })
            
        def find(self, query: str) -> pl.DataFrame:
            """Stubs JolTree.find()"""
            return pl.DataFrame({
                "tax_id": [1, 2, 3],
                "name": [f"Result for {query} 1", f"Result for {query} 2", f"Result for {query} 3"],
                "rank": ["genus", "species", "species"]
            })
            
        def lineage(self, tax_id: Union[int, str]) -> pl.DataFrame:
            """Stubs JolTree.lineage()"""
            return pl.DataFrame({
                "tax_id": [1, 10, 100, tax_id],
                "name": ["Root", "Phylum_A", "Genus_B", f"Target_{tax_id}"],
                "rank": ["root", "phylum", "genus", "species"]
            })

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
            logger.info(f"Loading taxonomy cache from {tax_path}...")
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
                logger.info(f"Building taxonomy from nodes: {arg1} and names: {arg2}")
                tree = JolTree(nodes=arg1, names=arg2)
            else:
                logger.info(f"Building taxonomy from directory: {arg1}")
                tree = JolTree(tax_dir=arg1)
                
            logger.info(f"Saving binary cache to {tax_path}...")
            tree.save(str(tax_path))
            return tax_path
        except Exception as e:
            logger.error(f"Failed to build taxonomy '{name}': {e}")
            raise
