"""Tests for viral clip models."""

import pytest
from pydantic import ValidationError

from app.models.clip import ClipAnalysisResponse, ViralClip, ViralClipBase


class TestViralClipBase:
    def test_normalizes_timestamps(self) -> None:
        clip = ViralClipBase(
            start="00:13",
            end="01:07",
            reason="Great moment",
            viral_score=9.0,
            emotion="shock",
            hook="Wait for it",
            summary="Something shocking happens.",
        )
        assert clip.start == "00:00:13"
        assert clip.end == "00:01:07"

    def test_rejects_invalid_score(self) -> None:
        with pytest.raises(ValidationError):
            ViralClipBase(
                start="00:00:13",
                end="00:00:45",
                reason="Great moment",
                viral_score=11.0,
                emotion="shock",
                hook="Wait for it",
                summary="Something shocking happens.",
            )


class TestViralClip:
    def test_from_base_computes_seconds(self) -> None:
        base = ViralClipBase(
            start="00:00:13",
            end="00:00:45",
            reason="Betrayal moment",
            viral_score=9.7,
            emotion="betrayal",
            hook="He trusted the wrong player.",
            summary="Alliance breaks down.",
        )
        clip = ViralClip.from_base(base)

        assert clip.start_seconds == 13.0
        assert clip.end_seconds == 45.0
        assert clip.duration_seconds == 32.0

    def test_rejects_end_before_start(self) -> None:
        with pytest.raises(ValidationError):
            ViralClip(
                start="00:01:00",
                end="00:00:30",
                reason="Invalid",
                viral_score=5.0,
                emotion="confusion",
                hook="Nope",
                summary="Bad timestamps",
                start_seconds=60.0,
                end_seconds=30.0,
                duration_seconds=-30.0,
            )


class TestClipAnalysisResponse:
    def test_parses_clip_list(self) -> None:
        response = ClipAnalysisResponse(
            clips=[
                ViralClipBase(
                    start="00:00:13",
                    end="00:00:45",
                    reason="Great moment",
                    viral_score=9.0,
                    emotion="shock",
                    hook="Wait for it",
                    summary="Something shocking happens.",
                )
            ]
        )
        assert len(response.clips) == 1
