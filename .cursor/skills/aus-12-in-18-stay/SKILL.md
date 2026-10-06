---
name: aus-12-in-18-stay
description: Calculate days Uma stayed in Australia on each trip and test the rolling 12-months-in-18-months visitor rule (condition 8558). Use when counting stay days, remaining visitor days, 600 trip length, 12 in 18, 8558, or whether a planned trip would exceed the cap.
---

# Australia 12-in-18 stay calculator

Use this skill instead of counting dates by hand.

## When to use

- User asks how many days a trip is in Australia
- User asks whether a visit satisfies / would breach **12 months in 18 months**
- Planning the next subclass **600** stay before **870** is granted
- Recording new arrival/departure dates into the trip log

## What the rule is

Condition **8558**: the holder must not stay in Australia for more than **12 months in any period of 18 months**. Rolling window. A short trip overseas does **not** reset the clock.

Confirm 8558 on the grant letter or VEVO before treating it as attached to Uma’s visa. Details: [references/condition-8558.md](references/condition-8558.md)

This is a **planning tool**, not legal advice.

## Counting rules (do not change)

1. **Inclusive days:** arrival date and departure date both count. `2026-01-01` to `2026-01-03` = **3** days.
2. **18-month window:** 18 calendar months, rolling — not a calendar year.
3. **12-month cap:** calendar days in 12 months from that window’s start (365, or 366 if a leap day falls in).
4. **Continuous stay:** 12 months in a row, then typically **6 months outside** before return. More than 12 months continually can make the visa cease.

## How to calculate

Always run the script. Do not add dates in your head.

Script path (from repo root):

```bash
python3 .cursor/skills/aus-12-in-18-stay/scripts/calculate.py
```

### Ad-hoc trips

```bash
python3 .cursor/skills/aus-12-in-18-stay/scripts/calculate.py \
  --trip 2023-04-01:2023-09-20 \
  --trip 2024-11-02:2025-06-15 \
  --as-of 2026-10-06 \
  --propose 2026-11-01:2027-06-30
```

`--trip` and `--propose` are `arrive:depart` in `YYYY-MM-DD`. Inclusive.

### Saved trip log

Default file: [`data/uma-aus-trips.json`](../../../data/uma-aus-trips.json)

```bash
python3 .cursor/skills/aus-12-in-18-stay/scripts/calculate.py \
  --file data/uma-aus-trips.json \
  --as-of 2026-10-06
```

If the user gives new travel dates and wants them kept, add them to that JSON (`arrive`, `depart`, `notes`) and re-run.

`--json` prints machine-readable output.

After changing the script, run:

```bash
python3 .cursor/skills/aus-12-in-18-stay/scripts/calculate.py --self-test
```

## How to answer the user

Lead with the numbers:

- Days **this trip**
- **Total** recorded days
- Tightest 18-month window: days used / cap, remaining, exceeded or not
- If they proposed a trip: whether it **would exceed**, and remaining after including it
- Consecutive days allowed from `--as-of`, and the **last safe date** in that stretch

Then one short reminder: confirm 8558 on VEVO; visa expiry (June 2028) is a separate limit; 870 stay is not this rule.

If travel history is still TBD, ask for arrival and departure stamps / VEVO movement, then calculate. Do not invent trip dates.

## Missing dates

Uma has two prior 600 visits and a 600 valid until June 2028, but exact grant/travel dates are TBD in `claude.md`. Until those dates exist in `data/uma-aus-trips.json`, only calculate trips the user just supplied.
