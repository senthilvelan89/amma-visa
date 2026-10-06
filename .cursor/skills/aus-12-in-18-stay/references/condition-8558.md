# Condition 8558 — 12 months in 18 months

Source of the legal words: Migration Regulations 1994, Schedule 8.

> 8558 The holder must not stay in Australia for more than 12 months in any period of 18 months.

Home Affairs labels this **8558 – Non Resident**. It **may** be imposed on unsponsored subclass **600** Tourist stream visas. It is **not** automatic on every visitor visa. Check the grant letter or VEVO.

## How this repo uses it

Uma is on (and has previously held) subclass **600**. Parent visitor grants that last more than 12 months are commonly told they must not stay more than **12 months in any 18-month period**. Embassy wording for parent visitor visas:

- Multiple entries are allowed while the visa is valid.
- Do not stay more than 12 months continually **or** a total of 12 months in any 18-month period.
- Example: 12 months in Australia continuously, then **6 months outside** before returning.
- A visa can **cease** if the holder spends **more than 12 months continually** in Australia.
- Longer visitor visas are generally not considered if the parent is already in Australia, or has already spent 12 months in Australia in the last 18 months.

A short trip overseas does **not** reset the 12-month allowance. The window is rolling.

Visa expiry (Uma’s current 600: June 2028) is a different limit from the 12-in-18 stay cap.

## Counting method in the calculator

Home Affairs does not publish a worked arithmetic method. This skill’s script uses a conservative planning method:

1. Arrival day and departure day both count.
2. “18 months” = 18 calendar months: dates in `[start, start + 18 months)`.
3. “12 months” cap = calendar days in `[start, start + 12 months)` for that same window (365, or 366 if a leap day sits in the 12 months).
4. Every rolling window is tested; the tightest one is reported.

This is **not** legal advice and is **not** a Home Affairs ruling.

## What this rule is not

- **Not** the 870 stay length (3 or 5 years, 10 years total).
- **Not** the 143 PR queue wait.
- **Not** citizenship presence tests.
- Frequent Traveller stream uses **8573** (12 months in 24), which is a different condition.

Once Uma is granted **870**, condition 8558 on a 600 is no longer the stay framework. Until then, use this skill for 600 trip planning.
