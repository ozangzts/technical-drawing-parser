import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from technical_drawing_parser.extraction.prompt import (
    build_ocr_target_refinement_prompt,
    build_tile_vlm_prompt,
    build_vlm_prompt,
)


class PromptTests(unittest.TestCase):
    def test_prompts_warn_against_symbolic_reference_dimensions(self) -> None:
        source_file = Path("drawing.pdf")

        full_page_prompt = build_vlm_prompt(source_file)
        tile_prompt = build_tile_vlm_prompt(
            source_file,
            {
                "id": "page_001_tile_001",
                "page": 1,
                "bbox": {"x": 0, "y": 0, "width": 100, "height": 100},
            },
        )

        self.assertIn("single-letter symbolic references", full_page_prompt)
        self.assertIn("single-letter symbolic references", tile_prompt)

    def test_prompts_preserve_visible_metadata_values(self) -> None:
        source_file = Path("drawing.pdf")

        full_page_prompt = build_vlm_prompt(source_file)
        tile_prompt = build_tile_vlm_prompt(
            source_file,
            {
                "id": "page_001_tile_001",
                "page": 1,
                "bbox": {"x": 0, "y": 0, "width": 100, "height": 100},
            },
        )

        self.assertIn("Preserve visible title-block values exactly", full_page_prompt)
        self.assertIn("Preserve visible title-block values exactly", tile_prompt)
        self.assertIn("Do not assign isolated numbers", full_page_prompt)
        self.assertIn("Do not assign isolated numbers", tile_prompt)

    def test_prompts_distinguish_brand_product_and_drawing_number(self) -> None:
        prompt = build_vlm_prompt(Path("drawing.pdf"))

        self.assertIn("brand_name", prompt)
        self.assertIn("not product_name", prompt)
        self.assertIn("drawing_number", prompt)
        self.assertIn("document_name", prompt)
        self.assertIn("source file name is only a processing hint", prompt)
        self.assertIn("Do not use a full filename", prompt)

    def test_prompts_warn_against_unit_inference(self) -> None:
        source_file = Path("drawing.pdf")
        full_page_prompt = build_vlm_prompt(source_file)
        tile_prompt = build_tile_vlm_prompt(
            source_file,
            {
                "id": "page_001_tile_001",
                "page": 1,
                "bbox": {"x": 0, "y": 0, "width": 100, "height": 100},
            },
        )
        ocr_target_prompt = build_ocr_target_refinement_prompt(
            source_file,
            {
                "id": "page_001_ocr_target_001",
                "page": 1,
                "bbox": {"x": 0, "y": 0, "width": 100, "height": 40},
                "text": "12.5",
                "ocr_bbox": {"x": 10, "y": 10, "width": 50, "height": 12},
            },
        )

        self.assertIn("Do not infer dimension unit", full_page_prompt)
        self.assertIn("Do not infer dimension unit", tile_prompt)
        self.assertIn("Do not infer mm", ocr_target_prompt)
        self.assertIn("applies only to physical product dimensions", full_page_prompt)
        self.assertIn("pin numbers", full_page_prompt)
        self.assertIn("scale values", ocr_target_prompt)
        self.assertIn("Do not convert decimal commas", full_page_prompt)
        self.assertIn("Do not convert decimal commas", tile_prompt)
        self.assertIn("Do not convert decimal commas", ocr_target_prompt)

    def test_prompts_require_readable_table_rows(self) -> None:
        source_file = Path("drawing.pdf")
        full_page_prompt = build_vlm_prompt(source_file)
        tile_prompt = build_tile_vlm_prompt(
            source_file,
            {
                "id": "page_001_tile_001",
                "page": 1,
                "bbox": {"x": 0, "y": 0, "width": 100, "height": 100},
            },
        )

        self.assertIn("one logical item per row", full_page_prompt)
        self.assertIn("cells as a list of objects", full_page_prompt)
        self.assertIn("separate columns array", full_page_prompt)
        self.assertIn("numbered specification sections", full_page_prompt)
        self.assertIn("one logical item per row", tile_prompt)

    def test_prompts_offer_legend_table_as_a_table_type(self) -> None:
        source_file = Path("drawing.pdf")
        full_page_prompt = build_vlm_prompt(source_file)
        tile_prompt = build_tile_vlm_prompt(
            source_file,
            {
                "id": "page_001_tile_001",
                "page": 1,
                "bbox": {"x": 0, "y": 0, "width": 100, "height": 100},
            },
        )

        self.assertIn("legend_table", full_page_prompt)
        self.assertIn("legend_table", tile_prompt)

    def test_prompts_clarify_drawing_number_vs_form_control_stamp(self) -> None:
        source_file = Path("drawing.pdf")
        full_page_prompt = build_vlm_prompt(source_file)
        tile_prompt = build_tile_vlm_prompt(
            source_file,
            {
                "id": "page_001_tile_001",
                "page": 1,
                "bbox": {"x": 0, "y": 0, "width": 100, "height": 100},
            },
        )

        self.assertIn("embedded inside the product_name or document_name", full_page_prompt)
        self.assertIn("embedded inside the product_name or document_name", tile_prompt)
        self.assertIn("form control stamp", full_page_prompt)
        self.assertIn("form control stamp", tile_prompt)

    def test_prompts_extract_schematic_components_but_not_block_diagrams(self) -> None:
        source_file = Path("drawing.pdf")
        full_page_prompt = build_vlm_prompt(source_file)
        tile_prompt = build_tile_vlm_prompt(
            source_file,
            {
                "id": "page_001_tile_001",
                "page": 1,
                "bbox": {"x": 0, "y": 0, "width": 100, "height": 100},
            },
        )

        self.assertIn("reference designators", full_page_prompt)
        self.assertIn("reference designators", tile_prompt)
        self.assertIn("functional blocks and arrows with no", full_page_prompt)
        self.assertIn("functional blocks and arrows with no", tile_prompt)

    def test_prompts_ask_to_consolidate_repeated_schematic_parameters(self) -> None:
        source_file = Path("drawing.pdf")
        full_page_prompt = build_vlm_prompt(source_file)
        tile_prompt = build_tile_vlm_prompt(
            source_file,
            {
                "id": "page_001_tile_001",
                "page": 1,
                "bbox": {"x": 0, "y": 0, "width": 100, "height": 100},
            },
        )

        self.assertIn("list it once in parameters", full_page_prompt)
        self.assertIn("list it once in parameters", tile_prompt)
        self.assertIn("instead of adding one identical entry per unit", full_page_prompt)
        self.assertIn("instead of adding one identical entry per unit", tile_prompt)

    def test_prompts_note_gdt_in_warnings_instead_of_forcing_a_shape(self) -> None:
        source_file = Path("drawing.pdf")
        full_page_prompt = build_vlm_prompt(source_file)
        tile_prompt = build_tile_vlm_prompt(
            source_file,
            {
                "id": "page_001_tile_001",
                "page": 1,
                "bbox": {"x": 0, "y": 0, "width": 100, "height": 100},
            },
        )

        self.assertIn("feature control frame", full_page_prompt)
        self.assertIn("feature control frame", tile_prompt)
        self.assertIn("do not force it into dimensions or invent a shape for tolerances", full_page_prompt)
        self.assertIn("do not force it into dimensions or invent a shape for tolerances", tile_prompt)

    def test_prompts_distinguish_pattern_from_linear_dimension_type(self) -> None:
        source_file = Path("drawing.pdf")
        full_page_prompt = build_vlm_prompt(source_file)
        tile_prompt = build_tile_vlm_prompt(
            source_file,
            {
                "id": "page_001_tile_001",
                "page": 1,
                "bbox": {"x": 0, "y": 0, "width": 100, "height": 100},
            },
        )

        self.assertIn("repeated center-to-center spacing", full_page_prompt)
        self.assertIn("repeated center-to-center spacing", tile_prompt)
        self.assertIn("even if it also carries a quantity marker", full_page_prompt)
        self.assertIn("even if it also carries a quantity marker", tile_prompt)

    def test_prompts_distinguish_dimension_label_from_context(self) -> None:
        source_file = Path("drawing.pdf")
        full_page_prompt = build_vlm_prompt(source_file)
        tile_prompt = build_tile_vlm_prompt(
            source_file,
            {
                "id": "page_001_tile_001",
                "page": 1,
                "bbox": {"x": 0, "y": 0, "width": 100, "height": 100},
            },
        )

        self.assertIn("reusable category name", full_page_prompt)
        self.assertIn("reusable category name", tile_prompt)
        self.assertIn("Do not repeat raw_text or value in label", full_page_prompt)
        self.assertIn("Do not repeat raw_text or value in label", tile_prompt)

    def test_prompts_ask_for_consistent_row_column_order(self) -> None:
        source_file = Path("drawing.pdf")
        full_page_prompt = build_vlm_prompt(source_file)
        tile_prompt = build_tile_vlm_prompt(
            source_file,
            {
                "id": "page_001_tile_001",
                "page": 1,
                "bbox": {"x": 0, "y": 0, "width": 100, "height": 100},
            },
        )

        self.assertIn("same column order in every row", full_page_prompt)
        self.assertIn("same column order in every row", tile_prompt)

    def test_ocr_target_prompt_requires_visual_text_verification(self) -> None:
        prompt = build_ocr_target_refinement_prompt(
            Path("drawing.pdf"),
            {
                "id": "page_001_ocr_target_001",
                "page": 1,
                "bbox": {"x": 0, "y": 0, "width": 100, "height": 40},
                "text": "13:100",
                "ocr_bbox": {"x": 10, "y": 10, "width": 50, "height": 12},
            },
        )

        self.assertIn("OCR text is only a hint", prompt)
        self.assertIn("visual_text", prompt)
        self.assertIn("ocr_text_supported", prompt)
        self.assertIn("do not use the OCR hint", prompt)
        self.assertIn("Set is_product_dimension to true only", prompt)
        self.assertIn("local_context", prompt)
        self.assertIn("visible_label", prompt)
        self.assertIn("isolated number", prompt)


if __name__ == "__main__":
    unittest.main()
