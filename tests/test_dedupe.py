import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from technical_drawing_parser.dedupe import build_tile_extraction_summary


class DedupeTests(unittest.TestCase):
    def test_build_tile_extraction_summary_groups_overlapping_duplicate_dimensions(self) -> None:
        tile_extractions = [
            {
                "tile_id": "page_001_tile_001",
                "page": 1,
                "bbox": {"x": 0, "y": 0, "width": 1024, "height": 1024},
                "product_json": {
                    "dimensions": [
                        {
                            "raw_text": "1,83",
                            "value": "1,83",
                            "type": "diameter",
                            "label": "PAD DIAMETER",
                            "quantity": 1,
                        }
                    ]
                },
            },
            {
                "tile_id": "page_001_tile_002",
                "page": 1,
                "bbox": {"x": 768, "y": 0, "width": 1024, "height": 1024},
                "product_json": {
                    "dimensions": [
                        {
                            "raw_text": "1.83",
                            "value": "1.83",
                            "type": "diameter",
                            "label": "PAD DIAMETER",
                            "quantity": 1,
                        }
                    ]
                },
            },
            {
                "tile_id": "page_001_tile_003",
                "page": 1,
                "bbox": {"x": 2200, "y": 0, "width": 1024, "height": 1024},
                "product_json": {
                    "dimensions": [
                        {
                            "raw_text": "1.83",
                            "value": "1.83",
                            "type": "diameter",
                            "label": "PAD DIAMETER",
                            "quantity": 1,
                        }
                    ]
                },
            },
        ]

        full_page_product_json = {
            "dimensions": [
                {
                    "raw_text": "(x1) 1,83",
                    "value": "1,83",
                    "type": "diameter",
                    "label": "PAD DIAMETER",
                    "quantity": 1,
                }
            ]
        }

        summary = build_tile_extraction_summary(
            tile_extractions,
            full_page_product_json=full_page_product_json,
        )

        self.assertEqual(summary["tiles_processed"], 3)
        self.assertEqual(summary["dimensions_found"], 3)
        self.assertEqual(len(summary["duplicate_candidate_groups"]), 1)
        self.assertEqual(summary["duplicate_candidate_groups"][0]["candidate_count"], 2)
        self.assertEqual(
            summary["duplicate_candidate_groups"][0]["classification"],
            "strong_duplicate",
        )
        self.assertEqual(
            summary["review_summary"]["strong_duplicate_groups"],
            1,
        )
        self.assertEqual(len(summary["full_page_supported_candidates"]), 3)
        self.assertEqual(len(summary["tile_only_candidates"]), 0)
        self.assertEqual(len(summary["unique_dimension_candidates"]), 1)


if __name__ == "__main__":
    unittest.main()
