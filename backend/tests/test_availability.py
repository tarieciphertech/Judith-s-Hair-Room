from datetime import date, time

from app.availability import build_end, generate_slots, overlaps


def test_available_non_overlapping_slot():
    assert overlaps(time(12), time(15), time(10), time(12)) is False


def test_exact_duplicate_overlaps():
    assert overlaps(time(10), time(13), time(10), time(13)) is True


def test_partial_overlap_at_start():
    assert overlaps(time(12), time(15), time(10), time(13)) is True


def test_existing_appointment_surrounds_request():
    assert overlaps(time(11), time(12), time(10), time(13)) is True


def test_back_to_back_appointments_are_allowed():
    assert overlaps(time(13), time(16), time(10), time(13)) is False


def test_duration_calculation():
    assert build_end(time(10), 180) == time(13)


def test_different_duration_slots():
    slots = generate_slots(date(2026, 9, 5), 120, time(8), time(18))
    assert slots[0].start == time(8)
    assert slots[0].end == time(10)
    assert slots[-1].end == time(18)


def test_slots_never_run_past_closing():
    slots = generate_slots(date(2026, 9, 5), 240, time(8), time(18))
    assert all(slot.end <= time(18) for slot in slots)


def test_overlap_boundary_is_half_open():
    assert overlaps(time(13), time(15), time(10), time(13)) is False
