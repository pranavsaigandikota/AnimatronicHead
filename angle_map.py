"""Pure RMS → jaw-angle helpers (no audio or serial imports)."""


def rms_to_angle(rms: float, min_rms: float, peak_rms: float, max_angle: int, response_curve: float = 1.0) -> int:
    if rms < min_rms:
        return 0
    ratio = (rms - min_rms) / (peak_rms - min_rms)
    ratio = max(0.0, min(1.0, ratio))
    return round(ratio ** response_curve * max_angle)


def should_send(target_angle: int, last_sent_angle: int, deadband: int) -> bool:
    return abs(target_angle - last_sent_angle) >= deadband or (
        target_angle == 0 and last_sent_angle != 0
    )
