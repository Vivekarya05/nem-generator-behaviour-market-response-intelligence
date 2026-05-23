"""Generate the Project 3 notebook scaffold and portfolio assets.

The notebooks are intentionally created as executable analyst workbooks:
they contain SQL extraction logic, feature engineering code, Plotly outputs,
and professional NEM market interpretation prompts.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def md(source: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": source.strip().splitlines(True),
    }


def code(source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source.strip().splitlines(True),
    }


def notebook(cells: list[dict]) -> dict:
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "pygments_lexer": "ipython3"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


SETUP = """
from pathlib import Path
import os
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine, text

PROJECT_ROOT = Path.cwd()
if PROJECT_ROOT.name == "notebooks":
    PROJECT_ROOT = PROJECT_ROOT.parent

OUTPUT_CSV = PROJECT_ROOT / "outputs" / "csv"
OUTPUT_CHARTS = PROJECT_ROOT / "outputs" / "charts"
OUTPUT_REPORTS = PROJECT_ROOT / "outputs" / "reports"
for path in [OUTPUT_CSV, OUTPUT_CHARTS, OUTPUT_REPORTS]:
    path.mkdir(parents=True, exist_ok=True)

START_DATE = "2026-02-01"
END_DATE = "2026-03-01"
REGIONS = ["NSW1", "VIC1"]

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://USER:PASSWORD@HOST:5432/DBNAME")

def get_engine():
    if "USER:PASSWORD@HOST" in DATABASE_URL:
        raise ValueError("Set DATABASE_URL before running database extraction cells.")
    return create_engine(DATABASE_URL)

def save_csv(df, name):
    path = OUTPUT_CSV / name
    df.to_csv(path, index=False)
    print(f"saved {path} rows={len(df):,}")
    return path

def save_chart(fig, name):
    path = OUTPUT_CHARTS / name
    fig.write_html(path, include_plotlyjs="cdn")
    print(f"saved {path}")
    return path
"""


NOTEBOOKS: dict[str, list[dict]] = {
    "01_etl_download_load_validation.ipynb": [
        md("""
# 01 ETL Download, Load, and Validation

## Objective
Confirm that the existing ETL pipeline has downloaded, parsed, cleaned, de-duplicated, validated, and loaded the required NEM dispatch tables into PostgreSQL for 2026-02-01 to 2026-03-01.

## Why this matters in the NEM
Generator behaviour analysis is only useful if dispatch interval records are complete, timestamp-aligned, and free from duplicate C/I/D parsing artefacts. Small ETL defects can create false ramping signals or misleading supply stress periods.

## Required data
- `raw.dispatch_price`
- `raw.dispatch_regionsum`
- `raw.dispatch_unit_scada`

## Outputs
- ETL validation checklist
- table row counts
- SCADA schema inspection
- data coverage checks supporting all downstream notebooks
"""),
        code(SETUP),
        md("""
## Existing ETL pipeline hand-off

This project does not use NEMOSIS. It assumes your existing NEMWeb ETL pipeline performs:

- public NEMWeb download
- C/I/D row parsing
- field standardisation
- duplicate removal
- validation
- PostgreSQL load into `raw` schema

Run your ETL pipeline before the validation cells below. Keep the pipeline source separate if it is shared across Projects 1-3.
"""),
        code("""
engine = get_engine()

tables = ["raw.dispatch_price", "raw.dispatch_regionsum", "raw.dispatch_unit_scada"]
for table in tables:
    query = text(f'''
        select count(*) as row_count,
               min(settlementdate) as min_settlementdate,
               max(settlementdate) as max_settlementdate
        from {table}
        where settlementdate >= :start_date
          and settlementdate < :end_date
    ''')
    display(pd.read_sql(query, engine, params={"start_date": START_DATE, "end_date": END_DATE}).assign(table=table))
"""),
        md("""
## Mandatory SCADA schema inspection

Before proceeding, inspect the actual schema of `raw.dispatch_unit_scada`. This is deliberately early because MMS table naming and column casing often varies across local ETL implementations.
"""),
        code("""
engine = get_engine()

schema_sql = text('''
    select column_name, data_type
    from information_schema.columns
    where table_schema = 'raw'
      and table_name = 'dispatch_unit_scada'
    order by ordinal_position
''')
scada_schema = pd.read_sql(schema_sql, engine)
print("SCADA column names:")
print(scada_schema["column_name"].tolist())
display(scada_schema)

row_count = pd.read_sql(text("select count(*) as row_count from raw.dispatch_unit_scada"), engine)
print("SCADA row count:")
display(row_count)

null_sql = text('''
    select
        count(*) filter (where settlementdate is null) as settlementdate_nulls,
        count(*) filter (where duid is null) as duid_nulls,
        count(*) filter (where scadavalue is null) as scadavalue_nulls,
        count(*) filter (where intervention is null) as intervention_nulls,
        count(*) filter (where lastchanged is null) as lastchanged_nulls
    from raw.dispatch_unit_scada
''')
print("SCADA null counts:")
display(pd.read_sql(null_sql, engine))

example_sql = text('''
    select *
    from raw.dispatch_unit_scada
    where settlementdate >= :start_date
      and settlementdate < :end_date
    order by settlementdate, duid
    limit 10
''')
print("SCADA example rows:")
display(pd.read_sql(example_sql, engine, params={"start_date": START_DATE, "end_date": END_DATE}))
"""),
        code("""
coverage_sql = text('''
with expected as (
    select generate_series(
        cast(:start_date as timestamp),
        cast(:end_date as timestamp) - interval '5 minutes',
        interval '5 minutes'
    ) as settlementdate
),
price_coverage as (
    select settlementdate, regionid
    from raw.dispatch_price
    where settlementdate >= :start_date
      and settlementdate < :end_date
      and regionid = any(:regions)
      and coalesce(intervention, 0) = 0
),
regionsum_coverage as (
    select settlementdate, regionid
    from raw.dispatch_regionsum
    where settlementdate >= :start_date
      and settlementdate < :end_date
      and regionid = any(:regions)
      and coalesce(intervention, 0) = 0
)
select
    e.settlementdate,
    r.regionid,
    case when p.settlementdate is null then 1 else 0 end as missing_price,
    case when rs.settlementdate is null then 1 else 0 end as missing_regionsum
from expected e
cross join unnest(:regions) as r(regionid)
left join price_coverage p on p.settlementdate = e.settlementdate and p.regionid = r.regionid
left join regionsum_coverage rs on rs.settlementdate = e.settlementdate and rs.regionid = r.regionid
where p.settlementdate is null or rs.settlementdate is null
order by e.settlementdate, r.regionid
''')

missing_intervals = pd.read_sql(
    coverage_sql,
    engine,
    params={"start_date": START_DATE, "end_date": END_DATE, "regions": REGIONS},
)
display(missing_intervals.head(50))
print(f"missing coverage rows: {len(missing_intervals):,}")
"""),
    ],
    "02_data_extraction_cleaning.ipynb": [
        md("""
# 02 Data Extraction and Cleaning

## Objective
Extract price, regional supply/demand, and unit SCADA from PostgreSQL, then clean and align all datasets at dispatch interval granularity.

## Why this matters in the NEM
Generator response analysis depends on a clean dispatch interval spine. Price, demand, available generation, and unit output must describe the same five-minute market interval.

## Features created
- cleaned price table
- cleaned regional operations table
- cleaned SCADA unit output table
- interval-aligned market table

## Outputs
- `clean_dispatch_price.csv`
- `clean_dispatch_regionsum.csv`
- `clean_dispatch_unit_scada.csv`
- `market_interval_base.csv`
"""),
        code(SETUP),
        code("""
engine = get_engine()

price_sql = text('''
    select settlementdate, regionid, rrp, intervention, lastchanged
    from raw.dispatch_price
    where settlementdate >= :start_date
      and settlementdate < :end_date
      and regionid = any(:regions)
''')

regionsum_sql = text('''
    select settlementdate, regionid, totaldemand, availablegeneration, netinterchange, intervention, lastchanged
    from raw.dispatch_regionsum
    where settlementdate >= :start_date
      and settlementdate < :end_date
      and regionid = any(:regions)
''')

scada_sql = text('''
    select settlementdate, duid, scadavalue, intervention, lastchanged
    from raw.dispatch_unit_scada
    where settlementdate >= :start_date
      and settlementdate < :end_date
''')

params = {"start_date": START_DATE, "end_date": END_DATE, "regions": REGIONS}
price = pd.read_sql(price_sql, engine, params=params)
regionsum = pd.read_sql(regionsum_sql, engine, params=params)
scada = pd.read_sql(scada_sql, engine, params=params)

print(price.shape, regionsum.shape, scada.shape)
display(price.head())
display(regionsum.head())
display(scada.head())
"""),
        code("""
def clean_dispatch_price(df):
    out = df.copy()
    out["settlementdate"] = pd.to_datetime(out["settlementdate"])
    out["lastchanged"] = pd.to_datetime(out["lastchanged"], errors="coerce")
    out["regionid"] = out["regionid"].astype(str).str.upper().str.strip()
    out["rrp"] = pd.to_numeric(out["rrp"], errors="coerce")
    out["intervention"] = pd.to_numeric(out["intervention"], errors="coerce").fillna(0).astype(int)
    out = out[out["intervention"].eq(0)]
    out = out[out["regionid"].isin(REGIONS)]
    out = out.sort_values(["settlementdate", "regionid", "lastchanged"])
    out = out.drop_duplicates(["settlementdate", "regionid"], keep="last")
    return out.reset_index(drop=True)

def clean_regionsum(df):
    out = df.copy()
    out["settlementdate"] = pd.to_datetime(out["settlementdate"])
    out["lastchanged"] = pd.to_datetime(out["lastchanged"], errors="coerce")
    out["regionid"] = out["regionid"].astype(str).str.upper().str.strip()
    for col in ["totaldemand", "availablegeneration", "netinterchange"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out["intervention"] = pd.to_numeric(out["intervention"], errors="coerce").fillna(0).astype(int)
    out = out[out["intervention"].eq(0)]
    out = out[out["regionid"].isin(REGIONS)]
    out = out.sort_values(["settlementdate", "regionid", "lastchanged"])
    out = out.drop_duplicates(["settlementdate", "regionid"], keep="last")
    return out.reset_index(drop=True)

def clean_scada(df):
    out = df.copy()
    out["settlementdate"] = pd.to_datetime(out["settlementdate"])
    out["lastchanged"] = pd.to_datetime(out["lastchanged"], errors="coerce")
    out["duid"] = out["duid"].astype(str).str.upper().str.strip()
    out["scadavalue"] = pd.to_numeric(out["scadavalue"], errors="coerce")
    out["intervention"] = pd.to_numeric(out["intervention"], errors="coerce").fillna(0).astype(int)
    out = out[out["intervention"].eq(0)]
    out = out.dropna(subset=["settlementdate", "duid"])
    out["scadavalue"] = out["scadavalue"].clip(lower=0)
    out = out.sort_values(["settlementdate", "duid", "lastchanged"])
    out = out.drop_duplicates(["settlementdate", "duid"], keep="last")
    return out.reset_index(drop=True)

price_clean = clean_dispatch_price(price)
regionsum_clean = clean_regionsum(regionsum)
scada_clean = clean_scada(scada)

market_base = price_clean.merge(
    regionsum_clean[["settlementdate", "regionid", "totaldemand", "availablegeneration", "netinterchange"]],
    on=["settlementdate", "regionid"],
    how="inner",
)

display(market_base.head())
print(price_clean.shape, regionsum_clean.shape, scada_clean.shape, market_base.shape)
"""),
        code("""
save_csv(price_clean, "clean_dispatch_price.csv")
save_csv(regionsum_clean, "clean_dispatch_regionsum.csv")
save_csv(scada_clean, "clean_dispatch_unit_scada.csv")
save_csv(market_base, "market_interval_base.csv")
"""),
    ],
    "03_generator_feature_engineering.ipynb": [
        md("""
# 03 Generator Feature Engineering

## Objective
Convert cleaned market and SCADA data into generator behaviour features that can explain supply-side market response.

## Why this matters in the NEM
Dispatch outcomes are shaped by whether available supply is actually producing, whether units are ramping, and whether aggregate output is responding to price and demand signals.

## Features created
- `total_generation_output`
- `generation_change`
- `generation_ramp_rate`
- `rolling_generation_avg`
- `generator_utilisation_proxy`
- `supply_margin`
- price and volatility flags
- time features

## Outputs
- `market_generation_features.csv`
- `generator_interval_features.csv`
"""),
        code(SETUP),
        code("""
market_base = pd.read_csv(OUTPUT_CSV / "market_interval_base.csv", parse_dates=["settlementdate"])
scada_clean = pd.read_csv(OUTPUT_CSV / "clean_dispatch_unit_scada.csv", parse_dates=["settlementdate"])

market_base = market_base.sort_values(["regionid", "settlementdate"])
scada_clean = scada_clean.sort_values(["duid", "settlementdate"])
"""),
        code("""
generator_features = scada_clean.copy()
generator_features["generation_change"] = generator_features.groupby("duid")["scadavalue"].diff()
generator_features["generation_ramp_rate"] = generator_features["generation_change"] / (5 / 60)
generator_features["rolling_generation_avg"] = (
    generator_features.groupby("duid")["scadavalue"]
    .transform(lambda s: s.rolling(12, min_periods=1).mean())
)

duid_capacity_proxy = generator_features.groupby("duid")["scadavalue"].transform(lambda s: s.quantile(0.99))
generator_features["generator_utilisation_proxy"] = np.where(
    duid_capacity_proxy.gt(0),
    generator_features["scadavalue"] / duid_capacity_proxy,
    np.nan,
)
generator_features["generator_utilisation_proxy"] = generator_features["generator_utilisation_proxy"].clip(0, 1.5)

aggregate_generation = (
    generator_features.groupby("settlementdate", as_index=False)
    .agg(
        total_generation_output=("scadavalue", "sum"),
        active_generators=("duid", "nunique"),
        aggregate_generation_change=("generation_change", "sum"),
        aggregate_abs_ramp=("generation_change", lambda x: x.abs().sum()),
    )
)

market_features = market_base.merge(aggregate_generation, on="settlementdate", how="left")
market_features = market_features.sort_values(["regionid", "settlementdate"])

market_features["supply_margin"] = market_features["availablegeneration"] - market_features["totaldemand"]
market_features["supply_margin_pct"] = market_features["supply_margin"] / market_features["totaldemand"].replace(0, np.nan)
market_features["price_spike_flag"] = market_features["rrp"].ge(300)
market_features["negative_price_flag"] = market_features["rrp"].lt(0)
market_features["rrp_abs_change"] = market_features.groupby("regionid")["rrp"].diff().abs()
market_features["volatility_flag"] = market_features["rrp_abs_change"].ge(150)
market_features["supply_stress_flag"] = market_features["supply_margin_pct"].lt(0.15)
market_features["hour"] = market_features["settlementdate"].dt.hour
market_features["weekday"] = market_features["settlementdate"].dt.day_name()
market_features["is_weekend"] = market_features["settlementdate"].dt.weekday.ge(5)

display(market_features.head())
display(generator_features.head())
"""),
        code("""
save_csv(market_features, "market_generation_features.csv")
save_csv(generator_features, "generator_interval_features.csv")
"""),
    ],
    "04_generation_mix_analysis.ipynb": [
        md("""
# 04 Generation Mix Analysis

## Objective
Analyse aggregate generation behaviour across NSW1 and VIC1 market conditions.

## Why this matters in the NEM
Generation mix and aggregate output shape regional price outcomes, especially when demand rises, available generation tightens, or prices move below zero.

## Outputs
- `generation_mix_summary.csv`
- Plotly charts for generation and price context
"""),
        code(SETUP),
        code("""
market = pd.read_csv(OUTPUT_CSV / "market_generation_features.csv", parse_dates=["settlementdate"])

generation_mix_summary = (
    market.groupby("regionid", as_index=False)
    .agg(
        intervals=("settlementdate", "count"),
        avg_rrp=("rrp", "mean"),
        avg_totaldemand=("totaldemand", "mean"),
        avg_availablegeneration=("availablegeneration", "mean"),
        avg_total_generation_output=("total_generation_output", "mean"),
        spike_intervals=("price_spike_flag", "sum"),
        negative_price_intervals=("negative_price_flag", "sum"),
        stress_intervals=("supply_stress_flag", "sum"),
    )
)
generation_mix_summary["spike_share"] = generation_mix_summary["spike_intervals"] / generation_mix_summary["intervals"]
generation_mix_summary["negative_price_share"] = generation_mix_summary["negative_price_intervals"] / generation_mix_summary["intervals"]
display(generation_mix_summary)
save_csv(generation_mix_summary, "generation_mix_summary.csv")
"""),
        code("""
fig = px.line(
    market,
    x="settlementdate",
    y=["rrp", "total_generation_output"],
    color="regionid",
    facet_row="regionid",
    title="RRP and Aggregate Generation Output"
)
fig.update_layout(height=750)
save_chart(fig, "rrp_vs_generation.html")
fig.show()
"""),
        code("""
event_mix = (
    market.assign(
        market_condition=np.select(
            [market["price_spike_flag"], market["negative_price_flag"], market["volatility_flag"]],
            ["Price spike", "Negative price", "High volatility"],
            default="Normal"
        )
    )
    .groupby(["regionid", "market_condition"], as_index=False)
    .agg(
        avg_rrp=("rrp", "mean"),
        avg_demand=("totaldemand", "mean"),
        avg_available_generation=("availablegeneration", "mean"),
        avg_generation_output=("total_generation_output", "mean"),
        avg_supply_margin=("supply_margin", "mean"),
        intervals=("settlementdate", "count"),
    )
)
display(event_mix)
save_csv(event_mix, "generation_mix_by_market_condition.csv")
"""),
    ],
    "05_generator_ramping_analysis.ipynb": [
        md("""
# 05 Generator Ramping Analysis

## Objective
Identify rapid generator output changes and assess which units respond fastest during price spikes and evening demand ramps.

## Why this matters in the NEM
Ramping capability is a key supply-side source of market flexibility. During scarcity or volatility, fast response can reduce price risk, while insufficient ramping can amplify it.

## Outputs
- `generator_ramping_summary.csv`
- ramping charts
"""),
        code(SETUP),
        code("""
market = pd.read_csv(OUTPUT_CSV / "market_generation_features.csv", parse_dates=["settlementdate"])
gen = pd.read_csv(OUTPUT_CSV / "generator_interval_features.csv", parse_dates=["settlementdate"])

event_context = market[["settlementdate", "price_spike_flag", "negative_price_flag", "volatility_flag", "hour"]].drop_duplicates("settlementdate")
gen_events = gen.merge(event_context, on="settlementdate", how="left")
gen_events["abs_generation_change"] = gen_events["generation_change"].abs()
gen_events["rapid_ramp_flag"] = gen_events["abs_generation_change"].ge(gen_events.groupby("duid")["abs_generation_change"].transform(lambda s: s.quantile(0.95)))
gen_events["evening_ramp_window"] = gen_events["hour"].between(16, 20)

ramping_summary = (
    gen_events.groupby("duid", as_index=False)
    .agg(
        avg_output=("scadavalue", "mean"),
        max_output=("scadavalue", "max"),
        avg_abs_ramp=("abs_generation_change", "mean"),
        p95_abs_ramp=("abs_generation_change", lambda s: s.quantile(0.95)),
        max_abs_ramp=("abs_generation_change", "max"),
        rapid_ramp_intervals=("rapid_ramp_flag", "sum"),
        spike_response_avg_ramp=("generation_change", lambda s: s[gen_events.loc[s.index, "price_spike_flag"].fillna(False)].mean()),
        evening_ramp_avg=("generation_change", lambda s: s[gen_events.loc[s.index, "evening_ramp_window"].fillna(False)].mean()),
    )
    .sort_values("p95_abs_ramp", ascending=False)
)
display(ramping_summary.head(25))
save_csv(ramping_summary, "generator_ramping_summary.csv")
"""),
        code("""
top_duids = ramping_summary.head(12)["duid"].tolist()
plot_df = gen_events[gen_events["duid"].isin(top_duids)]
fig = px.line(
    plot_df,
    x="settlementdate",
    y="generation_change",
    color="duid",
    title="Generator Dispatch Interval Output Changes - Top Ramping Units"
)
save_chart(fig, "generator_ramping.html")
fig.show()
"""),
    ],
    "06_supply_adequacy_analysis.ipynb": [
        md("""
# 06 Supply Adequacy Analysis

## Objective
Assess whether available generation is sufficient relative to operational demand and identify tight supply periods.

## Why this matters in the NEM
Supply margin is one of the clearest operational indicators of scarcity risk. Tight margins can increase exposure to price spikes, volatility, and intervention risk.

## Outputs
- `supply_adequacy_summary.csv`
- supply margin charts
"""),
        code(SETUP),
        code("""
market = pd.read_csv(OUTPUT_CSV / "market_generation_features.csv", parse_dates=["settlementdate"])

supply_adequacy_summary = (
    market.groupby("regionid", as_index=False)
    .agg(
        min_supply_margin=("supply_margin", "min"),
        avg_supply_margin=("supply_margin", "mean"),
        p10_supply_margin=("supply_margin", lambda s: s.quantile(0.10)),
        avg_supply_margin_pct=("supply_margin_pct", "mean"),
        stress_intervals=("supply_stress_flag", "sum"),
        spike_intervals=("price_spike_flag", "sum"),
        avg_rrp_during_stress=("rrp", lambda s: s[market.loc[s.index, "supply_stress_flag"]].mean()),
    )
)
display(supply_adequacy_summary)
save_csv(supply_adequacy_summary, "supply_adequacy_summary.csv")
"""),
        code("""
fig = px.line(
    market,
    x="settlementdate",
    y=["totaldemand", "availablegeneration", "supply_margin"],
    facet_row="regionid",
    color="regionid",
    title="Available Generation, Demand, and Supply Margin"
)
fig.update_layout(height=800)
save_chart(fig, "available_generation_vs_demand_supply_margin.html")
fig.show()
"""),
    ],
    "07_generator_response_price_events.ipynb": [
        md("""
# 07 Generator Response to Price Events

## Objective
Explain what generators were doing during price spikes, negative prices, volatility periods, and high demand intervals.

## Why this matters in the NEM
Price events are not just price outcomes. They reflect the interaction of dispatchable supply, renewable availability, ramping capability, demand shape, and interconnector flows.

## Outputs
- `generator_response_price_events.csv`
- event response charts
"""),
        code(SETUP),
        code("""
market = pd.read_csv(OUTPUT_CSV / "market_generation_features.csv", parse_dates=["settlementdate"])
gen = pd.read_csv(OUTPUT_CSV / "generator_interval_features.csv", parse_dates=["settlementdate"])

high_demand_threshold = market.groupby("regionid")["totaldemand"].transform(lambda s: s.quantile(0.90))
market["high_demand_flag"] = market["totaldemand"].ge(high_demand_threshold)

event_intervals = market[
    market[["price_spike_flag", "negative_price_flag", "volatility_flag", "high_demand_flag"]].any(axis=1)
][["settlementdate", "regionid", "rrp", "totaldemand", "availablegeneration", "supply_margin", "price_spike_flag", "negative_price_flag", "volatility_flag", "high_demand_flag"]]

gen_response = gen.merge(event_intervals.drop_duplicates("settlementdate"), on="settlementdate", how="inner")

generator_response_price_events = (
    gen_response.groupby(["duid"], as_index=False)
    .agg(
        event_intervals=("settlementdate", "nunique"),
        avg_output_during_events=("scadavalue", "mean"),
        avg_change_during_events=("generation_change", "mean"),
        avg_abs_ramp_during_events=("generation_change", lambda s: s.abs().mean()),
        spike_event_output=("scadavalue", lambda s: s[gen_response.loc[s.index, "price_spike_flag"]].mean()),
        negative_price_output=("scadavalue", lambda s: s[gen_response.loc[s.index, "negative_price_flag"]].mean()),
        volatility_output=("scadavalue", lambda s: s[gen_response.loc[s.index, "volatility_flag"]].mean()),
    )
    .sort_values("avg_abs_ramp_during_events", ascending=False)
)
display(generator_response_price_events.head(25))
save_csv(generator_response_price_events, "generator_response_price_events.csv")
"""),
        code("""
top = generator_response_price_events.head(15)["duid"]
plot_df = gen_response[gen_response["duid"].isin(top)]
fig = px.scatter(
    plot_df,
    x="rrp",
    y="scadavalue",
    color="duid",
    facet_col="regionid",
    title="Generator Output During Market Events"
)
save_chart(fig, "generation_during_events.html")
fig.show()
"""),
    ],
    "08_event_classification.ipynb": [
        md("""
# 08 Event Classification

## Objective
Classify market events into interpretable supply-side drivers.

## Event classes
1. Supply Tightness Event
2. Generator Ramping Event
3. High Volatility Event
4. Oversupply Event
5. Renewable Dominance Event
6. Mixed Driver Event

## Why this matters in the NEM
Classification converts dispatch data into market narrative. Traders and analysts need to know whether an event was driven by scarcity, ramping, volatility, oversupply, or mixed conditions.

## Outputs
- `generator_event_classification.csv`
"""),
        code(SETUP),
        code("""
market = pd.read_csv(OUTPUT_CSV / "market_generation_features.csv", parse_dates=["settlementdate"])

market["high_ramp_flag"] = market["aggregate_abs_ramp"].ge(market["aggregate_abs_ramp"].quantile(0.90))
market["oversupply_flag"] = market["negative_price_flag"] & market["supply_margin_pct"].ge(0.25)
market["renewable_dominance_proxy_flag"] = market["negative_price_flag"] & market["total_generation_output"].ge(market["total_generation_output"].quantile(0.75))

def classify_event(row):
    drivers = []
    if row["supply_stress_flag"] or (row["price_spike_flag"] and row["supply_margin_pct"] < 0.20):
        drivers.append("Supply Tightness Event")
    if row["high_ramp_flag"]:
        drivers.append("Generator Ramping Event")
    if row["volatility_flag"]:
        drivers.append("High Volatility Event")
    if row["oversupply_flag"]:
        drivers.append("Oversupply Event")
    if row["renewable_dominance_proxy_flag"]:
        drivers.append("Renewable Dominance Event")
    if len(drivers) > 1:
        return "Mixed Driver Event"
    if len(drivers) == 1:
        return drivers[0]
    return "Normal Dispatch Interval"

def explain_event(row):
    if row["event_class"] == "Supply Tightness Event":
        return "Supply margin is tight relative to regional demand, increasing scarcity pricing risk."
    if row["event_class"] == "Generator Ramping Event":
        return "Aggregate generator movement is elevated, indicating active supply-side response."
    if row["event_class"] == "High Volatility Event":
        return "Regional price movement is abrupt, suggesting unstable market conditions."
    if row["event_class"] == "Oversupply Event":
        return "Negative prices and healthy supply margin indicate surplus generation pressure."
    if row["event_class"] == "Renewable Dominance Event":
        return "Negative price conditions coincide with elevated aggregate output, a proxy for renewable-led oversupply."
    if row["event_class"] == "Mixed Driver Event":
        return "Multiple supply-side and price signals are active in the same interval."
    return "No material event signal detected."

events = market.copy()
events["event_class"] = events.apply(classify_event, axis=1)
events["event_explanation"] = events.apply(explain_event, axis=1)

event_cols = [
    "settlementdate", "regionid", "rrp", "totaldemand", "availablegeneration",
    "total_generation_output", "supply_margin", "supply_margin_pct",
    "price_spike_flag", "negative_price_flag", "volatility_flag",
    "supply_stress_flag", "high_ramp_flag", "event_class", "event_explanation"
]
generator_event_classification = events[event_cols]
display(generator_event_classification["event_class"].value_counts())
display(generator_event_classification.head())
save_csv(generator_event_classification, "generator_event_classification.csv")
"""),
        code("""
fig = px.scatter(
    generator_event_classification,
    x="settlementdate",
    y="rrp",
    color="event_class",
    facet_row="regionid",
    title="Classified Market Events"
)
fig.update_layout(height=800)
save_chart(fig, "classified_market_events.html")
fig.show()
"""),
    ],
    "09_decision_intelligence.ipynb": [
        md("""
# 09 Decision Intelligence

## Objective
Translate classified events into decision-ready market intelligence for traders, analysts, asset operators, modellers, and portfolio managers.

## Why this matters in the NEM
The value of analytics is not only identifying what happened. It is explaining why it matters, what risk it creates, and what action a market participant should consider.

## Outputs
- `market_decision_recommendations.csv`
"""),
        code(SETUP),
        code("""
events = pd.read_csv(OUTPUT_CSV / "generator_event_classification.csv", parse_dates=["settlementdate"])

def decision_record(row):
    event_class = row["event_class"]
    if event_class == "Supply Tightness Event":
        return pd.Series({
            "market_situation": "Supply margin tightening",
            "insight": "Available generation is not maintaining a comfortable buffer above regional demand.",
            "recommendation": "Monitor elevated scarcity pricing risk and review unit availability assumptions.",
            "risk": "Unexpected generator outage, renewable reduction, or interconnector constraint could amplify price response.",
            "confidence": "Medium-High",
        })
    if event_class == "Generator Ramping Event":
        return pd.Series({
            "market_situation": "Generator output moving rapidly",
            "insight": "Supply-side dispatch is changing quickly, indicating active response to demand, price, or system conditions.",
            "recommendation": "Identify fast-responding units and test whether ramping is stabilising or amplifying price outcomes.",
            "risk": "Ramp limits or delayed response may increase volatility during demand transitions.",
            "confidence": "Medium",
        })
    if event_class == "High Volatility Event":
        return pd.Series({
            "market_situation": "Price volatility elevated",
            "insight": "Regional price changes are abrupt, suggesting fragile dispatch balance or changing constraint/supply conditions.",
            "recommendation": "Review short-interval exposure, rebidding context, and generator response around the interval.",
            "risk": "Volatility can persist if supply response is insufficient or market conditions remain unstable.",
            "confidence": "Medium",
        })
    if event_class == "Oversupply Event":
        return pd.Series({
            "market_situation": "Oversupply pressure",
            "insight": "Negative prices and sufficient supply margin suggest surplus generation is placing downward pressure on price.",
            "recommendation": "Assess curtailment exposure, flexible load opportunities, and negative price bidding risk.",
            "risk": "Sustained oversupply can reduce revenue for inflexible generation and storage charging windows may tighten.",
            "confidence": "Medium-High",
        })
    if event_class == "Renewable Dominance Event":
        return pd.Series({
            "market_situation": "Renewable-led oversupply proxy",
            "insight": "Negative price conditions coincide with elevated aggregate output, consistent with renewable dominance risk.",
            "recommendation": "Extend analysis with DUID fuel mapping to separate solar, wind, hydro, coal, gas, and battery behaviour.",
            "risk": "Without technology mapping this remains a proxy, not a confirmed fuel-type attribution.",
            "confidence": "Medium",
        })
    if event_class == "Mixed Driver Event":
        return pd.Series({
            "market_situation": "Multiple market stress signals active",
            "insight": "Supply tightness, ramping, volatility, or oversupply signals overlap, indicating a more complex event.",
            "recommendation": "Prioritise interval-level review before drawing a single-driver conclusion.",
            "risk": "Single-factor explanations may miss the true operational driver.",
            "confidence": "Medium",
        })
    return pd.Series({
        "market_situation": "Normal dispatch conditions",
        "insight": "No major supply-side event signal detected.",
        "recommendation": "Use as baseline behaviour for comparison with stress periods.",
        "risk": "Low immediate event risk based on current rules.",
        "confidence": "Medium",
    })

recommendations = events.copy()
recommendations = pd.concat([recommendations, recommendations.apply(decision_record, axis=1)], axis=1)

cols = [
    "settlementdate", "regionid", "event_class", "rrp", "totaldemand", "availablegeneration",
    "supply_margin", "market_situation", "insight", "recommendation", "risk", "confidence"
]
market_decision_recommendations = recommendations[cols]
display(market_decision_recommendations.head())
save_csv(market_decision_recommendations, "market_decision_recommendations.csv")
"""),
    ],
    "10_powerbi_output_tables.ipynb": [
        md("""
# 10 Power BI Output Tables

## Objective
Prepare clean output tables for Power BI or GitHub Pages dashboard consumption.

## Why this matters in the NEM
Market intelligence needs to be visible and navigable. These tables provide a stable semantic layer for dashboard pages covering market overview, generation mix, ramping, supply adequacy, and decision intelligence.

## Outputs
The core CSV tables are already saved under `outputs/csv/`:

1. `market_generation_features.csv`
2. `generation_mix_summary.csv`
3. `generator_ramping_summary.csv`
4. `supply_adequacy_summary.csv`
5. `generator_event_classification.csv`
6. `market_decision_recommendations.csv`
"""),
        code(SETUP),
        code("""
required = [
    "market_generation_features.csv",
    "generation_mix_summary.csv",
    "generator_ramping_summary.csv",
    "supply_adequacy_summary.csv",
    "generator_event_classification.csv",
    "market_decision_recommendations.csv",
]

for filename in required:
    path = OUTPUT_CSV / filename
    if not path.exists():
        print(f"missing: {filename}")
    else:
        df = pd.read_csv(path)
        print(f"{filename}: rows={len(df):,}, columns={len(df.columns):,}")
        display(df.head(3))
"""),
        md("""
## Power BI dashboard structure

### Page 1: Market Overview
- RRP by region
- demand and available generation
- event count cards
- price spike and negative price interval filters

### Page 2: Generation Mix
- aggregate output trends
- output during high-price vs negative-price intervals
- regional comparison table

### Page 3: Generator Ramping
- top ramping DUIDs
- ramp rate distribution
- evening ramp window analysis
- spike response analysis

### Page 4: Supply Adequacy & Events
- supply margin over time
- stress intervals
- event classification scatter
- tight supply drill-through

### Page 5: Decision Intelligence
- event recommendations table
- confidence and risk slicers
- market situation summary
- interval-level analyst commentary
"""),
    ],
}


README = """
# NEM Generator Behaviour & Market Response Intelligence System

## Project Objective

This project builds a professional-grade market intelligence system that explains how generators and generation technologies respond to changing market conditions in the Australian National Electricity Market (NEM).

The system analyses generator response to price movements, generation ramping behaviour, supply adequacy, generation mix changes, market stress conditions, and supply-side drivers of volatility and price spikes.

## Business Question

How do generators respond to changing market conditions in the NEM, and how do generation behaviour, supply adequacy, and ramping influence prices, volatility, and market risk?

## Market Relevance

This portfolio project is designed for traders, market analysts, asset operators, energy modellers, and generation portfolio managers. It converts raw NEM operational data into decision-ready insights that explain:

- which generators respond during price spikes
- how available generation affects market stress
- which units ramp during volatile periods
- whether supply shortages are contributing to elevated prices
- how generation behaviour differs across normal, high-price, negative-price, and volatile intervals
- what supply-side signals indicate increased market risk

## Scope

- Date range: `2026-02-01` to `2026-03-01`
- Regions: `NSW1`, `VIC1`
- Source: existing NEMWeb ETL pipeline loaded into PostgreSQL
- Excludes bids in this version. `BIDDAYOFFER_D` and `BIDPEROFFER_D` are future extensions.

## Data Tables

| NEM table | PostgreSQL table | Purpose |
|---|---|---|
| DISPATCHPRICE | `raw.dispatch_price` | Regional dispatch price |
| DISPATCHREGIONSUM | `raw.dispatch_regionsum` | Demand, available generation, interchange |
| DISPATCH_UNIT_SCADA | `raw.dispatch_unit_scada` | Unit-level dispatch output |

## Methodology

1. Validate ETL outputs and inspect SCADA schema.
2. Extract dispatch price, regional summary, and unit SCADA from PostgreSQL.
3. Clean timestamps, intervention records, duplicates, missing values, and dispatch interval alignment.
4. Engineer market, generator, supply adequacy, price event, and time features.
5. Analyse generation mix and generator ramping behaviour.
6. Classify supply-side market events.
7. Generate decision intelligence recommendations.
8. Save CSV outputs and interactive Plotly HTML charts.
9. Structure outputs for Power BI and GitHub Pages presentation.

## Notebook Workflow

| Notebook | Purpose |
|---|---|
| `01_etl_download_load_validation.ipynb` | Validate ETL load, table coverage, and SCADA schema |
| `02_data_extraction_cleaning.ipynb` | Extract and clean PostgreSQL source data |
| `03_generator_feature_engineering.ipynb` | Create generator, market, supply adequacy, and event features |
| `04_generation_mix_analysis.ipynb` | Analyse aggregate generation behaviour and market outcomes |
| `05_generator_ramping_analysis.ipynb` | Identify rapid output changes and flexible units |
| `06_supply_adequacy_analysis.ipynb` | Analyse supply margin, tight conditions, and scarcity risk |
| `07_generator_response_price_events.ipynb` | Assess generator behaviour during price events |
| `08_event_classification.ipynb` | Classify supply-side event drivers |
| `09_decision_intelligence.ipynb` | Translate events into recommendations, risks, and confidence |
| `10_powerbi_output_tables.ipynb` | Prepare dashboard-ready output tables |

## Output Tables

Saved under `outputs/csv/`:

1. `market_generation_features.csv`
2. `generation_mix_summary.csv`
3. `generator_ramping_summary.csv`
4. `supply_adequacy_summary.csv`
5. `generator_event_classification.csv`
6. `market_decision_recommendations.csv`

## Plotly Visualisations

Saved under `outputs/charts/`:

- RRP vs generation
- available generation vs demand
- supply margin over time
- generator output trends
- generator ramping
- price spike periods
- negative price periods
- volatility periods
- generation during events

## Power BI Dashboard Pages

1. Market Overview
2. Generation Mix
3. Generator Ramping
4. Supply Adequacy & Events
5. Decision Intelligence

## Key Insights Framework

This project is designed to produce findings such as:

- whether tight supply margins are aligned with elevated prices
- which units have the strongest ramping response during price events
- whether negative price periods coincide with oversupply conditions
- whether high volatility intervals are associated with rapid aggregate generation movement
- where market risk is driven by supply tightness, ramping, oversupply, or mixed drivers

## Future Extensions

- Add DUID-to-fuel mapping for technology-specific generation mix analysis.
- Add bid data using `BIDDAYOFFER_D` and `BIDPEROFFER_D`.
- Add constraint and interconnector context from Project 2.
- Add storage charging/discharging classification.
- Add renewable forecast error and semi-scheduled curtailment analysis.
- Add automated GitHub Pages dashboard publishing.

## Tech Stack

- Python
- pandas
- numpy
- sqlalchemy
- psycopg2
- PostgreSQL
- Plotly
- HTML/CSS
- Power BI
- GitHub Pages
"""


REPORT = """
# Project 03 Generator Behaviour & Market Response Summary

## Executive Summary

This report summarises generator behaviour, ramping response, supply adequacy, and supply-side event drivers in NSW1 and VIC1 between 2026-02-01 and 2026-03-01.

The purpose is to explain how generators responded to market conditions and whether supply-side behaviour contributed to elevated prices, volatility, negative price outcomes, or market stress.

## Key Findings

Populate after running the notebooks:

- Finding 1:
- Finding 2:
- Finding 3:

## Generation Behaviour Insights

Assess aggregate generation output, output during high-price intervals, output during negative-price intervals, and regional differences.

## Generator Ramping Insights

Identify the fastest responding DUIDs, rapid ramping periods, evening ramp behaviour, and generator response during price spikes.

## Supply Adequacy Findings

Summarise supply margin behaviour, tight supply periods, scarcity risk indicators, and whether tight conditions aligned with elevated prices.

## Event Analysis

Classify events into:

- Supply Tightness Event
- Generator Ramping Event
- High Volatility Event
- Oversupply Event
- Renewable Dominance Event
- Mixed Driver Event

Explain the operational logic behind each material event.

## Decision Recommendations

Summarise recommendations for traders, analysts, operators, modellers, and portfolio managers.

## Limitations

- Unit fuel type mapping is not included in the initial version.
- Bid data is excluded, so bidding intent is not inferred.
- Renewable dominance is initially proxied using negative prices and aggregate output.
- Constraint and interconnector context should be linked from Project 2 in a later extension.

## Next Extension

The next extension should add DUID fuel/technology mapping, bid band behaviour, semi-scheduled curtailment, and constraint context to separate price outcomes driven by physical supply from outcomes driven by bidding and network limitations.
"""


DASHBOARD = """
# Power BI Dashboard Specification

## Page 1: Market Overview

Purpose: show the operating context for NSW1 and VIC1.

Visuals:
- RRP time series by region
- demand and available generation line chart
- event count cards
- price spike and negative price interval table
- region and date slicers

## Page 2: Generation Mix

Purpose: explain aggregate generation behaviour across market conditions.

Visuals:
- aggregate generation output trend
- output by market condition
- average output during spike, negative price, volatility, and normal intervals
- regional comparison matrix

## Page 3: Generator Ramping

Purpose: identify flexible and fast-responding units.

Visuals:
- top DUIDs by p95 ramp
- dispatch interval ramp time series
- evening ramp window analysis
- spike response table

## Page 4: Supply Adequacy & Events

Purpose: connect supply margin and market event classification.

Visuals:
- supply margin over time
- available generation vs demand
- event class scatter over RRP
- tight supply interval drill-through

## Page 5: Decision Intelligence

Purpose: turn event detection into action.

Visuals:
- recommendation table
- risk and confidence slicers
- event class cards
- market situation summary
"""


SQL = """
-- Project 03: NEM Generator Behaviour & Market Response Intelligence System
-- PostgreSQL extraction logic.
-- Parameters:
--   :start_date = '2026-02-01'
--   :end_date   = '2026-03-01'
--   :regions    = ARRAY['NSW1', 'VIC1']

-- 1. Dispatch price
select
    settlementdate,
    regionid,
    rrp,
    intervention,
    lastchanged
from raw.dispatch_price
where settlementdate >= :start_date
  and settlementdate < :end_date
  and regionid = any(:regions)
order by settlementdate, regionid, lastchanged;

-- 2. Regional demand, available generation, and interchange
select
    settlementdate,
    regionid,
    totaldemand,
    availablegeneration,
    netinterchange,
    intervention,
    lastchanged
from raw.dispatch_regionsum
where settlementdate >= :start_date
  and settlementdate < :end_date
  and regionid = any(:regions)
order by settlementdate, regionid, lastchanged;

-- 3. Unit-level SCADA output
select
    settlementdate,
    duid,
    scadavalue,
    intervention,
    lastchanged
from raw.dispatch_unit_scada
where settlementdate >= :start_date
  and settlementdate < :end_date
order by settlementdate, duid, lastchanged;

-- 4. Mandatory SCADA schema inspection
select
    column_name,
    data_type
from information_schema.columns
where table_schema = 'raw'
  and table_name = 'dispatch_unit_scada'
order by ordinal_position;

-- 5. SCADA row count
select count(*) as row_count
from raw.dispatch_unit_scada;

-- 6. SCADA null checks
select
    count(*) filter (where settlementdate is null) as settlementdate_nulls,
    count(*) filter (where duid is null) as duid_nulls,
    count(*) filter (where scadavalue is null) as scadavalue_nulls,
    count(*) filter (where intervention is null) as intervention_nulls,
    count(*) filter (where lastchanged is null) as lastchanged_nulls
from raw.dispatch_unit_scada;
"""


INDEX_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>NEM Generator Behaviour Intelligence</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <header class="topbar">
    <div>
      <p class="eyebrow">Australian National Electricity Market</p>
      <h1>Generator Behaviour & Market Response Intelligence</h1>
      <p class="summary">A supply-side market intelligence project for NSW1 and VIC1, focused on generator response, ramping, supply adequacy, event classification, and decision-ready recommendations.</p>
    </div>
  </header>

  <main>
    <section class="section">
      <h2>Dashboard Pages</h2>
      <div class="grid">
        <article>
          <h3>Market Overview</h3>
          <p>RRP, demand, available generation, and event counts.</p>
        </article>
        <article>
          <h3>Generation Mix</h3>
          <p>Aggregate output trends and behaviour across market conditions.</p>
        </article>
        <article>
          <h3>Generator Ramping</h3>
          <p>Fast-responding units, rapid dispatch movement, and evening ramp periods.</p>
        </article>
        <article>
          <h3>Supply Adequacy & Events</h3>
          <p>Supply margin, stress intervals, and classified market events.</p>
        </article>
        <article>
          <h3>Decision Intelligence</h3>
          <p>Market situation, insight, recommendation, risk, and confidence.</p>
        </article>
      </div>
    </section>

    <section class="section">
      <h2>Interactive Plotly Outputs</h2>
      <p>After running the notebooks, publish the generated HTML files from <code>outputs/charts/</code> or embed them here for GitHub Pages.</p>
      <ul>
        <li><code>rrp_vs_generation.html</code></li>
        <li><code>available_generation_vs_demand_supply_margin.html</code></li>
        <li><code>generator_ramping.html</code></li>
        <li><code>classified_market_events.html</code></li>
        <li><code>generation_during_events.html</code></li>
      </ul>
    </section>
  </main>
</body>
</html>
"""


STYLE_CSS = """
:root {
  color-scheme: light;
  --ink: #17202a;
  --muted: #5b6776;
  --line: #d9e1ea;
  --bg: #f7f9fb;
  --panel: #ffffff;
  --accent: #0f766e;
  --accent-2: #b45309;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: Inter, Arial, sans-serif;
  background: var(--bg);
  color: var(--ink);
}

.topbar {
  background: #0b1f2a;
  color: white;
  padding: 48px 28px 42px;
}

.topbar > div,
main {
  max-width: 1120px;
  margin: 0 auto;
}

.eyebrow {
  margin: 0 0 10px;
  color: #8bd4cc;
  font-size: 13px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0;
}

h1 {
  margin: 0;
  max-width: 860px;
  font-size: 42px;
  line-height: 1.12;
}

.summary {
  max-width: 780px;
  margin: 18px 0 0;
  color: #d8e5ea;
  font-size: 18px;
  line-height: 1.55;
}

main {
  padding: 30px 24px 56px;
}

.section {
  margin-top: 28px;
}

h2 {
  font-size: 24px;
  margin: 0 0 16px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 14px;
}

article {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 18px;
}

h3 {
  margin: 0 0 8px;
  font-size: 17px;
}

p,
li {
  color: var(--muted);
  line-height: 1.55;
}

code {
  color: var(--accent);
  font-weight: 700;
}
"""


LINKEDIN = """
# LinkedIn Positioning

## Suggested Headline

Built a NEM Generator Behaviour & Market Response Intelligence System using Python, PostgreSQL, Plotly, and Power BI.

## Positioning

This project demonstrates how raw NEM dispatch data can be converted into decision-ready market intelligence for generation behaviour, ramping response, supply adequacy, and price event analysis.

## Suggested Post

I have completed Project 3 in my Australian National Electricity Market portfolio: a Generator Behaviour & Market Response Intelligence System.

This project analyses how generators respond to changing market conditions across NSW1 and VIC1, focusing on:

- generator response during price spikes and negative prices
- dispatch interval ramping behaviour
- supply margin and scarcity risk
- generation behaviour across normal and stressed market conditions
- event classification and decision intelligence

The workflow uses PostgreSQL extraction, Python data cleaning, feature engineering, event classification, Plotly visualisations, Power BI-ready outputs, and an analyst report.

The goal is to simulate the thinking of an Energy Market Analyst or Energy Modeller: not just charting dispatch data, but explaining what the market behaviour means for traders, operators, modellers, and portfolio managers.

## Audience Fit

This project is positioned for:

- energy market analysts
- trading and commercial analytics teams
- generation portfolio managers
- energy modelling teams
- recruiters hiring for NEM, trading, analytics, or market modelling roles

## Recruiter Signal

Emphasise:

- PostgreSQL and Python workflow
- operational understanding of NEM dispatch data
- ability to translate raw market data into business recommendations
- dashboard-ready outputs and executive reporting
"""


REQUIREMENTS = """
pandas>=2.2
numpy>=1.26
sqlalchemy>=2.0
psycopg2-binary>=2.9
plotly>=5.22
jupyter>=1.0
ipykernel>=6.29
nbformat>=5.10
python-dotenv>=1.0
"""


GITIGNORE = """
.DS_Store
__pycache__/
*.pyc
.ipynb_checkpoints/
.env
outputs/csv/*.csv
outputs/charts/*.html
!outputs/csv/.gitkeep
!outputs/charts/.gitkeep
"""


HELPERS = '''
"""Shared helpers for the NEM generator behaviour project."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine


START_DATE = "2026-02-01"
END_DATE = "2026-03-01"
REGIONS = ["NSW1", "VIC1"]


def project_root() -> Path:
    root = Path.cwd()
    return root.parent if root.name == "notebooks" else root


def output_paths() -> tuple[Path, Path, Path]:
    root = project_root()
    csv = root / "outputs" / "csv"
    charts = root / "outputs" / "charts"
    reports = root / "outputs" / "reports"
    for path in [csv, charts, reports]:
        path.mkdir(parents=True, exist_ok=True)
    return csv, charts, reports


def get_engine_from_env():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("Set DATABASE_URL, for example postgresql+psycopg2://user:password@host:5432/dbname")
    return create_engine(database_url)


def save_csv(df: pd.DataFrame, filename: str) -> Path:
    csv_dir, _, _ = output_paths()
    path = csv_dir / filename
    df.to_csv(path, index=False)
    return path
'''


def write_text(path: Path, text: str) -> None:
    path.write_text(text.strip() + "\n", encoding="utf-8")


def main() -> None:
    for folder in [
        "notebooks",
        "outputs/csv",
        "outputs/charts",
        "outputs/reports",
        "dashboard",
        "src/nem_generator_behaviour",
    ]:
        (ROOT / folder).mkdir(parents=True, exist_ok=True)

    for name, cells in NOTEBOOKS.items():
        (ROOT / "notebooks" / name).write_text(
            json.dumps(notebook(cells), indent=2),
            encoding="utf-8",
        )

    write_text(ROOT / "README.md", README)
    write_text(ROOT / "requirements.txt", REQUIREMENTS)
    write_text(ROOT / ".gitignore", GITIGNORE)
    write_text(ROOT / "outputs" / "reports" / "project_03_generator_behaviour_summary.md", REPORT)
    write_text(ROOT / "dashboard" / "powerbi_dashboard_spec.md", DASHBOARD)
    write_text(ROOT / "dashboard" / "linkedin_positioning.md", LINKEDIN)
    write_text(ROOT / "dashboard" / "index.html", INDEX_HTML)
    write_text(ROOT / "dashboard" / "style.css", STYLE_CSS)
    write_text(ROOT / "sql" / "extraction_queries.sql", SQL)
    write_text(ROOT / "src" / "nem_generator_behaviour" / "__init__.py", "")
    write_text(ROOT / "src" / "nem_generator_behaviour" / "helpers.py", HELPERS)

    for keep in [
        ROOT / "outputs" / "csv" / ".gitkeep",
        ROOT / "outputs" / "charts" / ".gitkeep",
    ]:
        keep.touch()


if __name__ == "__main__":
    main()
