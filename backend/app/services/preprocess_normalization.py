import cv2


def normalize_to_square(image, target_size: int, keep_ratio: bool = True, interpolation: str = "cubic", padding: str = "white"):
    interp_map = {
        "nearest": cv2.INTER_NEAREST,
        "linear": cv2.INTER_LINEAR,
        "cubic": cv2.INTER_CUBIC,
        "area": cv2.INTER_AREA,
        "lanczos4": cv2.INTER_LANCZOS4,
    }
    pad_map = {
        "white": (255, 255, 255),
        "black": (0, 0, 0),
        "gray": (128, 128, 128),
    }

    if interpolation not in interp_map:
        raise ValueError(f"Unsupported interpolation: {interpolation}")
    if padding not in pad_map:
        raise ValueError(f"Unsupported padding color: {padding}")

    height, width = image.shape[:2]
    if keep_ratio:
        scale = target_size / max(height, width)
        new_width = max(1, int(round(width * scale)))
        new_height = max(1, int(round(height * scale)))
    else:
        new_width = target_size
        new_height = target_size

    resize_interp = interp_map[interpolation]
    if max(height, width) > target_size and interpolation == "cubic":
        resize_interp = cv2.INTER_AREA

    resized = cv2.resize(image, (new_width, new_height), interpolation=resize_interp)
    if not keep_ratio:
        return resized

    pad_left = (target_size - new_width) // 2
    pad_right = target_size - new_width - pad_left
    pad_top = (target_size - new_height) // 2
    pad_bottom = target_size - new_height - pad_top

    return cv2.copyMakeBorder(
        resized,
        pad_top,
        pad_bottom,
        pad_left,
        pad_right,
        borderType=cv2.BORDER_CONSTANT,
        value=pad_map[padding],
    )
