# SPDX-License-Identifier: GPL-3.0-only
"""Detect the transient battle-result ribbon without reading game text."""

import cv2
import numpy as np


def is_battle_result(image):
    """Return whether a normalized 360x800 BGR frame has a result ribbon.

    The result animation has a darkened background, a wide gold or purple
    ribbon, and a magenta lower-right edge.  Sampling the flanks leaves the
    central text free to vary with the game's language.  Unknown frames return
    False; callers must not treat this as proof that a battle did not end.
    """
    if image is None or image.shape != (800, 360, 3) or image.dtype != np.uint8:
        return False

    # Only this section of the normalized game viewport is needed.  Keeping
    # the calculation local avoids converting the full preview every frame.
    hsv = cv2.cvtColor(image[130:318], cv2.COLOR_BGR2HSV)
    top = hsv[0:40]
    dark = cv2.inRange(top, (0, 0, 0), (179, 255, 55))
    if cv2.countNonZero(dark) < dark.size * 0.60:
        return False

    # The slanted magenta accent is on the right-hand end of the lower edge,
    # rather than across the centre.  It distinguishes a coloured game scene
    # or ordinary rectangular dialog header from this particular ribbon.
    edge = hsv[148:188, 280:350]
    pink = cv2.inRange(edge, (140, 145, 145), (179, 255, 255))
    if cv2.countNonZero(pink) < pink.size * 0.055:
        return False

    left = hsv[70:150, 15:75]
    right = hsv[70:150, 285:345]
    for low, high in (((12, 90, 150), (40, 255, 255)),
                      ((125, 80, 90), (170, 255, 255))):
        left_color = cv2.inRange(left, low, high)
        right_color = cv2.inRange(right, low, high)
        if (cv2.countNonZero(left_color) >= left_color.size * 0.55
                and cv2.countNonZero(right_color) >= right_color.size * 0.55):
            return True
    return False
