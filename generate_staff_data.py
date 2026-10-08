"""Generate SYNTHETIC staff, availability and shift-preference data for Shiftr.

SYNTHETIC DATA: invented for the MSIN0023 Shiftr prototype. The people, wages
and restaurant are fictional. Do not present this as real operational data.

Restaurant (from Team_Project_Context, agreed spec): small-to-medium Italian
restaurant in central London. 50 dining seats (bookings + walk-ins) and a
separate 10-stool bar (walk-ins only). Lunch, dinner and bar drinks, open to
customers 11:00-00:00, 7 days a week.

Outputs (written to the data/ folder next to scripts/):
    staff.csv                       one row per staff member
    shift_blocks.csv                definition of the AM and PM shift blocks
    staff_availability_oct2026.csv  one row per staff member x date x block

Availability is a HARD constraint (0 = cannot work that block).
Preference is a SOFT constraint (+1 prefer, 0 neutral, -1 would rather not),
only given when the person is available.

Standard library only, so it runs on the ManSci VM or any Python 3.9+.
"""

import csv
import random
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

SEED = 2026          # change only if the team agrees; same seed = same data
YEAR, MONTH = 2026, 10
AD_HOC_UNAVAILABLE_RATE = 0.05   # chance an otherwise-available block is lost

OUT_DIR = Path(__file__).resolve().parent.parent / "data"

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# Customers 11:00-00:00. Staff arrive 1 h early to set up and stay 30 min to
# close. block: (start, end, duration_h, unpaid_break_min, paid_h)
# PM is over 6 h, so the Working Time Regulations require a 20-min rest break;
# we give an unpaid 30-min break.
SHIFT_BLOCKS = {
    "AM": ("10:00", "16:00", 6.0, 0, 6.0),
    "PM": ("16:00", "00:30", 8.5, 30, 8.0),
}

# Minimum available people per role per block, used only for the feasibility
# check below. Team assumptions, not sourced facts.
MIN_AVAILABLE = {
    ("Manager", "any"): 1,
    ("Chef", "Senior"): 1,
    ("Chef", "any"): 2,
    ("Kitchen Porter", "any"): 1,
    ("Bartender", "any"): 1,
    ("Server", "any"): 2,
}

# Hourly base pay, GBP, excluding tronc/tips (tips go to staff, not a labour
# cost to the restaurant). ESTIMATES for central London, informed by job
# adverts; all are above the GBP 12.71 National Living Wage (April 2026).
#
# staff_id, first_name, role, seniority, contract, hourly_wage_gbp,
# max_weekly_hours, preferred_block (AM/PM/Either), fixed unavailable weekdays
# (0 = Mon ... 6 = Sun), weekday the person would rather not work (or None),
# job_title
STAFF = [
    ("S01", "Amara",   "Manager",        "Senior", "Full-time", 24.00, 48, "Either", [0],    None, "General Manager"),
    ("S02", "Tomasz",  "Manager",        "Senior", "Full-time", 18.50, 45, "AM",     [2],    6,    "Assistant Manager"),
    ("S03", "Priya",   "Manager",        "Senior", "Part-time", 16.50, 30, "PM",     [0, 1], None, "Floor Supervisor"),
    ("S04", "Marco",   "Chef",           "Senior", "Full-time", 24.00, 48, "Either", [1],    None, "Head Chef"),
    ("S05", "Leila",   "Chef",           "Senior", "Full-time", 18.50, 48, "PM",     [],     6,    "Sous Chef"),
    ("S06", "Giulia",  "Chef",           "Senior", "Full-time", 16.50, 45, "AM",     [4],    None, "Senior Chef de Partie"),
    ("S07", "Daniel",  "Chef",           "Junior", "Full-time", 15.00, 45, "AM",     [3],    None, "Chef de Partie"),
    ("S08", "Sofia",   "Chef",           "Junior", "Full-time", 15.00, 40, "PM",     [0, 2], None, "Pizza Chef"),
    ("S09", "Kwame",   "Chef",           "Junior", "Part-time", 14.00, 30, "PM",     [1],    None, "Commis Chef"),
    ("S10", "Jun",     "Chef",           "Junior", "Part-time", 14.00, 25, "AM",     [4, 5], None, "Commis Chef"),
    ("S11", "Rocco",   "Chef",           "Junior", "Student",   14.00, 20, "PM",     [2],    None, "Commis Chef"),
    ("S12", "Olu",     "Kitchen Porter", "Junior", "Full-time", 13.85, 48, "Either", [2],    None, "Kitchen Porter"),
    ("S13", "Tariq",   "Kitchen Porter", "Junior", "Full-time", 13.85, 40, "AM",     [5],    None, "Kitchen Porter"),
    ("S14", "Ana",     "Kitchen Porter", "Junior", "Part-time", 13.85, 30, "PM",     [0, 1], None, "Kitchen Porter"),
    ("S15", "Ben",     "Kitchen Porter", "Junior", "Student",   13.85, 20, "PM",     [3],    None, "Kitchen Porter"),
    ("S16", "Chloe",   "Bartender",      "Senior", "Full-time", 16.00, 45, "PM",     [0],    None, "Head Bartender"),
    ("S17", "Matteo",  "Bartender",      "Junior", "Full-time", 14.50, 40, "Either", [3],    None, "Bartender"),
    ("S18", "Ravi",    "Bartender",      "Junior", "Part-time", 14.50, 30, "PM",     [1, 2], None, "Bartender"),
    ("S19", "Nadia",   "Bartender",      "Junior", "Part-time", 14.50, 25, "AM",     [5, 6], None, "Bartender"),
    ("S20", "Ella",    "Bartender",      "Junior", "Student",   14.00, 20, "PM",     [0],    6,    "Bartender"),
    ("S21", "Ruth",    "Server",         "Senior", "Full-time", 16.00, 45, "Either", [3],    None, "Head Waiter"),
    ("S22", "Omar",    "Server",         "Senior", "Full-time", 15.00, 45, "PM",     [1],    None, "Senior Waiter"),
    ("S23", "Francesca", "Server",       "Junior", "Full-time", 14.00, 40, "AM",     [6],    None, "Waiter"),
    ("S24", "Pedro",   "Server",         "Junior", "Full-time", 14.00, 40, "PM",     [2],    None, "Waiter"),
    ("S25", "Mia",     "Server",         "Junior", "Part-time", 14.00, 30, "AM",     [5, 6], None, "Waiter"),
    ("S26", "Luca",    "Server",         "Junior", "Part-time", 14.00, 30, "PM",     [0, 3], None, "Waiter"),
    ("S27", "Ibrahim", "Server",         "Junior", "Part-time", 14.00, 25, "Either", [5],    None, "Waiter"),
    ("S28", "Zara",    "Server",         "Junior", "Student",   13.50, 20, "PM",     [2],    None, "Waiter"),
    ("S29", "Noah",    "Server",         "Junior", "Student",   13.50, 20, "PM",     [4],    5,    "Waiter"),
    ("S30", "Grace",   "Server",         "Junior", "Student",   13.50, 20, "Either", [1],    None, "Waiter"),
    ("S31", "Elif",    "Server",         "Junior", "Part-time", 14.00, 30, "PM",     [0, 6], None, "Waiter"),
    ("S32", "Lily",   "Host",           "Junior", "Part-time", 14.00, 30, "PM",     [0, 1], None, "Host"),
    ("S33", "Jess",    "Host",           "Junior", "Student",   13.50, 20, "Either", [3],    None, "Host"),
    ("S34", "Sami",    "Host",           "Junior", "Part-time", 14.00, 25, "PM",     [4, 5], None, "Host"),
]

# New hires (team update 08/10/26 14:15) to close the kitchen cover gaps the
# optimiser reported against confirmed bookings. Appended at the END so every
# existing person's availability and preferences are unchanged (the random
# absences are drawn in list order).
NEW_HIRES = [
    ("S35", "Hugo",    "Chef",           "Senior", "Full-time", 16.50, 45, "Either", [0],    None, "Senior Chef de Partie"),
    ("S36", "Aisha",   "Chef",           "Junior", "Full-time", 15.00, 45, "PM",     [1],    None, "Chef de Partie"),
    ("S37", "Theo",    "Chef",           "Junior", "Part-time", 14.00, 30, "Either", [2, 3], None, "Commis Chef"),
    ("S38", "Kofi",    "Kitchen Porter", "Junior", "Part-time", 13.85, 25, "PM",     [3],    None, "Kitchen Porter"),
    ("S39", "Nina",    "Chef",           "Junior", "Part-time", 14.00, 24, "AM",     [0, 1, 2], None, "Commis Chef"),
    ("S40", "Dev",     "Manager",        "Senior", "Part-time", 16.50, 25, "PM",     [4, 5, 6], None, "Floor Supervisor"),
]
STAFF = STAFF + NEW_HIRES

# Pre-booked holidays (inclusive).
HOLIDAYS = {
    "S04": (date(2026, 10, 19), date(2026, 10, 25)),   # head chef: tests senior-chef cover
    "S21": (date(2026, 10, 1), date(2026, 10, 4)),     # head waiter
    "S16": (date(2026, 10, 26), date(2026, 10, 28)),   # head bartender: no senior on the bar
    "S23": (date(2026, 10, 26), date(2026, 10, 30)),   # London school half-term week
}


def month_dates(year, month):
    d = date(year, month, 1)
    while d.month == month:
        yield d
        d += timedelta(days=1)


def availability_for(member, d, block, rng):
    """Return (available, reason) for one staff member, date and block."""
    staff_id, contract, fixed_off = member[0], member[4], member[8]
    if staff_id in HOLIDAYS:
        start, end = HOLIDAYS[staff_id]
        if start <= d <= end:
            return 0, "Holiday"
    if d.weekday() in fixed_off:
        return 0, "Regular day off"
    # Students: lectures on weekday daytimes.
    if contract == "Student" and block == "AM" and d.weekday() < 5:
        return 0, "Study"
    if rng.random() < AD_HOC_UNAVAILABLE_RATE:
        return 0, "Personal"
    return 1, ""


def preference_for(member, d, block):
    preferred_block, avoid_weekday = member[7], member[9]
    if avoid_weekday is not None and d.weekday() == avoid_weekday:
        return -1
    if preferred_block == block:
        return 1
    return 0


def build_rows(rng):
    rows = []
    for member in STAFF:
        for d in month_dates(YEAR, MONTH):
            for block, (start, end, _dur, _brk, _paid) in SHIFT_BLOCKS.items():
                available, reason = availability_for(member, d, block, rng)
                rows.append({
                    "staff_id": member[0],
                    "date": d.isoformat(),
                    "weekday": WEEKDAYS[d.weekday()],
                    "block": block,
                    "block_start": start,
                    "block_end": end,
                    "available": available,
                    "unavailable_reason": reason,
                    "preference": preference_for(member, d, block) if available else "",
                })
    return rows


def write_csv(path, fieldnames, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def feasibility_check(rows):
    """Print role-by-block shortfalls in AVAILABLE people (not hours)."""
    staff_by_id = {m[0]: m for m in STAFF}
    counts = defaultdict(int)
    for r in rows:
        if r["available"]:
            m = staff_by_id[r["staff_id"]]
            counts[(r["date"], r["block"], m[2], "any")] += 1
            counts[(r["date"], r["block"], m[2], m[3])] += 1

    problems = []
    for d in month_dates(YEAR, MONTH):
        for block in SHIFT_BLOCKS:
            for (role, level), minimum in MIN_AVAILABLE.items():
                n = counts[(d.isoformat(), block, role, level)]
                if n < minimum:
                    problems.append(f"  {d} {block}: {n} available {level} {role} (need {minimum})")
    if problems:
        print("Availability shortfalls (the optimiser must report these as uncovered):")
        print("\n".join(problems))
    else:
        print("Every block has at least the minimum number of AVAILABLE people per role.")
    print("Note: this does not check hours. Max weekly hours may still make a week infeasible.")


def main():
    rng = random.Random(SEED)
    OUT_DIR.mkdir(exist_ok=True)

    staff_fields = ["staff_id", "first_name", "job_title", "role", "seniority", "contract",
                    "hourly_wage_gbp", "max_weekly_hours", "preferred_block"]
    write_csv(
        OUT_DIR / "staff.csv",
        staff_fields,
        [{"staff_id": m[0], "first_name": m[1], "job_title": m[10], "role": m[2],
          "seniority": m[3], "contract": m[4], "hourly_wage_gbp": m[5],
          "max_weekly_hours": m[6], "preferred_block": m[7]} for m in STAFF],
    )
    write_csv(
        OUT_DIR / "shift_blocks.csv",
        ["block", "start", "end", "duration_hours", "unpaid_break_minutes", "paid_hours"],
        [{"block": b, "start": s, "end": e, "duration_hours": dur,
          "unpaid_break_minutes": brk, "paid_hours": paid}
         for b, (s, e, dur, brk, paid) in SHIFT_BLOCKS.items()],
    )
    rows = build_rows(rng)
    write_csv(OUT_DIR / "staff_availability_oct2026.csv", list(rows[0].keys()), rows)

    n_available = sum(r["available"] for r in rows)
    print(f"Wrote {len(STAFF)} staff and {len(rows)} availability rows to {OUT_DIR}")
    print(f"Available staff-blocks: {n_available} of {len(rows)} ({n_available / len(rows):.0%})")
    feasibility_check(rows)


if __name__ == "__main__":
    main()
