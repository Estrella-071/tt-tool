# SPDX-License-Identifier: GPL-3.0-only
"""Read the numeric win rate from a bounded, independently located text band."""
import cv2
import numpy as np

_HORIZONTAL_FRAME = np.ones((1, 18), dtype=np.uint8)


def _runs(columns):
    groups, start = [], None
    for index, present in enumerate([*columns, False]):
        if present and start is None:
            start = index
        elif not present and start is not None:
            groups.append((start, index))
            start = None
    return groups


def _probability_mask(hsv):
    # The orange frame below the odds is the same hue as yellow numerals.  A
    # fixed vertical crop admits the frame after a small screen translation,
    # joining all glyphs.  Drop long horizontal frame runs and locate the
    # remaining line by its vertical extent.
    source = cv2.inRange(hsv[700:733, 235:325], (0, 100, 140), (90, 255, 255))
    frame = cv2.morphologyEx(source, cv2.MORPH_OPEN, _HORIZONTAL_FRAME)
    clean = cv2.bitwise_and(source, cv2.bitwise_not(frame))
    row_counts = np.count_nonzero(clean[:, 15:], axis=1)
    candidates = [(a, b) for a, b in _runs(row_counts >= 5) if 9 <= b-a <= 16]
    if not candidates:
        return None
    top, bottom = min(candidates, key=lambda p: abs((p[0]+p[1])/2 + 700 - 715))
    return clean[top:bottom]


def recognize_probability(hsv, digit_templates):
    """Return (base, bonus, confidence), or (None, None, score) if unclear.

    Unclear and incomplete glyphs are deliberately not interpreted as a
    shorter number. The numeric glyphs and percent signs are language-neutral.
    """
    mask = _probability_mask(hsv)
    if mask is None:
        return None, None, 0.0
    groups = _runs(np.any(mask != 0, axis=0))
    merged = []
    for a, b in groups:
        previous = merged[-1] if merged else None
        # Compression can break a percent sign at either dot or slash.  Both
        # the base and the bonus percent signs need this treatment.
        is_base_sign = (previous and 266 <= previous[0]+235 <= 295
                        and a-previous[1] <= 2 and b-previous[0] <= 17)
        is_bonus_sign = (previous and 308 <= previous[0]+235 <= 324
                         and a-previous[1] <= 2 and b-previous[0] <= 17)
        leading_dot = (previous and previous[1]-previous[0] <= 2
                       and a-previous[1] <= 1 and b-a >= 10)
        if is_base_sign or is_bonus_sign or leading_dot:
            merged[-1] = (previous[0], b)
        else:
            merged.append((a, b))
    groups = []
    for a, b in merged:
        if a + 235 >= 250 and 19 <= b-a <= 26:
            split = b - 13
            groups.extend(((a, split-1), (split, b)))
        else:
            groups.append((a, b))
    percent = next((i for i, (a, b) in enumerate(groups)
                    if 266 <= a+235 <= 303 and 10 <= b-a <= 17), None)
    if percent is None:
        return None, None, 0.0

    def digits_before(index, lower=0, minimum=1, max_gap=3):
        selected = []
        first_index = index
        right = groups[index][0]
        for group_index in range(index-1, lower-1, -1):
            a, b = groups[group_index]
            if right-b > max_gap or not 3 <= b-a <= 10:
                break
            selected.append((a, b))
            first_index = group_index
            right = a
            if len(selected) == 3:
                break
        selected.reverse()
        if len(selected) < minimum:
            return None, 0.0
        if minimum >= 2:
            # A severed stroke immediately before the first selected glyph can
            # turn 80 into a confident-looking 30 or 90 into 10. Never discard
            # such a fragment as though it were background.
            if first_index > lower:
                a, b = groups[first_index-1]
                if selected[0][0]-b <= 3 and b-a <= 3:
                    fragment = cv2.findNonZero(mask[:, a:b])
                    if fragment is not None and cv2.boundingRect(fragment)[3] >= 5:
                        return None, 0.0
        result, confidence = '', 1.0
        for index, (a, b) in enumerate(selected):
            segment = mask[:, a:b]
            points = cv2.findNonZero(segment)
            if points is None:
                return None, 0.0
            x, y, w, h = cv2.boundingRect(points)
            if h < 9:
                return None, 0.0
            digit = cv2.resize(segment[y:y+h, x:x+w], (16, 20),
                               interpolation=cv2.INTER_NEAREST) > 0
            scores = [max(float(np.mean(digit == t)) for t in variants)
                      for variants in digit_templates]
            best = int(np.argmax(scores))
            ordered = sorted(scores, reverse=True)
            # Compression can turn 2 into 7, 8 into 5, or bonus 8 into 3; use
            # stricter cutoffs for those candidates. Subpixel alignment can
            # soften 2, so allow a lower score only with a stronger lead.
            cutoff = (.79 if best == 7 else .78 if best == 5 and index == 0 and minimum >= 2 else
                      .80 if best == 3 and lower > 0 else .72 if best == 2 else .75)
            margin = .055 if best == 2 else .035
            if scores[best] < cutoff or ordered[0]-ordered[1] < margin:
                return None, scores[best]
            # A complete 1 is unusually narrow. A damaged 8 or 9 may resemble
            # it, so only accept a narrow leading glyph when it strongly matches
            # the supplied 1 template, with no discarded adjacent fragments.
            if index == 0 and minimum >= 2:
                if b-a < 6 and best != 1:
                    return None, scores[best]
                if best == 1 and scores[best] < .88:
                    return None, scores[best]
            result += str(best)
            confidence = min(confidence, scores[best])
        if minimum >= 2 and len(result) > 1 and result[0] == '0':
            return None, 0.0
        value = int(result)
        return (value, confidence) if value <= 100 else (None, 0.0)

    # A single surviving base digit could be the second digit of a partially
    # hidden two-digit rate. Require both rather than inventing a low rate.
    base, confidence = digits_before(percent, minimum=2)
    if base is None:
        return None, None, confidence
    bonus = 0
    second = next((i for i in range(percent+1, len(groups))
                   if 10 <= groups[i][1]-groups[i][0] <= 17), None)
    if percent+1 < len(groups):
        plus_a, plus_b = groups[percent+1]
        plus = 2 <= plus_a-groups[percent][1] <= 9 and 1 <= plus_b-plus_a <= 8
        if plus:
            if second is None:
                return None, None, 0.0
            bonus, extra_confidence = digits_before(second, percent+2, max_gap=5)
            if bonus is None:
                return None, None, extra_confidence
            confidence = min(confidence, extra_confidence)
        elif second is not None:
            return None, None, 0.0
        elif groups[percent][0]+235 < 288:
            # In the captured layout a base percentage shifted left leaves
            # room for the teammate bonus. If both plus and its percent were
            # lost to compression, omission would silently change the total.
            return None, None, 0.0
    elif groups[percent][0]+235 < 288:
        return None, None, 0.0
    return base, bonus, confidence
