import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from technical_drawing_parser.crops import (
    generate_overlapping_tiles,
    generate_tile_bboxes,
)


class CropTests(unittest.TestCase):
    def test_generate_tile_bboxes_cover_page_with_overlap(self) -> None:
        bboxes = generate_tile_bboxes(
            width=2481,
            height=1754,
            tile_size=1024,
            overlap_px=256,
            min_edge_tile=384,
        )

        self.assertEqual(len(bboxes), 6)
        self.assertEqual(bboxes[0], {"x": 0, "y": 0, "width": 1024, "height": 1024})
        self.assertEqual(bboxes[-1]["x"] + bboxes[-1]["width"], 2481)
        self.assertEqual(bboxes[-1]["y"] + bboxes[-1]["height"], 1754)
        self.assertLess(bboxes[1]["x"], bboxes[0]["x"] + bboxes[0]["width"])

    def test_generate_overlapping_tiles_writes_crop_files(self) -> None:
        from PIL import Image

        with TemporaryDirectory() as directory:
            root = Path(directory)
            image_path = root / "page.png"
            output_dir = root / "crops"
            Image.new("RGB", (1200, 800), "white").save(image_path)

            tiles = generate_overlapping_tiles(
                image_path=image_path,
                output_dir=output_dir,
                output_slug="drawing",
                page=1,
                source_ref="drawing.pdf#page=1",
            )

            self.assertEqual(len(tiles), 2)
            self.assertEqual(tiles[0]["id"], "page_001_tile_001")
            self.assertEqual(tiles[0]["overlap_px"], 256)
            self.assertTrue(Path(str(tiles[0]["crop_ref"])).exists())


if __name__ == "__main__":
    unittest.main()
