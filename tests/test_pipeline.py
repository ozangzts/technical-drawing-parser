import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from technical_drawing_parser.pipeline import (
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
            prompt_path = outputs / "internal" / "example.vlm_prompt.txt"
            self.assertTrue(result_path.exists())
            self.assertTrue(internal_path.exists())
            self.assertTrue(prompt_path.exists())
            self.assertEqual(first_summary["processed"], 1)
            self.assertEqual(second_summary["skipped"], 1)

            result = json.loads(result_path.read_text(encoding="utf-8"))
            internal = json.loads(internal_path.read_text(encoding="utf-8"))
            self.assertEqual(result["source_file"], drawing.name)
            self.assertEqual(result["dimension_tables"], [])
            self.assertNotIn("fingerprint", result)
            self.assertNotIn("regions", result)
            self.assertEqual(internal["extraction"]["extractor"], "none")
            self.assertEqual(internal["extraction"]["status"], "not_run")
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

    def test_process_can_generate_ocr_target_crops(self) -> None:
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
                    "text": "#1,83",
                    "bbox": {"x": 500, "y": 300, "width": 40, "height": 12},
                    "source_ref": str(drawing) + "#page=1",
                    "engine": "test",
                    "confidence": 0.91,
                },
                {
                    "id": "page_001_ocr_002",
                    "page": 1,
                    "text": "3",
                    "bbox": {"x": 100, "y": 100, "width": 5, "height": 8},
                    "source_ref": str(drawing) + "#page=1",
                    "engine": "test",
                    "confidence": 0.95,
                },
            ]

            with patch(
                "technical_drawing_parser.pipeline.run_ocr_pages",
                return_value=ocr_blocks,
            ):
                summary = process_inputs(
                    drawing,
                    outputs,
                    generate_ocr_target_crops=True,
                )

            internal_path = outputs / "internal" / "example.internal.json"
            internal = json.loads(internal_path.read_text(encoding="utf-8"))

            self.assertEqual(summary["processed"], 1)
            self.assertEqual(len(internal["ocr_candidates"]), 2)
            self.assertEqual(len(internal["ocr_target_crops"]), 1)
            self.assertEqual(
                internal["ocr_target_crops"][0]["source_ocr_block_id"],
                "page_001_ocr_001",
            )
            self.assertTrue(Path(internal["ocr_target_crops"][0]["crop_ref"]).exists())

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
                    raw_response='{"target_id": "page_001_ocr_target_001", "page": 1, "classification": "metadata", "is_product_dimension": false, "raw_text": "2:1", "dimension": null, "metadata": {"field": "scale", "value": "2:1"}, "confidence": 0.88, "warnings": []}',
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
                    refine_ocr_targets=True,
                )

            result_path = outputs / "products" / "example.json"
            internal_path = outputs / "internal" / "example.internal.json"
            internal = json.loads(internal_path.read_text(encoding="utf-8"))
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
