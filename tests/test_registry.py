import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from technical_drawing_parser.registry import should_process


class RegistryTests(unittest.TestCase):
    def test_should_skip_completed_fingerprint(self) -> None:
        registry = {
            "files": [
                {
                    "fingerprint": "sha256:abc",
                    "status": "completed",
                }
            ]
        }

        should_run, reason = should_process(
            registry=registry,
            fingerprint="sha256:abc",
            force=False,
            retry_failed=False,
        )

        self.assertFalse(should_run)
        self.assertEqual(reason, "already completed")

    def test_force_processes_completed_fingerprint(self) -> None:
        registry = {
            "files": [
                {
                    "fingerprint": "sha256:abc",
                    "status": "completed",
                }
            ]
        }

        should_run, reason = should_process(
            registry=registry,
            fingerprint="sha256:abc",
            force=True,
            retry_failed=False,
        )

        self.assertTrue(should_run)
        self.assertIsNone(reason)


if __name__ == "__main__":
    unittest.main()
