# JolTax-CLI Project Context

This file serves as the foundational mandate for the `joltax-cli` project. It integrates the original `CLI_BLUEPRINT.md`, the current implementation state, and architectural principles inherited from the core `joltax` library to ensure a seamless experience across the ecosystem.

## 1. Project Objective
Build an interactive, high-performance CLI explorer for the `joltax` taxonomy library. The tool functions as a dedicated "Taxonomic Shell" with pretty formatting, auto-completion, and multi-taxonomy support.

## 2. Engineering Standards & "JolTax" Philosophy
To maintain the same "air" and performance standards as the core library, the following principles apply:

- **Vectorization-First:** The CLI must never iterate over taxonomic nodes in Python loops. Always prefer mass-lookups via `tree.annotate()` or other vectorized methods.
- **Performance Integrity:** Results should feel instantaneous. Use `rich` progress indicators or status spinners only for heavy IO tasks like `build` or initial `load`.
- **Strict vs. Safe Queries:** Align with the library's `strict=True` default. If a TaxID is missing, the CLI should provide a clean error message (using `TaxIDNotFoundError` where applicable) rather than a traceback.
- **Type Safety & Hinting:** 
    - Ensure the CLI robustly handles both integer and string TaxID inputs, mirroring the library's internal type guards.
    - **All** public and internal methods MUST use explicit type hinting for parameters and return types.
- **Documentation Standards:**
    - Every module, class, and method MUST have a descriptive docstring.
    - Use **Google-style docstrings** (with `Args`, `Returns`, and `Raises` sections) as established in `joltree.py`.
- **Logging vs. Printing:**
    - Use the standard `logging` module for system events, errors, and background tasks.
    - Use the `rich` console only for direct user interaction and formatted taxonomic output.
- **2025 Taxonomy Support:** Correctly handle `superkingdom` vs `domain` terminology in all tables and summaries.

## 3. Architectural Mandates
- **Decoupled Design:** Maintain a strict separation between the shell logic (`shell.py`), result formatting (`formatter.py`), and the taxonomy loader (`loader.py`).
- **Binary Cache Optimization:** Exclusively use the binary cache format (`JolTree.load()`) for active exploration. Avoid re-parsing `.dmp` files except during an explicit `build`.
- **Context-Aware Completion:** Auto-completion must be dynamic. Command arguments (like ranks or taxonomy names) should be derived from the currently loaded state.
- **Pager Integration:** Any output exceeding the terminal height (especially mass-annotations or deep lineages) MUST be piped through the `rich` pager.

## 4. Core Dependencies
- `joltax`: The high-performance vectorized backend.
- `prompt_toolkit`: For the interactive REPL, history, and completion.
- `rich`: For the "Taxonomic Shell" aesthetics (tables, trees, and colors).
- `pyyaml`: For persistent user configuration.
- `polars`: For zero-copy data handling between the library and the CLI.
- `psutil`: For live system metrics and memory tracking in the status bar.
- `pygments`: For syntax highlighting in the interactive REPL.

## 5. System Architecture & Configuration
- **Config Path:** `~/.joltax-cli/config.yaml`
- **Cache Path:** `~/.joltax-cli/cache/` (Governed by `cache_dir` in config).
- **Interactive Shell:** Managed via `JolTaxShell` in `src/joltax_cli/shell.py`.

## 6. Supported Commands
- `use <name>`: Switch between binary caches in the configured directory.
- `build <name> <tax_dir> [names_dmp]`: Create a new optimized binary cache.
- `annotate <tax_id>...`: Pretty-printed canonical ranks for mass-lookups.
- `find <query>`: Fuzzy name search using the library's `rapidfuzz`-backed index.
- `lineage <tax_id>`: Visual tree representation utilizing Euler Tour traversal logic.
- `summary`: Overview of node counts, versions, and provenance metadata.
- `config`: Re-run the interactive setup wizard to configure the cache directory.
- `help` / `exit` / `quit`: Standard shell navigation.

## 7. Current Implementation State
- [x] Project Scaffolding & `pyproject.toml`.
- [x] Configuration Management (YAML) with Setup Wizard.
- [x] Vectorized Taxonomy Loader (Load/Save/Build logic fixed).
- [x] Interactive REPL with history and context-aware auto-completion.
- [x] Pretty-printing for DataFrames (`rich.table`) and Lineages (`rich.tree`).
- [x] Modern UI with status bar, dashboard summaries, and memory tracking.
- [x] Pager support for large result sets.
- [x] Unit tests for Shell UI and command handlers.
- [x] Enhanced code documentation, typing, and logging.
- [x] Auto-reload last used taxonomy on startup.

## 8. Selected Roadmap
- [x] **Persistent Shell History:** Switch from `InMemoryHistory` to `FileHistory` (storing in `~/.joltax-cli/history`) for cross-session commands.
- [ ] **Batch & CLI Mode:** Support running commands via CLI arguments (e.g., `joltax annotate 9606`) or piping from stdin.
- [ ] **Export Support:** Add `--output` flags to commands like `annotate` and `find` to save results as CSV, TSV, or Parquet using Polars. Ensure export files maintain raw `t_` prefixed column names for consistency with `joltax` core, even if the interactive shell display remains "pretty".
- [ ] **Clipboard Integration:** Commands to copy IDs or lineage trees directly to the system clipboard.
- [ ] **Distribution:** Finalize `pyproject.toml` and package structure for PyPI and Bioconda releases.
