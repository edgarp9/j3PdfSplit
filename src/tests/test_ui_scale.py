"""Unit tests for shared DPI scaling helpers."""

import unittest

from pdf_splitter.ui.scaling import UiScale


class UiScaleTests(unittest.TestCase):
    """Verify baseline pixel values scale predictably."""

    def test_geometry_and_padding_scale_from_baseline_pixels(self) -> None:
        ui_scale = UiScale(factor=1.5, font_family="Malgun Gothic")

        self.assertEqual("1770x1140", ui_scale.geometry(1180, 760))
        self.assertEqual((18, 0, 18, 9), ui_scale.padding(12, 0, 12, 6))
        self.assertEqual((315, 420), ui_scale.size(210, 280))

    def test_font_uses_requested_family_without_scaling_point_size(self) -> None:
        ui_scale = UiScale(factor=2.0, font_family="Malgun Gothic")

        self.assertEqual(("Malgun Gothic", 10, "bold"), ui_scale.font(10, "bold"))


if __name__ == "__main__":
    unittest.main()
