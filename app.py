"""Shiftr manager dashboard (Streamlit).

The manager uploads three Excel files (staff availability, bookings, last year's
history), then clicks Run to rebuild the master schedule. It also builds once
when the page first opens. The schedule is shown on the page and can be downloaded as Excel.

The interface only collects inputs and displays results. All calculation is in
shiftr_core.py, the same engine the notebook uses.

Run on the ManSci VM (from a notebook in the same folder):
    from mansci_tools import run_app
    run_app("app.py", kind="streamlit")
"""

import io
import sys
from datetime import datetime
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))   # find shiftr_core.py next to this file
import shiftr_core as sc  # noqa: E402

DATA = HERE / "data"
DEFAULT_FILES = {
    "staff": DATA / "Shiftr_Staff_Availability_Oct2026.xlsx",
    "bookings": DATA / "Shiftr_October_2026_Synthetic_Bookings.xlsx",
    "history": DATA / "Shiftr_October_2025_Historical_Demand.xlsx",
}
EXPECTED = {
    "staff": "sheets **Staff** (staff_id, first_name, job_title, role, seniority, contract, "
             "hourly_wage_gbp, max_weekly_hours, preferred_block) and **Availability** "
             "(staff_id, date, block, available, preference)",
    "bookings": "sheet **Bookings** (Booking ID, Reservation Date, Reservation Time, Meal Period, "
                "Covers (confirmed), Event Type)",
    "history": "sheet **Daily Demand** (Date, Day, Walk-in Lunch Customers, Walk-in Dinner Customers, "
               "Bar Walk-in Customers)",
}
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

st.set_page_config(page_title="Shiftr", layout="wide")


# ---------------------------------------------------------------- data loading

def file_bytes(upload, key, chosen):
    """Uploaded file if there is one, otherwise the file chosen from the data folder."""
    if upload is not None:
        return upload.getvalue(), f"{upload.name} (uploaded)"
    label = "built-in sample" if chosen == DEFAULT_FILES[key].name else "data folder"
    return (DATA / chosen).read_bytes(), f"{chosen} ({label})"


def data_folder_picker(label, key):
    """Dropdown of .xlsx files in data/, defaulting to the built-in sample."""
    files = sorted(p.name for p in DATA.glob("*.xlsx") if not p.name.startswith("~$"))
    default = DEFAULT_FILES[key].name
    return st.sidebar.selectbox(label, files, index=files.index(default) if default in files else 0,
                                key=f"pick_{key}")


@st.cache_data(show_spinner=False)
def read_inputs(staff_b, bookings_b, history_b):
    """Parse the three workbooks. Raises ValueError naming the file that is wrong."""
    def attempt(key, fn, b):
        try:
            return fn(io.BytesIO(b))
        except Exception as err:   # noqa: BLE001  any parsing problem is reported to the user
            raise ValueError(f"The {key} file could not be read ({err}). It needs {EXPECTED[key]}.")
    staff = attempt("staff", sc.load_staff, staff_b)
    availability = attempt("staff", sc.load_availability, staff_b)
    bookings = attempt("bookings", sc.load_bookings, bookings_b)
    walkins = attempt("history", sc.load_walkin_history, history_b)
    unknown = set(availability["staff_id"]) - set(staff["staff_id"])
    if unknown:
        raise ValueError(f"Availability lists staff not on the Staff sheet: {sorted(unknown)}")
    missing_days = walkins[walkins["walkin_lunch"].isna()].index.tolist()
    if missing_days:
        raise ValueError(f"The history file has no data for: {missing_days}")
    return staff, availability, bookings, walkins


@st.cache_data(show_spinner=False)
def build(staff_b, bookings_b, history_b, dates, absent, multiplier, per_server, per_chef):
    """Run the whole pipeline. Cached, so it only re-runs when an input actually changes."""
    staff, availability, bookings, walkins = read_inputs(staff_b, bookings_b, history_b)
    dates = list(dates)
    av = availability[availability["date"].isin(dates)].copy()
    av.loc[av["staff_id"].isin(absent), "available"] = 0

    demand = sc.build_demand(bookings, walkins, dates, walkin_multiplier=multiplier)
    requirements = sc.build_requirements(demand, per_server, per_chef)
    schedule, info = sc.build_schedule(staff, av, requirements, time_limit=45)
    coverage = sc.coverage_report(schedule, requirements)
    checks = sc.validate_schedule(schedule, staff, av, coverage)
    extra = sc.extra_cover_needed(coverage, "short_vs_bookings")
    grid = sc.rota_grid(schedule)

    excel = io.BytesIO()
    sc.export_excel(excel, schedule, grid, demand, coverage, checks, staff, info, extra)
    return dict(demand=demand, schedule=schedule, info=info, coverage=coverage, checks=checks,
                extra=extra, grid=grid, excel=excel.getvalue(),
                built_at=datetime.now().strftime("%H:%M:%S"))


def period_options(dates):
    weeks = {}
    for d in dates:
        weeks.setdefault(sc.week_of(d), []).append(d)
    options = {f"Week {v[0]:%a %d %b} - {v[-1]:%a %d %b}": tuple(v) for v in weeks.values()}
    options[f"Whole month (slow: about 2 minutes)"] = tuple(dates)
    return options


# ---------------------------------------------------------------- sidebar: uploads and settings

st.sidebar.title("Shiftr")
st.sidebar.caption("Manager dashboard. Prototype using synthetic data.")

st.sidebar.subheader("1. Upload this month's data")
up_staff = st.sidebar.file_uploader("Staff availability (this month)", type="xlsx", key="up_staff")
up_bookings = st.sidebar.file_uploader("Bookings (this month)", type="xlsx", key="up_bookings")
up_history = st.sidebar.file_uploader("Historic demand (same month last year)", type="xlsx",
                                      key="up_history")
st.sidebar.markdown("**...or choose a file from the `data` folder**")
st.sidebar.caption("If an upload above isn't received, put the file in the `data` folder with "
                   "JupyterLab's upload button instead, then pick it here.")
pick_staff = data_folder_picker("Staff availability file", "staff")
pick_bookings = data_folder_picker("Bookings file", "bookings")
pick_history = data_folder_picker("Historic demand file", "history")
st.sidebar.caption("An upload above takes priority over the dropdown. "
                   "After changing files, click **Run** at the bottom of this panel.")
received = st.sidebar.empty()   # filled in below once the files have been read

staff_b, staff_name = file_bytes(up_staff, "staff", pick_staff)
bookings_b, bookings_name = file_bytes(up_bookings, "bookings", pick_bookings)
history_b, history_name = file_bytes(up_history, "history", pick_history)

st.title("Shiftr: the right people, in the right place, at the right time")

try:
    staff, availability, bookings, walkins = read_inputs(staff_b, bookings_b, history_b)
except ValueError as err:
    st.error(str(err))
    st.stop()

received.caption(
    f"Files in use:  \n"
    f"• staff: {staff_name}, {len(staff)} staff  \n"
    f"• bookings: {bookings_name}, {len(bookings)} bookings  \n"
    f"• history: {history_name}, {int(walkins['days_observed'].sum())} days")

all_dates = sorted(availability["date"].unique())
booked_dates = set(bookings["date"])
if not booked_dates & set(all_dates):
    st.warning("None of the bookings fall in the dates covered by the staff availability file. "
               "Check both files are for the same month.")

st.sidebar.subheader("2. Choose the period")
periods = period_options(all_dates)
period = st.sidebar.selectbox("Period to schedule", list(periods), index=min(1, len(periods) - 1))

st.sidebar.subheader("3. What-if (optional)")
multiplier = st.sidebar.slider("Walk-in demand vs last year", 0.5, 2.0, 1.0, 0.1,
                               help="1.0 = same as last year. 1.3 = 30% more walk-ins.")
names = dict(zip(staff["staff_id"], staff["first_name"] + " (" + staff["job_title"] + ")"))
absent = st.sidebar.multiselect("Staff off sick for the whole period", list(names), format_func=names.get)
with st.sidebar.expander("Productivity assumptions"):
    per_server = st.slider("Diners per server", 6, 20, 12)
    per_chef = st.slider("Diners per line chef", 10, 30, 20)

# ---------------------------------------------------------------- build (on Run)

params = (staff_b, bookings_b, history_b, periods[period], tuple(sorted(absent)),
          multiplier, per_server, per_chef)
run = st.sidebar.button("Run", type="primary", use_container_width=True)

if run or "result" not in st.session_state:   # also builds once when the page first opens
    with st.spinner("Building the master schedule... (a week takes up to a minute)"):
        try:
            st.session_state["result"] = build(*params)
        except RuntimeError as err:
            st.error(f"No rota could be built: {err}")
            st.stop()
    st.session_state["params"] = params
    st.session_state["inputs"] = dict(staff=staff_name, n_staff=len(staff), period=period)
    st.session_state["ran_at"] = datetime.now().strftime("%H:%M:%S")
    if run:
        st.toast(f"Schedule updated at {st.session_state['ran_at']} using {staff_name}")

r = st.session_state["result"]
if st.session_state["params"] != params:
    st.info("Files or settings have changed since the last run. Click **Run** in the left panel "
            "to update the schedule.")

schedule, coverage, checks, extra = r["schedule"], r["coverage"], r["checks"], r["extra"]

with st.expander("Data in use", expanded=False):
    st.markdown(
        f"- **Staff availability:** {st.session_state['inputs']['staff']}: "
        f"{st.session_state['inputs']['n_staff']} staff, "
        f"{all_dates[0]:%d %b} to {all_dates[-1]:%d %b %Y}\n"
        f"- **Bookings:** {bookings_name}: {len(bookings)} bookings, {bookings['covers'].sum()} covers\n"
        f"- **Historic demand:** {history_name}: {int(walkins['days_observed'].sum())} days of history")
    t1, t2, t3 = st.columns(3)
    for col, key, label in ((t1, "staff", "staff availability"), (t2, "bookings", "bookings"),
                            (t3, "history", "historic demand")):
        col.download_button(f"Template: {label}", DEFAULT_FILES[key].read_bytes(),
                            file_name=DEFAULT_FILES[key].name, mime=XLSX, key=f"tpl_{key}")
    st.caption("Download a template, edit it in Excel (keep the sheet and column names), then upload it.")

st.caption(f"Schedule for **{st.session_state['inputs']['period']}**, last run at {st.session_state['ran_at']}. Solver: {r['info']['status']}")

passed = (checks["result"] == "PASS").sum()
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Labour cost", f"£{schedule['shift_cost_gbp'].sum():,.0f}")
c2.metric("Paid hours", f"{schedule['paid_hours'].sum():,.0f}")
c3.metric("Shifts", len(schedule))
c4.metric("Demand covered", f"{sc.coverage_score(coverage):.1%}")
c5.metric("Checks passed", f"{passed} / {len(checks)}")

d1, d2 = st.columns([3, 1])
if len(extra):
    d1.warning(f"Confirmed bookings need **{extra['staff_hours'].sum():.1f} extra staff-hours** "
               "that the current team cannot cover. See the *Cover gaps* tab.")
else:
    d1.success("Every confirmed booking is fully staffed.")
d2.download_button("Download master schedule (Excel)", r["excel"], type="primary",
                   file_name="Shiftr_Master_Schedule.xlsx", mime=XLSX, use_container_width=True)

tab_sched, tab_grid, tab_why, tab_gaps, tab_checks = st.tabs(
    ["Master schedule", "Rota grid", "Why this many staff?", "Cover gaps", "Checks"])

with tab_sched:
    f1, f2, f3 = st.columns(3)
    days = sorted(schedule["date"].unique())
    pick_day = f1.selectbox("Day", ["All"] + days,
                            format_func=lambda d: d if d == "All" else d.strftime("%a %d %b"))
    pick_area = f2.selectbox("Area", ["All"] + sorted(schedule["area"].unique()))
    pick_person = f3.selectbox("Employee", ["All"] + sorted(schedule["employee"].unique()))
    view = schedule
    if pick_day != "All":
        view = view[view["date"] == pick_day]
    if pick_area != "All":
        view = view[view["area"] == pick_area]
    if pick_person != "All":
        view = view[view["employee"] == pick_person]
    st.dataframe(
        view[["date", "day", "employee", "job_title", "area", "placement", "start", "end",
              "break", "paid_hours", "shift_cost_gbp", "preference"]],
        hide_index=True, use_container_width=True)

with tab_grid:
    st.dataframe(r["grid"], hide_index=True, use_container_width=True)

with tab_why:
    st.write("Pick a day and station to see how bookings and forecast walk-ins drive the staff needed, "
             "and how many people the rota puts there (breaks are taken off the floor).")
    w1, w2 = st.columns(2)
    day = w1.selectbox("Day ", days, format_func=lambda d: d.strftime("%a %d %b"))
    station = w2.selectbox("Station", list(sc.STATIONS), index=list(sc.STATIONS).index("Dining Room"))

    d = r["demand"][r["demand"]["date"] == day]
    fig = go.Figure()
    fig.add_bar(x=d["time"], y=d["booked_food"], name="Booked diners")
    fig.add_bar(x=d["time"], y=d["walkin_food"], name="Forecast walk-in diners")
    fig.add_scatter(x=d["time"], y=d["bar"], name="Bar guests", mode="lines+markers")
    fig.add_hline(y=sc.SEATS, line_dash="dash", annotation_text=f"{sc.SEATS} seats")
    fig.update_layout(barmode="stack", height=320, margin=dict(t=30, b=10),
                      title="Guests in the building", yaxis_title="people")
    st.plotly_chart(fig, use_container_width=True)

    c = coverage[(coverage["date"] == day) & (coverage["station"] == station)]
    fig2 = go.Figure()
    fig2.add_scatter(x=c["time"], y=c["req_min"], name="Needed for bookings", line_shape="hv")
    fig2.add_scatter(x=c["time"], y=c["req_full"], name="Needed incl. walk-ins", line_shape="hv")
    fig2.add_bar(x=c["time"], y=c["scheduled"], name="Scheduled on the floor", opacity=0.5)
    fig2.update_layout(height=320, margin=dict(t=30, b=10), title=f"{station}: staff needed vs scheduled",
                       yaxis_title="staff")
    st.plotly_chart(fig2, use_container_width=True)
    if d["overbooked"].any():
        st.warning("On this day, bookings alone exceed the seats at some times. "
                   "Staffing is planned for at most 50 diners; the bookings need reviewing.")

with tab_gaps:
    st.write("Times when the current team cannot staff **confirmed bookings**, after every rule is applied. "
             "These need agency cover, overtime by agreement, or a change to the bookings.")
    st.dataframe(extra, hide_index=True, use_container_width=True)

with tab_checks:
    st.write("Each rule is re-checked directly from the finished schedule, independently of the optimiser.")
    st.dataframe(checks, hide_index=True, use_container_width=True)
