# SPDX-License-Identifier: GPL-3.0-only
"""Locate the chest reward action without reading language-dependent text."""
import cv2
import numpy as np


def chest_button_target(image):
    """Return the normalized action center in a 360x800 reference frame.

    The reward pages use either one wide green control or a matched pair of
    green and yellow controls with a dark progress badge. In the latter case,
    return the yellow control to open the remaining batch. Text is never read;
    ambiguous images yield None.
    """
    if image is None or image.shape != (800, 360, 3) or image.dtype != np.uint8:
        return None
    # Most frames have no bright-green action. A small subsample rejects them
    # before allocating and analyzing the full bottom-region mask.
    samples = cv2.cvtColor(image[670:760:3, ::4], cv2.COLOR_BGR2HSV)
    sample_mask = cv2.inRange(samples, (30, 95, 110), (90, 255, 255))
    green_peak = np.count_nonzero(sample_mask, axis=1).max(initial=0)
    if green_peak < 24:
        return None
    yellow_sample = cv2.inRange(samples, (15, 100, 150), (35, 255, 255))
    # Both halves must occur on the same row. This cheaply rejects boss panel
    # borders, whose unrelated green and orange areas occur on different rows.
    green_left = np.count_nonzero(sample_mask[:, :45], axis=1)
    yellow_right = np.count_nonzero(yellow_sample[:, 45:], axis=1)
    split_candidate = bool(np.any((green_left >= 24) & (yellow_right >= 24)))
    if green_peak < 54 and not split_candidate:
        return None
    # A dimmed background distinguishes this overlay from bright game screens.
    if np.mean(np.max(image[80:200, :80], axis=2) < 100) < .60:
        return None
    top = 620
    hsv = cv2.cvtColor(image[top:780], cv2.COLOR_BGR2HSV)
    green = cv2.inRange(hsv, (30, 95, 110), (90, 255, 255))
    green = cv2.morphologyEx(green, cv2.MORPH_CLOSE, np.ones((3, 7), np.uint8))
    _, _, stats, _ = cv2.connectedComponentsWithStats(green)
    if split_candidate:
        yellow = cv2.inRange(hsv, (15, 100, 150), (35, 255, 255))
        yellow = cv2.morphologyEx(yellow, cv2.MORPH_CLOSE, np.ones((3, 7), np.uint8))
        _, _, yellow_stats, _ = cv2.connectedComponentsWithStats(yellow)
        pairs = []
        for row in stats[1:]:
            lx, ly, lw, lh, la = map(int, row)
            lc = lx + lw/2
            if not (100 <= lw <= 195 and 23 <= lh <= 65 and 670 <= ly+top <= 750
                    and 55 <= lc <= 145 and la >= .58*lw*lh):
                continue
            # The progress capsule overlaps the top of the green button. Its
            # dark purple body remains even when its characters are obscured.
            x1 = max(0, round(lc - .15*lw)); x2 = min(360, round(lc + .15*lw))
            y1 = ly + 2; y2 = min(hsv.shape[0], ly + 8)
            badge = hsv[y1:y2, x1:x2]
            if not badge.size:
                continue
            dark_purple = cv2.inRange(badge, (100, 45, 0), (170, 255, 100))
            if cv2.countNonZero(dark_purple) < dark_purple.size * .33:
                continue
            for other in yellow_stats[1:]:
                rx, ry, rw, rh, ra = map(int, other)
                rc = rx + rw/2
                gap = rx - (lx + lw)
                if not (100 <= rw <= 195 and 23 <= rh <= 65 and 215 <= rc <= 305
                        and -1 <= gap <= 40 and abs(ly-ry) <= 8 and abs(lh-rh) <= 10
                        and abs(lw-rw) <= .25*max(lw,rw) and abs(lc+rc-360) <= 28
                        and ra >= .58*rw*rh):
                    continue
                pairs.append((rc/360., (ry+top+rh/2)/800.))
        if len(pairs) == 1:
            return pairs[0]
        if len(pairs) > 1:
            return None
    matching = []
    for row in stats[1:]:
        x, y, w, h, area = map(int, row)
        y += top
        cx = x + w / 2
        if not (w >= 260 and 22 <= h <= 65 and 670 <= y <= 750
                and 144 <= cx <= 216 and y+h <= 780 and area >= .60*w*h):
            continue
        # Behind the overlay is the dimmed round teal advance control. This
        # is a separate signal from the green rectangle and is checked relative
        # to its position, rather than assuming a fixed pixel location.
        x1 = max(0, round(cx - 40)); x2 = min(360, round(cx + 40))
        y1 = max(0, y-top-74); y2 = max(y1, y-top-3)
        backdrop = hsv[y1:y2, x1:x2]
        if not backdrop.size:
            continue
        teal = cv2.inRange(backdrop, (65, 70, 25), (100, 255, 150))
        if cv2.countNonZero(teal) < teal.size * .20:
            continue
        matching.append((cx / 360., (y + h/2) / 800.))
    return matching[0] if len(matching) == 1 else None
