"""Command-line interface for bibtex-dedup."""
import argparse
import sys

from .core import deduplicate, format_entry, parse_bibtex


def main(argv=None):
    ap = argparse.ArgumentParser(prog="bibtex-dedup", description="Find and merge duplicate BibTeX entries.")
    ap.add_argument("bibfiles", nargs="+", help="one or more .bib files (combined before deduplication)")
    ap.add_argument("-o", "--output", help="write deduplicated BibTeX here (default: stdout)")
    ap.add_argument("-t", "--threshold", type=float, default=0.9, help="title similarity threshold 0-1 (default 0.9)")
    ap.add_argument("--report-only", action="store_true", help="only list duplicate groups; exit 1 if any")
    args = ap.parse_args(argv)

    entries = []
    for path in args.bibfiles:
        with open(path, encoding="utf-8") as fh:
            entries.extend(parse_bibtex(fh.read()))
    result, report = deduplicate(entries, args.threshold)

    for group in report:
        print("duplicate: " + " = ".join(group), file=sys.stderr)
    print("%d entries, %d duplicate groups, %d after merge" % (len(entries), len(report), len(result)), file=sys.stderr)
    if args.report_only:
        return 1 if report else 0
    text = "\n\n".join(format_entry(e) for e in result) + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text)
    else:
        sys.stdout.write(text)
    return 0
