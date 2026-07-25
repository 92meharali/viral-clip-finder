"""Framing geometry helpers for shot composition."""

from __future__ import annotations

from app.reframe.models.composition import FramingTarget
from app.reframe.models.faces import BoundingBox
from app.reframe.models.tracking import TrackedFace


def union_bounding_boxes(boxes: list[BoundingBox]) -> BoundingBox | None:
    """Return the smallest axis-aligned box containing all inputs."""
    if not boxes:
        return None

    left = min(box.x for box in boxes)
    top = min(box.y for box in boxes)
    right = max(box.x + box.width for box in boxes)
    bottom = max(box.y + box.height for box in boxes)
    return BoundingBox(x=left, y=top, width=right - left, height=bottom - top)


def _crop_dimensions_for_content(
    content_width: float,
    content_height: float,
    *,
    target_aspect: float,
) -> tuple[float, float]:
    """Compute the smallest crop with ``target_aspect`` that contains the content box."""
    if content_width <= 0 or content_height <= 0:
        return (1.0, 1.0)

    content_aspect = content_width / content_height
    if content_aspect > target_aspect:
        crop_width = content_width
        crop_height = crop_width / target_aspect
    else:
        crop_height = content_height
        crop_width = crop_height * target_aspect

    return (crop_width, crop_height)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def compute_framing_target(
    faces: list[TrackedFace],
    target_track_ids: list[str],
    *,
    image_width: int,
    image_height: int,
    target_aspect: float,
    min_padding: float,
    forehead_padding_ratio: float,
    rule_of_thirds_offset: float,
    zoom_multiplier: float,
) -> FramingTarget:
    """Build a framing target that keeps all target faces safely inside the crop."""
    selected = [face for face in faces if face.track_id in target_track_ids]
    if not selected:
        crop_width = float(image_width)
        crop_height = float(image_height)
        return FramingTarget(
            center_x=image_width / 2,
            center_y=image_height / 2,
            crop_width=crop_width,
            crop_height=crop_height,
        )

    union = union_bounding_boxes([face.bounding_box for face in selected])
    assert union is not None

    avg_face_height = sum(face.bounding_box.height for face in selected) / len(selected)
    padded = union.expand(min_padding)
    padded_top = max(0.0, padded.y - avg_face_height * forehead_padding_ratio)
    padded_height = padded.height + (padded.y - padded_top)
    content = BoundingBox(
        x=padded.x,
        y=padded_top,
        width=padded.width,
        height=padded_height,
    )

    crop_width, crop_height = _crop_dimensions_for_content(
        content.width,
        content.height,
        target_aspect=target_aspect,
    )
    crop_width = min(float(image_width), crop_width * zoom_multiplier)
    crop_height = min(float(image_height), crop_height * zoom_multiplier)

    center_x = content.center_x
    center_y = content.center_y - crop_height * rule_of_thirds_offset

    half_width = crop_width / 2
    half_height = crop_height / 2
    center_x = _clamp(center_x, half_width, image_width - half_width)
    center_y = _clamp(center_y, half_height, image_height - half_height)

    return FramingTarget(
        center_x=center_x,
        center_y=center_y,
        crop_width=crop_width,
        crop_height=crop_height,
    )
