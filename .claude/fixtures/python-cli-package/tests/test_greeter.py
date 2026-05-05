import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cc_spec_sample import greet


class GreeterTests(unittest.TestCase):
    def test_greet_trims_name(self) -> None:
        self.assertEqual(greet(" Ada "), "hello, Ada")

    def test_greet_rejects_blank_name(self) -> None:
        with self.assertRaises(ValueError):
            greet("  ")


if __name__ == "__main__":
    unittest.main()
