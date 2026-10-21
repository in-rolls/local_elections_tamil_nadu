from contextlib import nullcontext
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

import pdfplumber

from local_elections_tamil_nadu.parse.common import RAW
from local_elections_tamil_nadu.parse.results import ELECTIONS
from local_elections_tamil_nadu.parse.wards import parse_2011


class WardCaptionTests(TestCase):
    def test_kpm_union_in_merged_header_cell_is_retained(self):
        path = RAW / "tnsec/rulbe2011/vpwm_kpm.pdf"
        with pdfplumber.open(path) as source:
            first_page = SimpleNamespace(pages=source.pages[:1])
            with patch(
                "local_elections_tamil_nadu.parse.wards.pdfplumber.open",
                return_value=nullcontext(first_page),
            ):
                rows = parse_2011(path, "vpwm", "kpm", ELECTIONS["rulbe2011"][1])
        self.assertEqual(len(rows), 24)
        self.assertEqual({row["block"] for row in rows}, {"காஞ்சிபுரம்"})
        self.assertEqual({row["source_page"] for row in rows}, {1})
