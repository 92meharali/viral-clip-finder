"""Scene segmentation helpers."""

from __future__ import annotations

from app.reframe.models.scenes import SceneBoundary, SceneSegment


def merge_close_boundaries(
    boundaries: list[SceneBoundary],
    *,
    min_gap_seconds: float,
) -> list[SceneBoundary]:
    """Merge boundaries that occur within ``min_gap_seconds`` of each other."""
    if not boundaries:
        return []

    sorted_boundaries = sorted(boundaries, key=lambda item: item.timestamp)
    merged: list[SceneBoundary] = [sorted_boundaries[0]]

    for boundary in sorted_boundaries[1:]:
        previous = merged[-1]
        if boundary.timestamp - previous.timestamp < min_gap_seconds:
            if boundary.confidence > previous.confidence:
                merged[-1] = boundary
            continue
        merged.append(boundary)

    return merged


def build_scene_segments(
    boundaries: list[SceneBoundary],
    duration_seconds: float,
) -> list[SceneSegment]:
    """Build continuous scene segments from boundary timestamps."""
    if duration_seconds <= 0:
        return []

    cut_points = [0.0, *[boundary.timestamp for boundary in boundaries], duration_seconds]
    segments: list[SceneSegment] = []

    for index in range(len(cut_points) - 1):
        start = cut_points[index]
        end = cut_points[index + 1]
        if end <= start:
            continue
        segments.append(
            SceneSegment(
                index=index,
                start_seconds=start,
                end_seconds=end,
                duration_seconds=end - start,
            )
        )

    return segments
