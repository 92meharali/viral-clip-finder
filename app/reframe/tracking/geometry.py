"""Bounding box geometry helpers for face tracking."""

from __future__ import annotations

from app.reframe.models.faces import BoundingBox


def intersection_over_union(box_a: BoundingBox, box_b: BoundingBox) -> float:
    """Compute IoU between two axis-aligned bounding boxes."""
    x_left = max(box_a.x, box_b.x)
    y_top = max(box_a.y, box_b.y)
    x_right = min(box_a.x + box_a.width, box_b.x + box_b.width)
    y_bottom = min(box_a.y + box_a.height, box_b.y + box_b.height)

    if x_right <= x_left or y_bottom <= y_top:
        return 0.0

    intersection = (x_right - x_left) * (y_bottom - y_top)
    union = box_a.area + box_b.area - intersection
    if union <= 0:
        return 0.0
    return intersection / union


def center_distance(box_a: BoundingBox, box_b: BoundingBox) -> float:
    """Euclidean distance between bounding box centers."""
    ax, ay = box_a.center
    bx, by = box_b.center
    return float(((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5)
