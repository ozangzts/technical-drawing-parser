import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from technical_drawing_parser.config import load_dotenv


class ConfigTests(unittest.TestCase):
    def test_load_dotenv_sets_missing_values(self) -> None:
        with TemporaryDirectory() as directory:
            dotenv = Path(directory) / ".env"
            dotenv.write_text("TDP_EXTRACTOR=none\nTDP_MODEL=test-model\n", encoding="utf-8")

            old_extractor = os.environ.pop("TDP_EXTRACTOR", None)
            old_model = os.environ.pop("TDP_MODEL", None)
            try:
                load_dotenv(dotenv)
                self.assertEqual(os.environ["TDP_EXTRACTOR"], "none")
                self.assertEqual(os.environ["TDP_MODEL"], "test-model")
            finally:
                os.environ.pop("TDP_EXTRACTOR", None)
                os.environ.pop("TDP_MODEL", None)
                if old_extractor is not None:
                    os.environ["TDP_EXTRACTOR"] = old_extractor
                if old_model is not None:
                    os.environ["TDP_MODEL"] = old_model


if __name__ == "__main__":
    unittest.main()
