import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from technical_drawing_parser.pipeline import (
    build_refinement_review_decisions,
    build_ocr_target_refinement_summary,
    build_output_slug,
    process_inputs,
)


class PipelineTests(unittest.TestCase):
    def test_process_writes_product_json_and_skips_repeat_content(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            inputs = root / "inputs"
            outputs = root / "outputs"
            inputs.mkdir()
            drawing = inputs / "Example Drawing.jpg"
            drawing.write_bytes(b"\xff\xd8\xff\xd9")

            first_summary = process_inputs(drawing, outputs)
            second_summary = process_inputs(drawing, outputs)

            result_path = outputs / "products" / "example.json"
            internal_path = outputs / "internal" / "example.internal.json"
            review_path = outputs / "internal" / "reviews" / "example.review.json"
            prompt_path = outputs / "internal" / "example.vlm_prompt.txt"
            self.assertTrue(result_path.exists())
            self.assertTrue(internal_path.exists())
            self.assertTrue(review_path.exists())
            self.assertTrue(prompt_path.exists())
            self.assertEqual(first_summary["processed"], 1)
            self.assertEqual(second_summary["skipped"], 1)

            result = json.loads(result_path.read_text(encoding="utf-8"))
            internal = json.loads(internal_path.read_text(encoding="utf-8"))
            review = json.loads(review_path.read_text(encoding="utf-8"))
            self.assertEqual(result["source_file"], drawing.name)
            self.assertIsNone(result["sheet"])
            self.assertEqual(result["dimension_tables"], [])
            self.assertEqual(result["tables"], [])
            self.assertNotIn("fingerprint", result)
            self.assertNotIn("regions", result)
            self.assertEqual(internal["extraction"]["extractor"], "none")
            self.assertEqual(internal["extraction"]["status"], "not_run")
            self.assertEqual(review["product"]["path"], str(result_path))
            self.assertEqual(review["counts"]["dimensions"], 0)
            self.assertEqual(review["coverage"]["covered_by_dimensions_count"], 0)
            self.assertEqual(
                review["coverage"]["covered_by_dimension_tables_count"],
                0,
            )
            self.assertIn("Schema:", prompt_path.read_text(encoding="utf-8"))

    def test_build_output_slug_prefers_brand_and_code(self) -> None:
        self.assertEqual(
            build_output_slug("DEICO_DE8135_Technical_Drawing_page-0001"),
            "deico_de8135",
        )

    def test_ocr_target_refinement_summary_marks_dimension_table_coverage(self) -> None:
        refinements = [
            {
                "target_id": "page_001_ocr_target_001",
                "ocr_text": "800",
                "status": "completed",
                "refinement_json": {
                    "classification": "dimension",
                    "is_product_dimension": True,
                    "dimension": {
                        "raw_text": "800",
                        "value": "800",
                        "unit": "mm",
                        "type": "linear",
                    },
                    "confidence": 0.95,
                },
            },
            {
                "target_id": "page_001_ocr_target_002",
                "ocr_text": "950",
                "status": "completed",
                "refinement_json": {
                    "classification": "dimension",
                    "is_product_dimension": True,
                    "dimension": {
                        "raw_text": "950",
                        "value": "950",
                        "unit": "mm",
                        "type": "linear",
                    },
                    "confidence": 0.9,
                },
            },
        ]
        product_json = {
            "dimensions": [],
            "dimension_tables": [
                {
                    "rows": [
                        {
                            "label": "DE12000",
                            "values": ["DE12000", "20U", "800", "SINGLE"],
                        }
                    ]
                }
            ],
        }

        summary = build_ocr_target_refinement_summary(
            refinements,
            full_page_product_json=product_json,
        )

        self.assertEqual(summary["dimensions"], 2)
        self.assertEqual(len(summary["covered_by_dimension_tables"]), 1)
        self.assertEqual(
            summary["covered_by_dimension_tables"][0]["target_id"],
            "page_001_ocr_target_001",
        )
        self.assertEqual(len(summary["new_dimension_candidates"]), 1)
        self.assertEqual(
            summary["new_dimension_candidates"][0]["target_id"],
            "page_001_ocr_target_002",
        )

    def test_ocr_target_refinement_summary_marks_metadata_conflicts(self) -> None:
        refinements = [
            {
                "target_id": "page_001_ocr_target_001",
                "ocr_text": "05.09.2025",
                "status": "completed",
                "refinement_json": {
                    "classification": "metadata",
                    "metadata": {
                        "field": "REVISION DATE",
                        "value": "05.09.2025",
                    },
                    "confidence": 1.0,
                },
            },
            {
                "target_id": "page_001_ocr_target_002",
                "ocr_text": "A3",
                "status": "completed",
                "refinement_json": {
                    "classification": "metadata",
                    "metadata": {
                        "field": "sheet size",
                        "value": "A3",
                    },
                    "confidence": 0.9,
                },
            },
        ]
        product_json = {
            "revision_date": "09.09.2021",
            "size": "A3",
        }

        summary = build_ocr_target_refinement_summary(
            refinements,
            full_page_product_json=product_json,
        )

        self.assertEqual(summary["metadata"], 2)
        self.assertEqual(len(summary["metadata_review_candidates"]), 2)
        self.assertEqual(
            summary["metadata_review_candidates"][0]["field"],
            "revision_date",
        )
        self.assertEqual(
            summary["metadata_review_candidates"][0]["status"],
            "conflict",
        )
        self.assertEqual(
            summary["metadata_review_candidates"][1]["field"],
            "size",
        )
        self.assertEqual(
            summary["metadata_review_candidates"][1]["status"],
            "supported",
        )

    def test_refinement_review_decisions_keep_review_actionable(self) -> None:
        decisions = build_refinement_review_decisions(
            {
                "new_dimension_candidates": [
                    {
                        "target_id": "page_001_ocr_target_001",
                        "ocr_text": "950",
                        "dimension": {
                            "raw_text": "950",
                            "value": "950",
                            "unit": "mm",
                            "type": "linear",
                        },
                        "confidence": 0.91,
                    },
                    {
                        "target_id": "page_001_ocr_target_002",
                        "ocr_text": "2,1",
                        "dimension": {
                            "raw_text": "2,1",
                            "value": "2,1",
                            "unit": "mm",
                            "type": "linear",
                        },
                        "confidence": 0.62,
                    },
                    {
                        "target_id": "page_001_ocr_target_006",
                        "ocr_text": "慄 12",
                        "visual_text": "X 12",
                        "ocr_text_supported": True,
                        "dimension": {
                            "raw_text": "X 12",
                            "value": "12",
                            "unit": None,
                            "type": "pattern",
                        },
                        "confidence": 0.95,
                    },
                ],
                "covered_by_dimensions": [
                    {
                        "target_id": "page_001_ocr_target_003",
                        "ocr_text": "100",
                        "confidence": 0.99,
                    }
                ],
                "metadata_review_candidates": [
                    {
                        "target_id": "page_001_ocr_target_004",
                        "ocr_text": "05.09.2025",
                        "field": "revision_date",
                        "product_value": "09.09.2021",
                        "refinement_value": "05.09.2025",
                        "confidence": 1.0,
                        "status": "conflict",
                    },
                    {
                        "target_id": "page_001_ocr_target_005",
                        "ocr_text": "A3",
                        "field": "size",
                        "product_value": "A3",
                        "refinement_value": "A3",
                        "confidence": 0.94,
                        "status": "supported",
                    },
                ],
            }
        )

        self.assertEqual(len(decisions["merge_ready"]), 1)
        self.assertEqual(
            decisions["merge_ready"][0]["target_id"],
            "page_001_ocr_target_001",
        )
        self.assertEqual(len(decisions["needs_review"]), 3)
        self.assertEqual(
            [item["kind"] for item in decisions["needs_review"]],
            ["dimension", "dimension", "metadata"],
        )
        self.assertNotIn(
            "page_001_ocr_target_003",
            [item.get("target_id") for item in decisions["needs_review"]],
        )

    def test_process_can_generate_overlapping_crops(self) -> None:
        from PIL import Image

        with TemporaryDirectory() as directory:
            root = Path(directory)
            outputs = root / "outputs"
            drawing = root / "Example Drawing.png"
            Image.new("RGB", (1200, 800), "white").save(drawing)

            summary = process_inputs(drawing, outputs, generate_crops=True)

            internal_path = outputs / "internal" / "example.internal.json"
            internal = json.loads(internal_path.read_text(encoding="utf-8"))

            self.assertEqual(summary["processed"], 1)
            self.assertEqual(len(internal["tiles"]), 2)
            self.assertEqual(internal["tiles"][0]["type"], "tile")
            self.assertEqual(internal["tiles"][0]["bbox"]["x"], 0)
            self.assertTrue(Path(internal["tiles"][0]["crop_ref"]).exists())

    def test_process_can_run_ocr_internally(self) -> None:
        from PIL import Image

        with TemporaryDirectory() as directory:
            root = Path(directory)
            outputs = root / "outputs"
            drawing = root / "Example Drawing.png"
            Image.new("RGB", (1200, 800), "white").save(drawing)

            ocr_blocks = [
                {
                    "id": "page_001_ocr_001",
                    "page": 1,
                    "text": "Ø1,83",
                    "bbox": {"x": 10, "y": 20, "width": 30, "height": 12},
                    "source_ref": str(drawing) + "#page=1",
                    "engine": "test",
                    "confidence": 0.9,
                }
            ]

            with patch(
                "technical_drawing_parser.pipeline.run_ocr_pages",
                return_value=ocr_blocks,
            ):
                summary = process_inputs(drawing, outputs, run_ocr=True)

            internal_path = outputs / "internal" / "example.internal.json"
            internal = json.loads(internal_path.read_text(encoding="utf-8"))

            self.assertEqual(summary["processed"], 1)
            self.assertEqual(internal["raw_ocr_blocks"], ocr_blocks)
            self.assertEqual(len(internal["ocr_candidates"]), 1)
            self.assertEqual(
                internal["ocr_candidates"][0]["full_page_status"],
                "not_found_in_full_page",
            )
            self.assertEqual(internal["ocr_target_crops"], [])
            self.assertEqual(internal["ocr_target_refinements"], [])
            self.assertIn(
                "OCR target refinement was skipped because no VLM extractor is enabled.",
                internal["warnings"],
            )

    def test_process_can_refine_ocr_target_crops_internally(self) -> None:
        from PIL import Image

        with TemporaryDirectory() as directory:
            root = Path(directory)
            outputs = root / "outputs"
            drawing = root / "Example Drawing.png"
            Image.new("RGB", (1200, 800), "white").save(drawing)

            ocr_blocks = [
                {
                    "id": "page_001_ocr_001",
                    "page": 1,
                    "text": "2:1",
                    "bbox": {"x": 500, "y": 300, "width": 40, "height": 12},
                    "source_ref": str(drawing) + "#page=1",
                    "engine": "test",
                    "confidence": 0.91,
                }
            ]
            responses = [
                SimpleNamespace(
                    status="completed",
                    raw_response='{"product_name": "Full Page", "dimensions": [], "tolerances": [], "notes": [], "warnings": []}',
                    error=None,
                ),
                SimpleNamespace(
                    status="completed",
                    raw_response='{"target_id": "page_001_ocr_target_001", "page": 1, "classification": "metadata", "is_product_dimension": false, "raw_text": "2:1", "visual_text": "2:1", "ocr_text_supported": true, "dimension": null, "metadata": {"field": "scale", "value": "2:1"}, "confidence": 0.88, "warnings": []}',
                    error=None,
                ),
            ]

            with patch(
                "technical_drawing_parser.pipeline.run_ocr_pages",
                return_value=ocr_blocks,
            ), patch(
                "technical_drawing_parser.pipeline.extract_with_ollama",
                side_effect=responses,
            ) as extractor:
                summary = process_inputs(
                    drawing,
                    outputs,
                    extractor="ollama",
                    model="test-model",
                    run_ocr=True,
                )

            result_path = outputs / "products" / "example.json"
            internal_path = outputs / "internal" / "example.internal.json"
            review_path = outputs / "internal" / "reviews" / "example.review.json"
            internal = json.loads(internal_path.read_text(encoding="utf-8"))
            review = json.loads(review_path.read_text(encoding="utf-8"))
            result = json.loads(result_path.read_text(encoding="utf-8"))

            self.assertEqual(summary["processed"], 1)
            self.assertEqual(extractor.call_count, 2)
            self.assertEqual(result["product_name"], "Full Page")
            self.assertEqual(len(internal["ocr_target_crops"]), 1)
            self.assertEqual(len(internal["ocr_target_refinements"]), 1)
            refinement = internal["ocr_target_refinements"][0]
            self.assertEqual(refinement["status"], "completed")
            self.assertEqual(
                refinement["refinement_json"]["classification"],
                "metadata",
            )
            self.assertEqual(
                refinement["refinement_json"]["metadata"]["field"],
                "scale",
            )
            self.assertEqual(
                internal["ocr_target_refinement_summary"]["targets"],
                1,
            )
            self.assertEqual(
                internal["ocr_target_refinement_summary"]["metadata"],
                1,
            )
            self.assertEqual(
                internal["ocr_target_refinement_summary"]["merge_candidates"],
                [],
            )
            self.assertEqual(review["counts"]["ocr_target_refinements"], 1)
            self.assertEqual(review["review"]["merge_ready"], [])
            self.assertEqual(len(review["review"]["needs_review"]), 1)
            self.assertEqual(review["review"]["needs_review"][0]["kind"], "metadata")
            self.assertEqual(review["review"]["needs_review"][0]["field"], "scale")
            self.assertEqual(
                review["review"]["needs_review"][0]["visual_text"],
                "2:1",
            )
            self.assertIs(
                review["review"]["needs_review"][0]["ocr_text_supported"],
                True,
            )
            self.assertTrue(Path(refinement["raw_response_path"]).exists())

    def test_process_can_extract_generated_crops_internally(self) -> None:
        from PIL import Image

        with TemporaryDirectory() as directory:
            root = Path(directory)
            outputs = root / "outputs"
            drawing = root / "Example Drawing.png"
            Image.new("RGB", (1200, 800), "white").save(drawing)

            responses = [
                SimpleNamespace(
                    status="completed",
                    raw_response='{"product_name": "Full Page", "dimensions": [], "tolerances": [], "notes": [], "warnings": []}',
                    error=None,
                ),
                SimpleNamespace(
                    status="completed",
                    raw_response='{"product_name": "Tile 1", "dimensions": [{"raw_text": "1,83", "value": "1,83", "unit": "mm", "type": "diameter", "quantity": 1, "label": "PAD DIAMETER", "context": null}], "tolerances": [], "notes": [], "warnings": []}',
                    error=None,
                ),
                SimpleNamespace(
                    status="completed",
                    raw_response='{"product_name": "Tile 2", "dimensions": [{"raw_text": "1.83", "value": "1.83", "unit": "mm", "type": "diameter", "quantity": 1, "label": "PAD DIAMETER", "context": null}], "tolerances": [], "notes": [], "warnings": []}',
                    error=None,
                ),
            ]

            with patch(
                "technical_drawing_parser.pipeline.extract_with_ollama",
                side_effect=responses,
            ) as extractor:
                summary = process_inputs(
                    drawing,
                    outputs,
                    extractor="ollama",
                    model="test-model",
                    extract_crops=True,
                )

            result_path = outputs / "products" / "example.json"
            internal_path = outputs / "internal" / "example.internal.json"
            tile_summary_path = outputs / "internal" / "example.tile_summary.json"
            internal = json.loads(internal_path.read_text(encoding="utf-8"))
            tile_summary = json.loads(tile_summary_path.read_text(encoding="utf-8"))
            result = json.loads(result_path.read_text(encoding="utf-8"))

            self.assertEqual(summary["processed"], 1)
            self.assertEqual(extractor.call_count, 3)
            self.assertEqual(result["product_name"], "Full Page")
            self.assertEqual(len(internal["tiles"]), 2)
            self.assertEqual(len(internal["tile_extractions"]), 2)
            self.assertEqual(
                internal["tile_extractions"][0]["product_json"]["product_name"],
                "Tile 1",
            )
            self.assertTrue(
                Path(internal["tile_extractions"][0]["raw_response_path"]).exists()
            )
            self.assertEqual(
                internal["tile_extraction_summary"]["dimensions_found"],
                2,
            )
            self.assertEqual(
                len(internal["tile_extraction_summary"]["duplicate_candidate_groups"]),
                1,
            )
            self.assertEqual(tile_summary["dimensions_found"], 2)
            self.assertEqual(
                internal["tile_summary_path"],
                str(tile_summary_path),
            )
            self.assertEqual(
                len(internal["tile_extraction_summary"]["full_page_supported_candidates"]),
                0,
            )
            self.assertEqual(
                len(internal["tile_extraction_summary"]["tile_only_candidates"]),
                2,
            )

    def test_process_pdf_renders_all_pages_but_writes_one_product_json(self) -> None:
        try:
            import fitz
        except ImportError:
            self.skipTest("PyMuPDF is not installed.")

        with TemporaryDirectory() as directory:
            root = Path(directory)
            outputs = root / "outputs"
            drawing = root / "Example Drawing.pdf"

            document = fitz.open()
            document.new_page(width=100, height=100)
            document.new_page(width=200, height=100)
            document.save(drawing)
            document.close()

            summary = process_inputs(drawing, outputs)

            result_path = outputs / "products" / "example.json"
            internal_path = outputs / "internal" / "example.internal.json"
            self.assertEqual(summary["processed"], 1)
            self.assertTrue(result_path.exists())
            self.assertTrue((outputs / "internal" / "page_images" / "example_page_001.png").exists())
            self.assertTrue((outputs / "internal" / "page_images" / "example_page_002.png").exists())

            result = json.loads(result_path.read_text(encoding="utf-8"))
            internal = json.loads(internal_path.read_text(encoding="utf-8"))
            self.assertEqual(result["source_file"], drawing.name)
            self.assertEqual(len(internal["rendered_pages"]), 2)
            self.assertEqual(len(internal["regions"]), 2)
            self.assertEqual(internal["regions"][1]["page"], 2)
            self.assertIn("product JSON uses page 1", result["warnings"][1])

    def test_process_pdf_runs_page_level_ollama_extraction(self) -> None:
        try:
            import fitz
        except ImportError:
            self.skipTest("PyMuPDF is not installed.")

        with TemporaryDirectory() as directory:
            root = Path(directory)
            outputs = root / "outputs"
            drawing = root / "Example Drawing.pdf"

            document = fitz.open()
            document.new_page(width=100, height=100)
            document.new_page(width=100, height=100)
            document.save(drawing)
            document.close()

            responses = [
                SimpleNamespace(
                    status="completed",
                    raw_response='{"product_name": "Page 1", "dimensions": [], "tolerances": [], "notes": [], "warnings": []}',
                    error=None,
                ),
                SimpleNamespace(
                    status="completed",
                    raw_response='{"product_name": "Page 2", "dimensions": [], "tolerances": [], "notes": [], "warnings": []}',
                    error=None,
                ),
            ]

            with patch(
                "technical_drawing_parser.pipeline.extract_with_ollama",
                side_effect=responses,
            ) as extractor:
                summary = process_inputs(
                    drawing,
                    outputs,
                    extractor="ollama",
                    model="test-model",
                )

            result_path = outputs / "products" / "example.json"
            internal_path = outputs / "internal" / "example.internal.json"
            page_2_raw_path = outputs / "internal" / "example_page_002.raw_response.txt"

            result = json.loads(result_path.read_text(encoding="utf-8"))
            internal = json.loads(internal_path.read_text(encoding="utf-8"))

            self.assertEqual(summary["processed"], 1)
            self.assertEqual(extractor.call_count, 2)
            self.assertEqual(result["product_name"], "Page 1")
            self.assertTrue(page_2_raw_path.exists())
            self.assertEqual(len(internal["page_extractions"]), 2)
            self.assertEqual(
                internal["page_extractions"][1]["raw_response_path"],
                str(page_2_raw_path),
            )
            self.assertEqual(
                internal["page_extractions"][1]["product_json"]["product_name"],
                "Page 2",
            )


if __name__ == "__main__":
    unittest.main()
