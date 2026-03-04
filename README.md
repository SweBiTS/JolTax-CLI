# JolTax-CLI

**JolTax-CLI** is an interactive, high-performance "Taxonomic Shell" for exploring and querying biological taxonomies. It is built on top of the `joltax` library, leveraging vectorized operations and binary caches to provide nearly instantaneous results even for massive datasets like the NCBI taxonomy.

## 🚀 Key Features

- **Interactive REPL:** A persistent shell environment with context-aware auto-completion and command history.
- **High Performance:** Utilizes the `joltax` vectorized backend for $O(1)$ and $O(\log N)$ taxonomic queries.
- **Beautiful UI:** Pretty-printed tables, visual lineage trees, and color-coded console output powered by `rich`.
- **Flexible Configuration:** Manage multiple taxonomy caches (e.g., NCBI, GTDB) and switch between them seamlessly.
- **Pager Support:** Long results (like mass annotations) automatically open in a pager (like `less`) for easy reading.
- **Direct Build:** Create optimized binary caches directly from NCBI-style `.dmp` files.

## 🛠 Installation

Currently, JolTax-CLI can be installed from source:

```bash
git clone https://github.com/SweBiTS/JolTax-CLI.git
cd JolTax-CLI
pip install -e .
```

Ensure you have the `joltax` backend installed as well.

## 🏁 Quick Start

1. **Launch the shell:**
   ```bash
   joltax
   ```
   *On your first run, a **Setup Wizard** will guide you through configuring your cache directory.*

2. **Build a taxonomy cache:**
   ```text
   joltax> build ncbi /path/to/ncbi_taxonomy/
   ```

3. **Load and use the taxonomy:**
   ```text
   joltax> use ncbi
   joltax(ncbi)> summary
   joltax(ncbi)> annotate 9606
   ```

## ⌨️ Command Reference

| Command | Description |
| :--- | :--- |
| `use <name>` | Switch between available binary caches in your cache directory. |
| `build <name> <dir>` | Build a new optimized binary cache from NCBI `.dmp` files. |
| `remove <name>` | Permanently delete a cached taxonomy from the disk. |
| `annotate <id>...` | Pretty-print canonical ranks (Domain, Phylum, etc.) for one or more IDs. |
| `find <query>` | Fuzzy search for taxonomic names using the RapidFuzz index. |
| `lineage <id>` | Display a visual tree of the taxonomic path to the root. |
| `config` | Re-run the interactive setup wizard to change the cache directory. |
| `summary` | Overview of node counts, versions, and provenance metadata. |
| `help` | List all available commands. |
| `exit` / `quit` | Exit the interactive shell. |

## ⚙️ Configuration

JolTax-CLI stores its configuration in `~/.joltax-cli/config.yaml`. You can modify the `cache_dir` setting to change where taxonomy binaries are stored.

## 🧪 Architecture & Performance

JolTax-CLI is designed with the same performance philosophy as the core `joltax` library:
- **Zero-Copy Loading:** Binary caches use NumPy `.npy` and Apache Arrow IPC for instantaneous loading.
- **Vectorized Lookups:** Mass-annotations are performed as batch operations rather than individual node traversals.
- **Euler Tour Indexing:** Clade and lineage operations are optimized for speed using pre-calculated traversal timestamps.

---
Developed by the **SweBiTS** team.
