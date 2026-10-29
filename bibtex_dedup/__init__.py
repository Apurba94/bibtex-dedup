"""Find and merge duplicate BibTeX entries."""
from .core import parse_bibtex, find_duplicates, merge_entries, deduplicate, format_entry

__version__ = "0.1.0"
__all__ = ["parse_bibtex", "find_duplicates", "merge_entries", "deduplicate", "format_entry"]
