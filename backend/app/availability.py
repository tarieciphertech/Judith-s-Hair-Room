from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

BLOCKING_STATUSES = frozenset({'PENDING', 'CONFIRMED', 'IN_PROGRESS'})

@dataclass(frozen=True)
class Slot:
    start: time
    end: time


def overlaps(start: time, end: time, other_start: time, other_end: time) -> bool:
    return start < other_end and end > other_start


def build_end(start: time, duration_minutes: int) -> time:
    value = datetime.combine(date.today(), start) + timedelta(minutes=duration_minutes)
    if value.date() != date.today():
        raise ValueError('Appointment cannot run past midnight')
    return value.time()


def generate_slots(
    day: date,
    duration_minutes: int,
    opening_time: time,
    closing_time: time,
    step_minutes: int = 30,
) -> list[Slot]:
    cursor = datetime.combine(day, opening_time)
    close = datetime.combine(day, closing_time)
    duration = timedelta(minutes=duration_minutes)
    slots: list[Slot] = []
    while cursor + duration <= close:
        slots.append(Slot(cursor.time(), (cursor + duration).time()))
        cursor += timedelta(minutes=step_minutes)
    return slots
