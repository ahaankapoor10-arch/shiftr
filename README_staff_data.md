# Staff availability and preferences: October 2026 (SYNTHETIC)

**Synthetic data.** The restaurant, people and wages are invented for the Shiftr prototype. This is not real operational data.

To regenerate, run `scripts/generate_staff_data.py` and then `scripts/export_staff_excel.py`. The seed is 2026, so the same seed always gives the same files.

## The restaurant (team spec in Team_Project_Context)

Small-to-medium Italian restaurant in central London:
- **Dining room:** 50 seats, taking bookings and walk-ins.
- **Bar:** a separate 10-stool bar, walk-ins only.
- **Service:** lunch, dinner and bar drinks, open to customers 11:00–00:00, 7 days a week.

## Files

| File | Contents |
|---|---|
| `Shiftr_Staff_Availability_Oct2026.xlsx` | The workbook. Sheets: README, Staff, Shift_Blocks, Rules, Availability, Availability_Grid, Coverage_Check |
| `staff.csv` | 34 staff. Columns: `staff_id`, `first_name`, `job_title`, `role`, `seniority`, `contract`, `hourly_wage_gbp`, `max_weekly_hours`, `preferred_block` |
| `shift_blocks.csv` | **AM** 10:00–16:00, 6 h paid. **PM** 16:00–00:30, 8.5 h including a 30-min unpaid break, so 8 h paid |
| `staff_availability_oct2026.csv` | 2,108 rows, one per staff × date × block |

### Roster

| Role | Count | Who |
|---|---|---|
| Manager | 3 | General Manager, Assistant Manager, Floor Supervisor |
| Chef | 8 | Senior: Head Chef, Sous Chef, Senior CDP. Junior: CDP, Pizza Chef, 3 Commis |
| Kitchen Porter | 4 | |
| Bartender | 5 | Head Bartender is the only senior |
| Server | 11 | Head Waiter and Senior Waiter are senior |
| Host | 3 | |

### Availability columns

- **`available` (hard constraint):** 1 = can work, 0 = cannot.
- **`unavailable_reason`:** Holiday, Regular day off, Study (students on weekday AM) or Personal (random 5%).
- **`preference` (soft constraint):** only filled when available. +1 = preferred block, 0 = neutral, −1 = would rather not work that weekday.

## Rules the optimiser must respect (Working Time Regulations 1998)

- **Weekly hours:** no more than 48 a week. Every contract's `max_weekly_hours` is 48 or less.
- **Daily rest:** at least 11 h between working days, so each person works at most **one block per day** and never PM followed by AM the next day (00:30 to 10:00 is only 9.5 h).
- **Weekly rest:** at least 1 full day off in every 7.
- **Breaks:** a 20-min break is required for shifts over 6 h. It's included as a 30-min unpaid break in the PM block.
- **Students:** capped at 20 h a week. This is the typical Student visa term-time limit and a team assumption.

## Built-in scenarios

| Scenario | Dates | What to expect |
|---|---|---|
| Head chef on holiday | S04 Marco, 19–25 Oct | Sous chef and senior CDP must cover every senior-chef block |
| Head waiter on holiday | S21 Ruth, 1–4 Oct | Covered by the other servers |
| Head bartender on holiday | S16 Chloe, 26–28 Oct | No senior on the bar |
| Waiter on holiday for half-term | S23 Francesca, 26–30 Oct | Same week as Chloe, the run-up to Halloween |

The Coverage_Check currently shows every block **OK** for available people against the minimums. Hours caps and the one-block-per-day rule may still make some weeks tight; that's for the optimiser to show. Illness isn't included because it isn't known in advance, so model it as a what-if.

## Wages and assumptions to verify

- **Wage basis:** base pay excludes tronc and tips. Under the Employment (Allocation of Tips) Act 2023 tips go to staff, so they aren't counted as labour cost.
- **Wage levels:** wages are **estimates** for central London, informed by job adverts: kitchen porter about £13.85, waiter £14–16, chef de partie about £15 and head chef about £24 per hour.
  - No reliable published average was found. Payscale and job adverts disagree, so cite these as estimates.
- **Legal floor:** every wage is at least £12.71, the National Living Wage for ages 21+ from 1 April 2026 (GOV.UK).
- **Age:** all staff are assumed to be 21 or over, so young-worker rules and lower minimum-wage bands don't apply.
- **Team assumptions:** the minimum staffing per block (1 manager, 1 senior chef, 2 chefs, 1 KP, 1 bartender, 2 servers) and students being unavailable on weekday mornings because of lectures.
