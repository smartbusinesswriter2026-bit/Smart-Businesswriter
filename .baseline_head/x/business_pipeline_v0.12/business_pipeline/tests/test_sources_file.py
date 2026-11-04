"""The student's own source list is read, labelled and never treated as evidence (B-182).

The reader opens a declared subset of .bib, .ris and .csv.  Every test here is about one
of two promises: an entry that can be read keeps exactly what the student wrote, and an
entry that cannot be read becomes a **named problem** instead of disappearing.
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp.product import sources_file  # noqa: E402

BIB = b"""% a comment line
@article{smith2019,
  author = {Smith, J. and Doe, A.},
  title  = {Growth {and} value in retail},
  year   = {2019},
  doi    = {https://doi.org/10.1000/xyz123},
  journal = {Journal of Retail}
}

@book{jones2021,
  author    = {Jones, K.},
  title     = {Retail operations},
  year      = {2021},
  publisher = {Press}
}

@misc{broken,
  author = {Nobody},
  year   = {2020}
}
"""

RIS = b"""TY  - JOUR
AU  - Smith, Jane
AU  - Doe, Adam
TI  - Supply chain resilience
PY  - 2020
DO  - 10.1000/abc
ER  - 

TY  - BOOK
TI  - Operations management
ER  - 
"""

CSV = b"""key,title,authors,year,doi,url
s1,Market sizing,"Smith, J.; Doe, A.",2019,10.1/x,
s2,,Nobody,2020,,
"""


class BibFileTest(unittest.TestCase):
    def setUp(self):
        self.table = sources_file.parse("refs.bib", BIB)

    def test_every_readable_entry_is_kept(self):
        self.assertEqual(self.table["format"], "bp-sources/1")
        self.assertEqual(self.table["n_entries"], 2)
        self.assertEqual(self.table["n_problems"], 1)
        self.assertEqual([e["key"] for e in self.table["entries"]], ["smith2019", "jones2021"])

    def test_the_fields_are_the_students_own_words(self):
        first = self.table["entries"][0]
        self.assertEqual(first["authors"], ["Smith, J.", "Doe, A."])
        self.assertEqual(first["title"], "Growth {and} value in retail")
        self.assertEqual(first["year"], "2019")
        self.assertEqual(first["doi"], "10.1000/xyz123", "a doi.org URL is stored as the bare DOI")
        self.assertEqual(first["type"], "article")

    def test_an_entry_with_no_title_is_a_named_problem_not_a_dropped_row(self):
        problem = self.table["problems"][0]
        self.assertIn("no title", problem["problem"])
        self.assertEqual(problem["raw"], "broken")

    def test_a_url_that_is_not_http_is_a_problem_and_is_not_kept(self):
        body = b'@misc{a, title = {X}, url = {ftp://example.org/x}}'
        table = sources_file.parse("refs.bib", body)
        self.assertEqual(table["n_entries"], 1)
        self.assertIsNone(table["entries"][0]["url"])
        self.assertIn("not an http", table["problems"][0]["problem"])

    def test_a_non_utf8_file_is_decoded_rather_than_refused(self):
        table = sources_file.parse("refs.bib", b"@misc{a, title = {Caf\xe9 economics}}")
        self.assertIn("Caf\u00e9", table["entries"][0]["title"])


class RisFileTest(unittest.TestCase):
    def test_each_record_is_one_entry(self):
        table = sources_file.parse("refs.ris", RIS)
        self.assertEqual(table["n_entries"], 2)
        self.assertEqual(table["n_problems"], 0)
        first = table["entries"][0]
        self.assertEqual(first["authors"], ["Smith, Jane", "Doe, Adam"])
        self.assertEqual(first["title"], "Supply chain resilience")
        self.assertEqual(first["year"], "2020")
        self.assertEqual(first["doi"], "10.1000/abc")

    def test_a_record_with_no_title_is_a_named_problem(self):
        table = sources_file.parse("refs.ris", b"TY  - JOUR\nAU  - Nobody\nER  - \n")
        self.assertEqual(table["n_entries"], 0)
        self.assertIn("no title", table["problems"][0]["problem"])


class CsvFileTest(unittest.TestCase):
    def test_a_declared_header_is_read(self):
        table = sources_file.parse("refs.csv", CSV)
        self.assertEqual(table["n_entries"], 1)
        self.assertEqual(table["entries"][0]["authors"], ["Smith, J.", "Doe, A."])
        self.assertEqual(table["entries"][0]["doi"], "10.1/x")

    def test_a_row_with_no_title_is_a_named_problem(self):
        table = sources_file.parse("refs.csv", CSV)
        self.assertEqual(table["n_problems"], 1)
        self.assertIn("no title", table["problems"][0]["problem"])
        self.assertEqual(table["problems"][0]["line"], 3)

    def test_a_header_without_title_is_refused(self):
        with self.assertRaises(sources_file.SourcesError) as caught:
            sources_file.parse("refs.csv", b"key,authors\n1,Smith\n")
        self.assertIn("title", str(caught.exception))


class RefusalsTest(unittest.TestCase):
    def test_an_extension_with_no_reader_is_refused(self):
        with self.assertRaises(sources_file.SourcesError) as caught:
            sources_file.parse("notes.txt", b"hello")
        self.assertIn(".bib", str(caught.exception))

    def test_an_empty_file_is_refused(self):
        with self.assertRaises(sources_file.SourcesError):
            sources_file.parse("refs.bib", b"")

    def test_too_many_entries_is_refused_not_truncated(self):
        rows = ["key,title"] + ["k%d,title %d" % (n, n) for n in range(sources_file.MAX_ENTRIES + 5)]
        with self.assertRaises(sources_file.SourcesError) as caught:
            sources_file.parse("refs.csv", "\n".join(rows).encode("utf-8"))
        self.assertIn("more than", str(caught.exception))


class CitationsTest(unittest.TestCase):
    """B-182: the citation line invents nothing and never claims verification."""

    def test_a_citation_is_the_students_own_fields(self):
        table = sources_file.parse("refs.bib", BIB)
        lines = sources_file.citations(table)
        self.assertEqual(lines[0],
                         "Smith, J.; Doe, A. (2019). Growth {and} value in retail. "
                         "https://doi.org/10.1000/xyz123")
        self.assertEqual(lines[1], "Jones, K. (2021). Retail operations. Press.")

    def test_the_order_is_the_order_the_student_wrote(self):
        table = sources_file.parse("refs.bib", BIB)
        self.assertEqual([line.split("(")[0].strip() for line in sources_file.citations(table)],
                         ["Smith, J.; Doe, A.", "Jones, K."])

    def test_a_limit_never_reorders(self):
        table = sources_file.parse("refs.bib", BIB)
        self.assertEqual(sources_file.citations(table, limit=1),
                         sources_file.citations(table)[:1])

    def test_the_table_says_the_sources_are_not_evidence(self):
        table = sources_file.parse("refs.ris", RIS)
        self.assertIn("not evidence", table["note"])
        self.assertIn("has not verified", table["note"])

    def test_the_summary_carries_the_counts(self):
        table = sources_file.parse("refs.csv", CSV)
        self.assertEqual(sources_file.summary(table),
                         {"n_entries": 1, "n_problems": 1, "ext": ".csv",
                          "format": "bp-sources/1"})


if __name__ == "__main__":
    unittest.main()

