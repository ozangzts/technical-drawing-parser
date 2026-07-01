import unittest
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from technical_drawing_parser.discovery import discover_inputs


class DiscoveryTests(unittest.TestCase):
    def test_discover_inputs_returns_supported_files(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            supported = root / "drawing.JPG"
            unsupported = root / "notes.txt"
            supported.write_bytes(b"example")
            unsupported.write_text("example", encoding="utf-8")

            self.assertEqual(discover_inputs(root), [supported])


if __name__ == "__main__":
    unittest.main()
