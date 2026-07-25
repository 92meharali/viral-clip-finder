"""Safe crop geometry helpers."""

from __future__ import annotations

from app.reframe.models.crop import CropFrame
from app.reframe.models.faces import BoundingBox
from app.reframe.models.tracking import TrackedFace


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def max_vertical_crop_size(
    source_width: int,
    source_height: int,
    target_aspect: float,
) -> tuple[float, float]:
    """Return the largest 9:16 crop window that fits inside the source frame."""
    crop_height = float(source_height)
    crop_width = crop_height * target_aspect
    if crop_width > source_width:
        crop_width = float(source_width)
        crop_height = crop_width / target_aspect
    return (crop_width, crop_height)


def crop_from_center(
    *,
    frame_number: int,
    timestamp: float,
    center_x: float,
    center_y: float,
    crop_width: float,
    crop_height: float,
    source_width: int,
    source_height: int,
) -> CropFrame:
    """Build a fixed-size crop window centered on a point, clamped to the source."""
    half_width = crop_width / 2
    half_height = crop_height / 2
    clamped_x = _clamp(center_x, half_width, float(source_width) - half_width)
    clamped_y = _clamp(center_y, half_height, float(source_height) - half_height)
    return CropFrame(
        frame_number=frame_number,
        timestamp=timestamp,
        x=clamped_x - half_width,
        y=clamped_y - half_height,
        width=crop_width,
        height=crop_height,
    )


def pan_fixed_crop_for_faces(
    crop: CropFrame,
    faces: list[TrackedFace],
    *,
    source_width: int,
    source_height: int,
    face_padding: float,
) -> CropFrame:
    """Shift a fixed-size crop window to keep faces visible without resizing."""
    if not faces:
        return crop

    boxes = [face.bounding_box.expand(face_padding) for face in faces]
    union = _union_boxes(boxes)
    assert union is not None

    half_width = crop.width / 2
    half_height = crop.height / 2
    center_x = _clamp(
        _center_to_include(crop.center_x, half_width, union.x, union.x + union.width),
        half_width,
        float(source_width) - half_width,
    )
    center_y = _clamp(
        _center_to_include(crop.center_y, half_height, union.y, union.y + union.height),
        half_height,
        float(source_height) - half_height,
    )

    return CropFrame(
        frame_number=crop.frame_number,
        timestamp=crop.timestamp,
        x=center_x - half_width,
        y=center_y - half_height,
        width=crop.width,
        height=crop.height,
    )


def camera_state_to_crop(
    *,
    frame_number: int,
    timestamp: float,
    center_x: float,
    center_y: float,
    crop_width: float,
    crop_height: float,
) -> CropFrame:
    """Convert a virtual camera state into a top-left crop rectangle."""
    return CropFrame(
        frame_number=frame_number,
        timestamp=timestamp,
        x=center_x - crop_width / 2,
        y=center_y - crop_height / 2,
        width=crop_width,
        height=crop_height,
    )


def clamp_crop_to_source(
    crop: CropFrame,
    *,
    source_width: int,
    source_height: int,
    target_aspect: float,
) -> CropFrame:
    """Clamp a crop rectangle to remain inside the source frame."""
    width = min(float(source_width), crop.width)
    height = min(float(source_height), crop.height)

    if width / height > target_aspect:
        height = width / target_aspect
    else:
        width = height * target_aspect

    width = min(width, float(source_width))
    height = min(height, float(source_height))

    x = _clamp(crop.center_x - width / 2, 0.0, float(source_width) - width)
    y = _clamp(crop.center_y - height / 2, 0.0, float(source_height) - height)

    return CropFrame(
        frame_number=crop.frame_number,
        timestamp=crop.timestamp,
        x=x,
        y=y,
        width=width,
        height=height,
    )


def enforce_face_safety(
    crop: CropFrame,
    faces: list[TrackedFace],
    *,
    source_width: int,
    source_height: int,
    target_aspect: float,
    face_padding: float,
) -> CropFrame:
    """Expand or shift the crop so tracked faces remain fully visible."""
    if not faces:
        return clamp_crop_to_source(
            crop,
            source_width=source_width,
            source_height=source_height,
            target_aspect=target_aspect,
        )

    boxes = [face.bounding_box.expand(face_padding) for face in faces]
    union = _union_boxes(boxes)
    assert union is not None

    width = crop.width
    height = crop.height
    center_x = crop.center_x
    center_y = crop.center_y

    if union.width > width or union.height > height:
        width, height = _crop_dimensions_for_content(
            union.width,
            union.height,
            target_aspect=target_aspect,
        )
        width = min(width, float(source_width))
        height = min(height, float(source_height))

    half_width = width / 2
    half_height = height / 2
    center_x = _clamp(
        _center_to_include(center_x, half_width, union.x, union.x + union.width),
        half_width,
        float(source_width) - half_width,
    )
    center_y = _clamp(
        _center_to_include(center_y, half_height, union.y, union.y + union.height),
        half_height,
        float(source_height) - half_height,
    )

    return CropFrame(
        frame_number=crop.frame_number,
        timestamp=crop.timestamp,
        x=center_x - width / 2,
        y=center_y - height / 2,
        width=width,
        height=height,
    )


def _union_boxes(boxes: list[BoundingBox]) -> BoundingBox | None:
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


def _center_to_include(
    center: float,
    half_extent: float,
    content_min: float,
    content_max: float,
) -> float:
    crop_min = center - half_extent
    crop_max = center + half_extent

    if content_min < crop_min:
        center += content_min - crop_min
    if content_max > crop_max:
        center += content_max - crop_max

    return center


def face_visibility_ratio(crop: CropFrame, face: TrackedFace) -> float:
    """Return the fraction of a face bounding box visible inside the crop."""
    box = face.bounding_box
    overlap_left = max(crop.x, box.x)
    overlap_top = max(crop.y, box.y)
    overlap_right = min(crop.x + crop.width, box.x + box.width)
    overlap_bottom = min(crop.y + crop.height, box.y + box.height)

    if overlap_right <= overlap_left or overlap_bottom <= overlap_top:
        return 0.0

    overlap_area = (overlap_right - overlap_left) * (overlap_bottom - overlap_top)
    return overlap_area / box.area if box.area > 0 else 0.0
