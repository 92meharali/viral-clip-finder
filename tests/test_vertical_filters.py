"""Tests for vertical crop filter builders."""

from app.video.filters import (
    CROP_MODE_BLUR,
    CROP_MODE_CENTER,
    build_blur_background_filter,
    build_center_crop_filter,
)


class TestCenterCropFilter:
    def test_landscape_source_crops_sides(self) -> None:
        filt = build_center_crop_filter(1920, 1080, 1080, 1920)
        assert "crop=ih*1080/1920:ih" in filt
        assert "scale=1080:1920" in filt

    def test_portrait_source_scales_and_crops(self) -> None:
        filt = build_center_crop_filter(1080, 1920, 1080, 1920)
        assert "force_original_aspect_ratio=increase" in filt
        assert "crop=1080:1920" in filt

    def test_square_source_uses_landscape_crop(self) -> None:
        filt = build_center_crop_filter(1080, 1080, 1080, 1920)
        assert "crop=ih*1080/1920" in filt
        assert "scale=1080:1920" in filt


class TestBlurBackgroundFilter:
    def test_includes_blur_and_overlay(self) -> None:
        filt = build_blur_background_filter(1080, 1920, blur_strength=25)
        assert "boxblur=25:5" in filt
        assert "overlay=(W-w)/2:(H-h)/2[vout]" in filt
        assert "split=2" in filt

    def test_target_dimensions(self) -> None:
        filt = build_blur_background_filter(720, 1280)
        assert "scale=720:1280" in filt
        assert "crop=720:1280" in filt


class TestCropModeConstants:
    def test_mode_values(self) -> None:
        assert CROP_MODE_CENTER == "center_crop"
        assert CROP_MODE_BLUR == "blur_background"
