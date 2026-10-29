import os
import tempfile
import unittest

from bibtex_dedup.cli import main
from bibtex_dedup.core import (deduplicate, find_duplicates, is_duplicate, normalize_doi,
                               normalize_title, parse_bibtex)

EXAMPLE = os.path.join(os.path.dirname(__file__), "..", "examples", "refs.bib")


def entry(title, year="2020", author="Smith, A", doi=None):
    f = {"title": title, "year": year, "author": author}
    if doi:
        f["doi"] = doi
    return {"type": "article", "key": title[:5], "fields": f}


class ParseTests(unittest.TestCase):
    def test_parses_braces_quotes_and_bare_values(self):
        e = parse_bibtex('@article{k1, title={A {Nested} Title}, journal="J. {X}", year=2021}')[0]
        self.assertEqual(e["key"], "k1")
        self.assertEqual(e["fields"]["title"], "A {Nested} Title")
        self.assertEqual(e["fields"]["journal"], "J. {X}")
        self.assertEqual(e["fields"]["year"], "2021")

    def test_skips_comments_and_strings(self):
        text = "@comment{ignore me}\n@string{nat = {Nature}}\n@book{b1, title={T}}"
        self.assertEqual([e["key"] for e in parse_bibtex(text)], ["b1"])

    def test_unbalanced_raises(self):
        with self.assertRaises(ValueError):
            parse_bibtex("@article{k, title={oops}")


class NormalizeTests(unittest.TestCase):
    def test_title(self):
        self.assertEqual(normalize_title("A {Survey} of \\emph{GNNs}: Caf\u00e9!"), "a survey of gnns cafe")

    def test_doi(self):
        self.assertEqual(normalize_doi("https://dx.doi.org/10.1/ABC"), "10.1/abc")
        self.assertEqual(normalize_doi("doi:10.1/x"), "10.1/x")


class DuplicateTests(unittest.TestCase):
    def test_same_doi_is_duplicate_even_with_different_titles(self):
        self.assertTrue(is_duplicate(entry("One", doi="10.1/a"), entry("Two", doi="https://doi.org/10.1/A")))

    def test_different_doi_never_duplicate(self):
        self.assertFalse(is_duplicate(entry("Same title", doi="10.1/a"), entry("Same title", doi="10.1/b")))

    def test_year_mismatch_blocks_title_match(self):
        self.assertFalse(is_duplicate(entry("Same title", "2019"), entry("Same title", "2020")))

    def test_author_mismatch_blocks_title_match(self):
        self.assertFalse(is_duplicate(entry("Same title", author="Smith, A"), entry("Same title", author="B. Jones")))

    def test_transitive_grouping(self):
        es = [entry("x", doi="10.1/a"), entry("Some long title here"), entry("x2", doi="10.1/A"),
              entry("Some long title here.")]
        self.assertEqual(sorted(map(sorted, find_duplicates(es))), [[0, 2], [1, 3]])

    def test_example_file_merges_and_fills_fields(self):
        with open(EXAMPLE, encoding="utf-8") as fh:
            entries = parse_bibtex(fh.read())
        out, report = deduplicate(entries)
        self.assertEqual(len(out), 2)
        self.assertEqual(len(report), 2)
        self.assertEqual(out[0]["fields"]["volume"], "577")
        self.assertEqual(out[1]["fields"]["pages"], "1--10")


class CliTests(unittest.TestCase):
    def test_cli_writes_output(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "clean.bib")
            self.assertEqual(main([EXAMPLE, "-o", out]), 0)
            with open(out, encoding="utf-8") as fh:
                self.assertEqual(len(parse_bibtex(fh.read())), 2)

    def test_report_only_exit_code(self):
        self.assertEqual(main([EXAMPLE, "--report-only"]), 1)


if __name__ == "__main__":
    unittest.main()
