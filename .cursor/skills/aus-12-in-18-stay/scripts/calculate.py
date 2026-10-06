#!/usr/bin/env python3
"""Plan subclass 600 stay against the rolling 12-months-in-18-months rule.

This is a planning tool, not legal advice. Home Affairs may count differently.
Confirm whether condition 8558 is on the visa via the grant letter or VEVO.

Counting rules used here:
- Arrival and departure dates both count as days in Australia (inclusive).
- The 18-month window is 18 calendar months: [start, start+18 months).
- The 12-month cap for a window is the number of calendar days in
  [start, start+12 months) — usually 365, or 366 when a leap day falls in.
- Any 18-month window is checked (rolling), not a fixed calendar year.
- A short trip overseas does not reset the clock.
"""

from __future__ import annotations

import argparse
import bisect
import calendar
import csv
import json
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable


def add_months(d: date, months: int) -> date:
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def parse_date(value: str) -> date:
    return datetime.strptime(value.strip(), "%Y-%m-%d").date()


def inclusive_days(arrive: date, depart: date) -> int:
    if depart < arrive:
        raise ValueError(f"depart {depart} is before arrive {arrive}")
    return (depart - arrive).days + 1


def daterange(start: date, end: date) -> Iterable[date]:
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)


@dataclass(frozen=True)
class Trip:
    arrive: date
    depart: date
    notes: str = ""

    @property
    def days(self) -> int:
        return inclusive_days(self.arrive, self.depart)

    def anniversary_12m(self) -> date:
        return add_months(self.arrive, 12)

    def continuous_12m_completed(self) -> bool:
        """True if the trip covers a full 12 calendar months of inclusive stay."""
        last_day_of_12m = add_months(self.arrive, 12) - timedelta(days=1)
        return self.depart >= last_day_of_12m

    def continuous_more_than_12m(self) -> bool:
        """True if still in Australia on the 12-month anniversary date."""
        return self.depart >= self.anniversary_12m()


@dataclass
class WindowHit:
    start: date
    end: date
    days_in_aus: int
    cap_days: int

    @property
    def remaining(self) -> int:
        return self.cap_days - self.days_in_aus

    @property
    def exceeded(self) -> bool:
        return self.days_in_aus > self.cap_days


def window_start_for_end(end_inclusive: date) -> date:
    """Start of the 18-month period whose last included day is end_inclusive."""
    return add_months(end_inclusive + timedelta(days=1), -18)


def twelve_month_cap_days(window_start: date) -> int:
    return (add_months(window_start, 12) - window_start).days


def present_days(trips: Iterable[Trip]) -> list[date]:
    days: set[date] = set()
    for trip in trips:
        days.update(daterange(trip.arrive, trip.depart))
    return sorted(days)


def count_in_span(sorted_days: list[date], start: date, end: date) -> int:
    return bisect.bisect_right(sorted_days, end) - bisect.bisect_left(sorted_days, start)


def worst_window(sorted_days: list[date]) -> WindowHit | None:
    if not sorted_days:
        return None
    first, last = sorted_days[0], sorted_days[-1]
    scan_from = window_start_for_end(first)
    scan_to = add_months(last, 18)
    worst: WindowHit | None = None
    for end in daterange(scan_from, scan_to):
        start = window_start_for_end(end)
        n = count_in_span(sorted_days, start, end)
        if n == 0:
            continue
        hit = WindowHit(
            start=start,
            end=end,
            days_in_aus=n,
            cap_days=twelve_month_cap_days(start),
        )
        if worst is None or (hit.days_in_aus - hit.cap_days, hit.days_in_aus) > (
            worst.days_in_aus - worst.cap_days,
            worst.days_in_aus,
        ):
            worst = hit
    return worst


def remaining_consecutive_days(
    trips: list[Trip], from_date: date, max_search: int = 400
) -> int:
    """Max extra consecutive days in Australia starting from_date without exceeding.

    Days already recorded as stay on/after from_date are kept; this only adds
    new days that are not already in a trip.
    """
    existing = set(present_days(trips))
    lo, hi, ans = 0, max_search, 0
    while lo <= hi:
        mid = (lo + hi) // 2
        extra_end = from_date + timedelta(days=mid - 1) if mid else from_date - timedelta(days=1)
        extra = []
        if mid > 0:
            extra = [Trip(from_date, extra_end, "probe")]
        merged_days = sorted(set(existing) | set(present_days(extra)))
        hit = worst_window(merged_days)
        if hit is None or not hit.exceeded:
            ans = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return ans


def parse_trip_token(token: str, notes: str = "") -> Trip:
    parts = token.split(":")
    if len(parts) != 2:
        raise ValueError(f"trip must be YYYY-MM-DD:YYYY-MM-DD, got {token!r}")
    return Trip(parse_date(parts[0]), parse_date(parts[1]), notes)


def load_data_file(path: Path) -> tuple[list[Trip], Trip | None, date | None]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return [], None, None
    if path.suffix.lower() == ".json":
        payload = json.loads(text)
        trips = [
            Trip(parse_date(row["arrive"]), parse_date(row["depart"]), row.get("notes", ""))
            for row in payload.get("trips", [])
        ]
        proposed = None
        if payload.get("proposed"):
            p = payload["proposed"]
            proposed = Trip(parse_date(p["arrive"]), parse_date(p["depart"]), p.get("notes", "proposed"))
        as_of = parse_date(payload["as_of"]) if payload.get("as_of") else None
        return trips, proposed, as_of

    trips: list[Trip] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            trips.append(
                Trip(
                    parse_date(row["arrive"]),
                    parse_date(row["depart"]),
                    (row.get("notes") or "").strip(),
                )
            )
    return trips, None, None


def report(
    trips: list[Trip],
    proposed: Trip | None,
    as_of: date | None,
) -> dict:
    as_of = as_of or date.today()
    base_days = present_days(trips)
    base_worst = worst_window(base_days)
    remaining_now = remaining_consecutive_days(trips, as_of)
    last_safe = as_of + timedelta(days=remaining_now - 1) if remaining_now > 0 else None

    proposed_block = None
    if proposed:
        with_proposed = trips + [proposed]
        prop_days = present_days(with_proposed)
        prop_worst = worst_window(prop_days)
        proposed_block = {
            "arrive": proposed.arrive.isoformat(),
            "depart": proposed.depart.isoformat(),
            "notes": proposed.notes,
            "days_this_trip": proposed.days,
            "worst_window": _window_dict(prop_worst),
            "would_exceed": bool(prop_worst and prop_worst.exceeded),
        }

    return {
        "as_of": as_of.isoformat(),
        "counting": {
            "arrival_and_departure_both_count": True,
            "window": "rolling 18 calendar months",
            "cap": "12 calendar months of days in that window",
            "condition": "8558 — must not stay in Australia for more than 12 months in any period of 18 months",
        },
        "trips": [
            {
                "arrive": t.arrive.isoformat(),
                "depart": t.depart.isoformat(),
                "notes": t.notes,
                "days_in_aus": t.days,
                "continuous_12m_completed": t.continuous_12m_completed(),
                "continuous_more_than_12m_cease_risk": t.continuous_more_than_12m(),
                "12m_anniversary": t.anniversary_12m().isoformat(),
            }
            for t in trips
        ],
        "total_recorded_days": len(base_days),
        "worst_window": _window_dict(base_worst),
        "remaining_consecutive_days_from_as_of": remaining_now,
        "last_safe_date_if_staying_from_as_of": last_safe.isoformat() if last_safe else None,
        "proposed": proposed_block,
        "disclaimer": (
            "Planning estimate only. Confirm 8558 on VEVO/grant letter. "
            "Not legal advice. Home Affairs may assess genuine-temporary-entrant "
            "stay even if the day count is under the cap."
        ),
    }


def _window_dict(hit: WindowHit | None) -> dict | None:
    if hit is None:
        return None
    return {
        "window_start": hit.start.isoformat(),
        "window_end": hit.end.isoformat(),
        "days_in_aus": hit.days_in_aus,
        "cap_days": hit.cap_days,
        "remaining_in_this_window": hit.remaining,
        "exceeded": hit.exceeded,
    }


def format_text(data: dict) -> str:
    lines = [
        "Australia 12-in-18 stay calculator (condition 8558 planning)",
        f"As of: {data['as_of']}",
        "",
        "Per trip (arrival and departure both count):",
    ]
    if not data["trips"]:
        lines.append("  (no trips recorded)")
    for trip in data["trips"]:
        flags = []
        if trip["continuous_12m_completed"]:
            flags.append("completed 12 calendar months continuous")
        if trip["continuous_more_than_12m_cease_risk"]:
            flags.append("MORE than 12 months continuous — visa-cease risk")
        extra = f"  [{'; '.join(flags)}]" if flags else ""
        lines.append(
            f"  {trip['arrive']} → {trip['depart']}: {trip['days_in_aus']} days"
            f"{f' ({trip['notes']})' if trip['notes'] else ''}{extra}"
        )
    lines.append(f"\nTotal recorded days in Australia: {data['total_recorded_days']}")
    worst = data["worst_window"]
    if worst:
        status = "EXCEEDS cap" if worst["exceeded"] else "within cap"
        lines.extend(
            [
                "",
                f"Tightest rolling 18-month window ({status}):",
                f"  {worst['window_start']} to {worst['window_end']}",
                f"  days in Australia: {worst['days_in_aus']} / {worst['cap_days']} cap",
                f"  remaining in this window: {worst['remaining_in_this_window']} days",
            ]
        )
    else:
        lines.append("\nNo stay days, so no 18-month window to test.")
    rem = data["remaining_consecutive_days_from_as_of"]
    last_safe = data["last_safe_date_if_staying_from_as_of"]
    if rem == 0:
        lines.append(
            f"\nStarting {data['as_of']}: 0 days — this model says she should not "
            "be in Australia on that date (a rolling 18-month window would already exceed 12 months)."
        )
    else:
        lines.append(
            f"\nIf she is in Australia from {data['as_of']} onwards "
            f"(that date counts): {rem} consecutive days allowed."
        )
        lines.append(f"Last date this model allows in that stretch: {last_safe}.")
        lines.append("Leave before the following day. A short trip overseas does not reset the 12-month cap.")
    prop = data["proposed"]
    if prop:
        lines.extend(
            [
                "",
                "Proposed extra trip:",
                f"  {prop['arrive']} → {prop['depart']}: {prop['days_this_trip']} days"
                f"{f' ({prop['notes']})' if prop['notes'] else ''}",
            ]
        )
        pw = prop["worst_window"]
        if pw:
            status = "WOULD EXCEED" if prop["would_exceed"] else "would stay within cap"
            lines.append(
                f"  with this trip included, tightest window: {pw['days_in_aus']} / {pw['cap_days']}"
                f" ({status}; remaining {pw['remaining_in_this_window']})"
            )
    lines.extend(["", data["disclaimer"]])
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Count days in Australia per trip and test the 12-in-18 rule."
    )
    parser.add_argument(
        "--trip",
        action="append",
        default=[],
        metavar="YYYY-MM-DD:YYYY-MM-DD",
        help="One stay. Repeat for multiple trips. Inclusive of both dates.",
    )
    parser.add_argument(
        "--file",
        type=Path,
        help="JSON (trips/proposed/as_of) or CSV with arrive,depart,notes columns.",
    )
    parser.add_argument(
        "--propose",
        metavar="YYYY-MM-DD:YYYY-MM-DD",
        help="A planned extra trip to test against the rolling cap.",
    )
    parser.add_argument("--as-of", metavar="YYYY-MM-DD", help="Date to measure remaining stay from.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of text.")
    parser.add_argument("--self-test", action="store_true", help="Run built-in checks and exit.")
    return parser


def run_self_tests() -> None:
    assert inclusive_days(date(2024, 1, 1), date(2024, 1, 1)) == 1
    assert inclusive_days(date(2024, 1, 1), date(2024, 1, 3)) == 3
    assert inclusive_days(date(2024, 1, 1), date(2024, 12, 31)) == 366  # leap year

    t = Trip(date(2024, 1, 1), date(2024, 12, 31))
    assert t.days == 366
    assert t.continuous_12m_completed()
    assert not t.continuous_more_than_12m()
    assert t.anniversary_12m() == date(2025, 1, 1)

    over = Trip(date(2024, 1, 1), date(2025, 1, 1))
    assert over.continuous_more_than_12m()

    full_year = [Trip(date(2024, 1, 1), date(2024, 12, 31), "full year")]
    hit = worst_window(present_days(full_year))
    assert hit is not None
    assert hit.days_in_aus == 366
    assert hit.cap_days == 366
    assert not hit.exceeded
    # Last day of the 12-month stay is allowed; the next day is not.
    assert remaining_consecutive_days(full_year, date(2024, 12, 31)) == 1
    assert remaining_consecutive_days(full_year, date(2025, 1, 1)) == 0
    assert remaining_consecutive_days([], date(2026, 10, 6)) == 365

    # After 12 months in, 6 months out, a 1 Jul 2025 return is the embassy example.
    with_return = full_year + [Trip(date(2025, 7, 1), date(2025, 7, 1), "return")]
    hit2 = worst_window(present_days(with_return))
    assert hit2 is not None
    assert not hit2.exceeded, hit2

    # A short overseas break does not reset: 11 months in, 2 weeks out, 2 more months in.
    split = [
        Trip(date(2024, 1, 1), date(2024, 11, 30)),
        Trip(date(2024, 12, 15), date(2025, 2, 14)),
    ]
    hit3 = worst_window(present_days(split))
    assert hit3 is not None
    assert hit3.days_in_aus == (
        inclusive_days(date(2024, 1, 1), date(2024, 11, 30))
        + inclusive_days(date(2024, 12, 15), date(2025, 2, 14))
    )

    proposed_over = Trip(date(2025, 1, 1), date(2025, 6, 30), "too much")
    data = report(full_year, proposed_over, date(2025, 1, 1))
    assert data["proposed"]["would_exceed"]

    print("self-test: ok")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.self_test:
        run_self_tests()
        return 0

    trips: list[Trip] = []
    proposed: Trip | None = None
    as_of: date | None = parse_date(args.as_of) if args.as_of else None

    if args.file:
        file_trips, file_proposed, file_as_of = load_data_file(args.file)
        trips.extend(file_trips)
        proposed = file_proposed
        as_of = as_of or file_as_of

    for token in args.trip:
        trips.append(parse_trip_token(token))
    if args.propose:
        proposed = parse_trip_token(args.propose, notes="proposed")

    trips.sort(key=lambda t: t.arrive)
    data = report(trips, proposed, as_of)
    if args.json:
        json.dump(data, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(format_text(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
