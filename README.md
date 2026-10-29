# bibtex-dedup

**Find and merge duplicate BibTeX entries by DOI, normalized title and fuzzy matching.**

Part of the *Research Automation Toolkit*: 100 open tools for daily research work.

## Why

Bibliographies grow by copy-pasting from Google Scholar, publisher pages, Zotero exports and
co-authors' files. The same paper ends up cited under two keys (`smith2020` and `Smith_2020_dl`),
with different capitalization, a DOI written as a URL, or one copy missing the volume.
Duplicate references inflate reference counts, confuse reviewers and break journal reference limits.

## Features

- Dependency-free BibTeX parser (braces, quotes, bare values; skips `@comment`/`@string`)
- Duplicate detection: identical DOIs (normalized: `https://doi.org/`, `doi:` and case removed),
  or fuzzy title similarity guarded by year and first-author surname
- Transitive grouping (A = B and B = C gives one group)
- Merge strategy: keep the first key, fill missing fields, prefer the most complete value
- Combine several `.bib` files at once; report-only mode for CI checks

## Install

```bash
pip install .
```

## Usage

```bash
bibtex-dedup refs.bib coauthor.bib -o clean.bib
bibtex-dedup refs.bib --report-only          # exit code 1 if duplicates exist
bibtex-dedup refs.bib -t 0.85                # looser title matching
python -m bibtex_dedup examples/refs.bib     # without installing
```

```python
from bibtex_dedup import parse_bibtex, deduplicate, format_entry

entries = parse_bibtex(open("refs.bib", encoding="utf-8").read())
clean, report = deduplicate(entries)
print(report)   # [['smith2020', 'Smith_2020_dl'], ['lee2019', 'lee2019survey']]
```

## How it works

1. Titles are normalized: LaTeX commands, braces, accents and punctuation removed, lowercased.
2. Two entries are duplicates if their DOIs match. If both have DOIs that differ, they are distinct.
   Otherwise `difflib.SequenceMatcher` similarity must reach the threshold with no conflicting
   year or first-author surname.
3. Duplicates are grouped with union-find and merged field by field.

## Testing

```bash
python -m unittest discover -s tests -t .
```

## License

MIT (c) JANIN A APURBA
