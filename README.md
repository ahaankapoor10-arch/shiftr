# Shiftr: staff scheduling prototype (MSIN0023, Team How2Shift)

> **Synthetic data only.** The restaurant, staff, bookings and history are invented for coursework.

Shiftr builds the cheapest staff rota for a 50-seat Italian restaurant with a 10-stool bar in central London. Its rules:
- **Confirmed bookings** set the minimum staffing, which must always be met.
- **Last year's walk-ins** add forecast extra demand on top.
- **The rota respects:** staff availability, contract hours, 11 h rest between shifts, a day off each week, and a 30-minute break on shifts over 6 h.

## Files
| File | What it is |
|---|---|
| `app.py` | Streamlit manager dashboard: upload the 3 Excel files, click **Run**, view and download the master schedule |
| `shiftr_core.py` | Scheduling engine (demand forecast, staffing requirements, PuLP optimiser, checks, Excel export) |
| `Shiftr_Master_Schedule.ipynb` | Notebook that walks through the same pipeline step by step |
| `data/*.xlsx` | Built-in sample inputs. `..._v2_new_hires.xlsx` adds 6 hires that close the cover gaps |
| `scripts/` | Generators for the synthetic staff data |

## Run it
- **Hosted:** use the Streamlit Community Cloud link shared by the team.
- **Local or ManSci VM:** `streamlit run app.py`, or `run_app("app.py", kind="streamlit")` on the VM.

## Adding new data
Download a template from **Data in use** in the app. Edit it in Excel, keeping the sheet and column names, then upload it in the sidebar and click **Run**. Uploads last only for your browser session. To change a built-in sample for everyone, commit a new file to `data/`.
