from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_DIR = ROOT / "notebooks"


def md(text: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": text.strip().splitlines(True),
    }


def code(text: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": text.strip().splitlines(True),
    }


def nb(cells: list[dict]) -> dict:
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


NOTEBOOK_07 = nb([
    md("""
# Notebook 07: Event Classification

## Project
NEM Generator Behaviour & Market Response Intelligence System

## Objective
Classify dispatch intervals into supply-side market event drivers using price, supply adequacy, volatility, and aggregate generator ramping features.

## Business Question
What type of market event occurred in each interval, and was the event mainly driven by supply tightness, generator ramping, volatility, oversupply, renewable dominance proxy, or mixed drivers?

## Input Files
- `outputs/05_market_features_with_supply_condition.csv`
- `outputs/04_event_ramp_comparison.csv`
- `outputs/06_event_interval_generator_response.csv`

## Output Files
- `outputs/07_generator_event_classification.csv`
- `outputs/07_event_classification_summary.csv`
- `outputs/07_mixed_driver_events.csv`
"""),
    code("""
from pathlib import Path

import pandas as pd
import numpy as np

pd.set_option("display.max_columns", 100)
"""),
    md("""
## Step 1: Define Project Paths

### What we are doing
We are locating the project root and defining the input files created by earlier notebooks.

### Why it matters
Event classification should use the engineered features already created, rather than rebuilding extraction or cleaning logic.
"""),
    code("""
PROJECT_ROOT = (
    Path.cwd().parents[0]
    if Path.cwd().name == "notebooks"
    else Path.cwd()
)

OUTPUT_DIR = PROJECT_ROOT / "outputs"

MARKET_SUPPLY_FILE = OUTPUT_DIR / "05_market_features_with_supply_condition.csv"
EVENT_RESPONSE_FILE = OUTPUT_DIR / "06_event_interval_generator_response.csv"
RAMP_COMPARISON_FILE = OUTPUT_DIR / "04_event_ramp_comparison.csv"

print("Project root:", PROJECT_ROOT)
print("Market supply file:", MARKET_SUPPLY_FILE)
print("Event response file:", EVENT_RESPONSE_FILE)
print("Ramp comparison file:", RAMP_COMPARISON_FILE)
"""),
    md("""
## Step 2: Load Market And Generator Event Data

### What we are doing
We are loading the regional market feature table and the DUID-level event response table.

### Why it matters
The market table contains interval-level price, supply, volatility, and aggregate ramping signals. The generator response table provides supporting DUID-level evidence for event interpretation.
"""),
    code("""
market_events = pd.read_csv(
    MARKET_SUPPLY_FILE,
    parse_dates=["settlementdate"]
)

event_generator_response = pd.read_csv(
    EVENT_RESPONSE_FILE,
    parse_dates=["settlementdate"]
)

market_events.head()
"""),
    code("""
print("Market events shape:", market_events.shape)
print("Generator event response shape:", event_generator_response.shape)
print("Regions:", market_events["regionid"].unique())
print("Date range:", market_events["settlementdate"].min(), "to", market_events["settlementdate"].max())
"""),
    md("""
## Step 3: Create Classification Driver Flags

### What we are doing
We are creating logical driver flags for supply tightness, generator ramping, high volatility, oversupply, and renewable dominance proxy.

### Why it matters
Professional market event analysis should separate the type of driver behind an event. A high price interval caused by tight supply is different from a volatile interval caused by rapid generator movement or a negative price interval caused by oversupply.
"""),
    code("""
classified_events = market_events.copy()

classified_events["aggregate_ramp_p90"] = (
    classified_events
    .groupby("regionid")["aggregate_absolute_ramp"]
    .transform(lambda x: x.quantile(0.90))
)

classified_events["rapid_units_p90"] = (
    classified_events
    .groupby("regionid")["rapid_ramping_units"]
    .transform(lambda x: x.quantile(0.90))
)

classified_events["generation_output_p75"] = (
    classified_events
    .groupby("regionid")["total_generation_output"]
    .transform(lambda x: x.quantile(0.75))
)

classified_events["supply_tightness_driver"] = (
    classified_events["supply_stress_flag"]
    | (classified_events["supply_margin_pct"] < 0.15)
)

classified_events["generator_ramping_driver"] = (
    (classified_events["aggregate_absolute_ramp"] >= classified_events["aggregate_ramp_p90"])
    | (classified_events["rapid_ramping_units"] >= classified_events["rapid_units_p90"])
)

classified_events["high_volatility_driver"] = classified_events["volatility_flag"]

classified_events["oversupply_driver"] = (
    classified_events["negative_price_flag"]
    & (classified_events["supply_margin_pct"] >= 0.25)
)

classified_events["renewable_dominance_proxy_driver"] = (
    classified_events["negative_price_flag"]
    & (classified_events["total_generation_output"] >= classified_events["generation_output_p75"])
)

classified_events[
    [
        "settlementdate",
        "regionid",
        "rrp",
        "supply_margin_pct",
        "aggregate_absolute_ramp",
        "rapid_ramping_units",
        "supply_tightness_driver",
        "generator_ramping_driver",
        "high_volatility_driver",
        "oversupply_driver",
        "renewable_dominance_proxy_driver",
    ]
].head()
"""),
    md("""
## Step 4: Classify Market Events

### What we are doing
We are converting the driver flags into a single event class and an analyst explanation.

### Why it matters
Event classification turns raw market signals into a business-readable description of what likely mattered in the interval.
"""),
    code("""
driver_columns = [
    "supply_tightness_driver",
    "generator_ramping_driver",
    "high_volatility_driver",
    "oversupply_driver",
    "renewable_dominance_proxy_driver",
]

def classify_event(row):
    active_drivers = [col for col in driver_columns if row[col]]

    if len(active_drivers) > 1:
        return "Mixed Driver Event"
    if row["supply_tightness_driver"]:
        return "Supply Tightness Event"
    if row["generator_ramping_driver"]:
        return "Generator Ramping Event"
    if row["high_volatility_driver"]:
        return "High Volatility Event"
    if row["oversupply_driver"]:
        return "Oversupply Event"
    if row["renewable_dominance_proxy_driver"]:
        return "Renewable Dominance Event"
    return "Normal Dispatch Interval"

def explain_event(row):
    if row["event_class"] == "Supply Tightness Event":
        return "Supply margin is tight relative to demand, increasing scarcity pricing risk."
    if row["event_class"] == "Generator Ramping Event":
        return "Aggregate generator movement is elevated, indicating material supply-side response."
    if row["event_class"] == "High Volatility Event":
        return "Regional price volatility is elevated, indicating unstable market conditions."
    if row["event_class"] == "Oversupply Event":
        return "Negative prices and a healthy supply margin indicate oversupply pressure."
    if row["event_class"] == "Renewable Dominance Event":
        return "Negative price conditions coincide with elevated aggregate output, used here as a renewable dominance proxy."
    if row["event_class"] == "Mixed Driver Event":
        return "Multiple market signals are active, so the interval should not be explained by a single driver."
    return "No material event driver was detected under the selected rules."

classified_events["active_driver_count"] = classified_events[driver_columns].sum(axis=1)
classified_events["event_class"] = classified_events.apply(classify_event, axis=1)
classified_events["event_explanation"] = classified_events.apply(explain_event, axis=1)

classified_events[
    [
        "settlementdate",
        "regionid",
        "rrp",
        "supply_margin_pct",
        "event_class",
        "active_driver_count",
        "event_explanation",
    ]
].head(20)
"""),
    md("""
## Step 5: Summarise Event Classes

### What we are doing
We are counting event classes by region and summarising price, supply margin, and ramping metrics.

### Why it matters
This shows which event types were most common and whether they were associated with materially different market outcomes.
"""),
    code("""
event_classification_summary = (
    classified_events
    .groupby(["regionid", "event_class"])
    .agg(
        intervals=("settlementdate", "count"),
        average_rrp=("rrp", "mean"),
        max_rrp=("rrp", "max"),
        min_rrp=("rrp", "min"),
        average_supply_margin_pct=("supply_margin_pct", "mean"),
        average_supply_margin_mw=("supply_margin", "mean"),
        average_aggregate_absolute_ramp=("aggregate_absolute_ramp", "mean"),
        average_rapid_ramping_units=("rapid_ramping_units", "mean"),
        price_spike_intervals=("price_spike_flag", "sum"),
        negative_price_intervals=("negative_price_flag", "sum"),
    )
    .reset_index()
)

event_classification_summary["event_share_pct"] = (
    event_classification_summary["intervals"]
    / event_classification_summary.groupby("regionid")["intervals"].transform("sum")
    * 100
)

event_classification_summary.sort_values(["regionid", "intervals"], ascending=[True, False])
"""),
    md("""
## Step 6: Isolate Mixed Driver Events

### What we are doing
We are filtering intervals where more than one event driver was active.

### Why it matters
Mixed driver events are usually the most important intervals for analyst review because a single-factor explanation may be misleading.
"""),
    code("""
mixed_driver_events = (
    classified_events[
        classified_events["event_class"] == "Mixed Driver Event"
    ]
    .copy()
    .sort_values(["regionid", "rrp"], ascending=[True, False])
)

mixed_driver_events[
    [
        "settlementdate",
        "regionid",
        "rrp",
        "supply_margin_pct",
        "aggregate_absolute_ramp",
        "rapid_ramping_units",
        "supply_tightness_driver",
        "generator_ramping_driver",
        "high_volatility_driver",
        "oversupply_driver",
        "renewable_dominance_proxy_driver",
        "event_explanation",
    ]
].head(30)
"""),
    md("""
## Step 7: Save Notebook 07 Outputs

### What we are doing
We are saving event classification tables for decision intelligence and dashboard use.

### Why it matters
These outputs become the input to Notebook 08, where event classes are converted into market situations, insights, recommendations, risks, and confidence levels.
"""),
    code("""
event_classification_output = OUTPUT_DIR / "07_generator_event_classification.csv"
event_classification_summary_output = OUTPUT_DIR / "07_event_classification_summary.csv"
mixed_driver_events_output = OUTPUT_DIR / "07_mixed_driver_events.csv"

classified_events.to_csv(event_classification_output, index=False)
event_classification_summary.to_csv(event_classification_summary_output, index=False)
mixed_driver_events.to_csv(mixed_driver_events_output, index=False)

print("Saved:", event_classification_output)
print("Saved:", event_classification_summary_output)
print("Saved:", mixed_driver_events_output)
"""),
    md("""
## Notebook 07 Summary

| Step | What we did | Why it matters for NEM analysis | Output / Result |
|---|---|---|---|
| 1 | Loaded market and generator event data | Brings together price, supply, ramping, and event response context | Input CSVs loaded |
| 2 | Created driver flags | Separates supply tightness, ramping, volatility, oversupply, and renewable dominance proxy signals | Driver flag columns |
| 3 | Classified each interval | Converts market signals into event classes | `event_class` |
| 4 | Added event explanations | Makes the classification analyst-readable | `event_explanation` |
| 5 | Summarised event classes | Shows event frequency and market outcomes by region | `07_event_classification_summary.csv` |
| 6 | Isolated mixed driver events | Identifies complex intervals requiring careful interpretation | `07_mixed_driver_events.csv` |
| 7 | Saved outputs | Creates input tables for decision intelligence and dashboards | CSV outputs saved to `outputs/` |

### Conceptual takeaway

Notebook 07 turns engineered features into market event narratives.

Instead of only saying that price was high or generation ramped, this notebook classifies the likely operating condition behind each interval.
"""),
    md("""
## Analyst Note

Notebook 07 classified market intervals into supply tightness, generator ramping, high volatility, oversupply, renewable dominance proxy, mixed driver, and normal dispatch conditions.

The classification is rule-based and transparent. It is designed for portfolio analysis, dashboard filtering, and decision intelligence rather than black-box prediction.
"""),
])


NOTEBOOK_08 = nb([
    md("""
# Notebook 08: Decision Intelligence

## Project
NEM Generator Behaviour & Market Response Intelligence System

## Objective
Convert classified market events into decision-ready intelligence with market situation, insight, recommendation, risk, and confidence.

## Business Question
What should a trader, market analyst, asset operator, energy modeller, or portfolio manager take away from each classified event?

## Input Files
- `outputs/07_generator_event_classification.csv`
- `outputs/07_event_classification_summary.csv`

## Output Files
- `outputs/08_market_decision_recommendations.csv`
- `outputs/08_decision_summary_by_event_class.csv`
- `outputs/08_high_priority_market_events.csv`
"""),
    code("""
from pathlib import Path

import pandas as pd
import numpy as np

pd.set_option("display.max_columns", 100)
"""),
    md("""
## Step 1: Define Project Paths

### What we are doing
We are locating the event classification outputs from Notebook 07.

### Why it matters
Decision intelligence should be based on transparent event classifications and the market evidence behind them.
"""),
    code("""
PROJECT_ROOT = (
    Path.cwd().parents[0]
    if Path.cwd().name == "notebooks"
    else Path.cwd()
)

OUTPUT_DIR = PROJECT_ROOT / "outputs"

EVENT_CLASSIFICATION_FILE = OUTPUT_DIR / "07_generator_event_classification.csv"
EVENT_SUMMARY_FILE = OUTPUT_DIR / "07_event_classification_summary.csv"

print("Project root:", PROJECT_ROOT)
print("Event classification file:", EVENT_CLASSIFICATION_FILE)
print("Event summary file:", EVENT_SUMMARY_FILE)
"""),
    md("""
## Step 2: Load Classified Events

### What we are doing
We are loading the interval-level classified event table.

### Why it matters
Each interval already contains the market condition, event class, and supporting price, supply, and ramping features needed for decision recommendations.
"""),
    code("""
classified_events = pd.read_csv(
    EVENT_CLASSIFICATION_FILE,
    parse_dates=["settlementdate"]
)

event_summary = pd.read_csv(EVENT_SUMMARY_FILE)

classified_events.head()
"""),
    code("""
print("Classified events shape:", classified_events.shape)
print("Event classes:", classified_events["event_class"].unique())
event_summary.head()
"""),
    md("""
## Step 3: Create Decision Intelligence Logic

### What we are doing
We are mapping each event class to a market situation, insight, recommendation, risk, and confidence level.

### Why it matters
This translates technical feature outputs into the type of operational commentary used by market analysts and trading teams.
"""),
    code("""
def create_decision_record(row):
    event_class = row["event_class"]

    if event_class == "Supply Tightness Event":
        return pd.Series({
            "market_situation": "Supply margin tightening",
            "insight": "Available generation buffer is low relative to demand, increasing price sensitivity.",
            "recommendation": "Monitor scarcity pricing risk and review outage, renewable, and interconnector assumptions.",
            "risk": "Unexpected generator outage, renewable reduction, or import limitation could amplify prices.",
            "confidence": "Medium-High",
            "priority": "High",
        })

    if event_class == "Generator Ramping Event":
        return pd.Series({
            "market_situation": "Generator output moving rapidly",
            "insight": "Aggregate generator movement is elevated, indicating material supply-side response.",
            "recommendation": "Identify fast-moving DUIDs and test whether ramping is stabilising or amplifying price outcomes.",
            "risk": "Ramp limits or delayed response may increase volatility during demand transitions.",
            "confidence": "Medium",
            "priority": "Medium",
        })

    if event_class == "High Volatility Event":
        return pd.Series({
            "market_situation": "Price volatility elevated",
            "insight": "Recent RRP movement is unstable, suggesting fragile dispatch balance or changing supply conditions.",
            "recommendation": "Review short-interval exposure and compare generator movement with volatility timing.",
            "risk": "Volatility can persist if market balance remains fragile or generator response is uneven.",
            "confidence": "Medium",
            "priority": "Medium",
        })

    if event_class == "Oversupply Event":
        return pd.Series({
            "market_situation": "Oversupply pressure",
            "insight": "Negative prices and a healthy supply buffer suggest surplus generation pressure.",
            "recommendation": "Assess curtailment exposure, flexible load opportunities, storage charging value, and negative price risk.",
            "risk": "Sustained oversupply can reduce revenue for inflexible generation.",
            "confidence": "Medium-High",
            "priority": "Medium",
        })

    if event_class == "Renewable Dominance Event":
        return pd.Series({
            "market_situation": "Renewable dominance proxy active",
            "insight": "Negative price conditions coincide with elevated aggregate output.",
            "recommendation": "Add DUID fuel mapping to confirm whether wind, solar, hydro, storage, or thermal units drove the event.",
            "risk": "Without fuel mapping, technology attribution remains a proxy rather than confirmed causality.",
            "confidence": "Medium",
            "priority": "Medium",
        })

    if event_class == "Mixed Driver Event":
        return pd.Series({
            "market_situation": "Multiple market stress signals active",
            "insight": "More than one event driver is active, so a single-driver explanation may be misleading.",
            "recommendation": "Prioritise interval-level review and compare supply margin, ramping, volatility, and negative price signals together.",
            "risk": "Simplified explanations may miss the true operational driver.",
            "confidence": "Medium",
            "priority": "High",
        })

    return pd.Series({
        "market_situation": "Normal dispatch conditions",
        "insight": "No material supply-side event signal was detected under the selected rules.",
        "recommendation": "Use as baseline behaviour for comparison against event intervals.",
        "risk": "Low immediate event risk based on current indicators.",
        "confidence": "Medium",
        "priority": "Low",
    })

decision_fields = classified_events.apply(create_decision_record, axis=1)
decision_recommendations = pd.concat([classified_events, decision_fields], axis=1)

decision_recommendations[
    [
        "settlementdate",
        "regionid",
        "event_class",
        "market_situation",
        "insight",
        "recommendation",
        "risk",
        "confidence",
        "priority",
    ]
].head(20)
"""),
    md("""
## Step 4: Identify High Priority Market Events

### What we are doing
We are filtering high-priority events and ranking them by price and event complexity.

### Why it matters
Analysts and traders need to know which intervals deserve attention first.
"""),
    code("""
high_priority_market_events = (
    decision_recommendations[
        decision_recommendations["priority"] == "High"
    ]
    .copy()
    .sort_values(
        ["regionid", "rrp", "active_driver_count"],
        ascending=[True, False, False]
    )
)

high_priority_market_events[
    [
        "settlementdate",
        "regionid",
        "rrp",
        "event_class",
        "supply_margin_pct",
        "aggregate_absolute_ramp",
        "active_driver_count",
        "market_situation",
        "recommendation",
        "risk",
        "confidence",
    ]
].head(30)
"""),
    md("""
## Step 5: Summarise Decision Intelligence By Event Class

### What we are doing
We are summarising priority, confidence, price, and supply margin by event class.

### Why it matters
This provides a dashboard-ready view of how often each type of recommendation appears and which event classes carry the highest market risk.
"""),
    code("""
decision_summary_by_event_class = (
    decision_recommendations
    .groupby(["regionid", "event_class", "priority", "confidence"])
    .agg(
        intervals=("settlementdate", "count"),
        average_rrp=("rrp", "mean"),
        max_rrp=("rrp", "max"),
        average_supply_margin_pct=("supply_margin_pct", "mean"),
        average_aggregate_absolute_ramp=("aggregate_absolute_ramp", "mean"),
        price_spike_intervals=("price_spike_flag", "sum"),
        negative_price_intervals=("negative_price_flag", "sum"),
    )
    .reset_index()
    .sort_values(["regionid", "priority", "intervals"], ascending=[True, True, False])
)

decision_summary_by_event_class
"""),
    md("""
## Step 6: Save Notebook 08 Outputs

### What we are doing
We are saving decision intelligence recommendations and summary tables.

### Why it matters
These outputs support the Decision Intelligence dashboard page and the final analyst report.
"""),
    code("""
decision_recommendations_output = OUTPUT_DIR / "08_market_decision_recommendations.csv"
decision_summary_output = OUTPUT_DIR / "08_decision_summary_by_event_class.csv"
high_priority_events_output = OUTPUT_DIR / "08_high_priority_market_events.csv"

decision_recommendations.to_csv(decision_recommendations_output, index=False)
decision_summary_by_event_class.to_csv(decision_summary_output, index=False)
high_priority_market_events.to_csv(high_priority_events_output, index=False)

print("Saved:", decision_recommendations_output)
print("Saved:", decision_summary_output)
print("Saved:", high_priority_events_output)
"""),
    md("""
## Notebook 08 Summary

| Step | What we did | Why it matters for NEM analysis | Output / Result |
|---|---|---|---|
| 1 | Loaded classified events | Uses transparent event logic from Notebook 07 | `07_generator_event_classification.csv` |
| 2 | Mapped event classes to decisions | Converts analytics into market commentary | Situation, insight, recommendation, risk, confidence |
| 3 | Identified high-priority events | Focuses analyst attention on complex or scarcity-driven intervals | `08_high_priority_market_events.csv` |
| 4 | Summarised decisions by event class | Creates dashboard-ready decision intelligence summaries | `08_decision_summary_by_event_class.csv` |
| 5 | Saved recommendation table | Provides final decision intelligence output | `08_market_decision_recommendations.csv` |

### Conceptual takeaway

Notebook 08 converts feature engineering and event classification into decision-ready market intelligence.

This is the point where the project moves from analysis to action: what happened, why it matters, what to monitor, what risk exists, and how confident the analyst should be.
"""),
    md("""
## Analyst Note

Notebook 08 translated classified market events into practical recommendations for traders, analysts, asset operators, modellers, and portfolio managers.

The decision logic is deliberately transparent and rule-based so that recommendations can be reviewed, challenged, and improved as additional datasets such as bids, fuel mapping, and constraints are added.
"""),
])


NOTEBOOK_09 = nb([
    md("""
# Notebook 09: Plotly Visualisation Pack

## Project
NEM Generator Behaviour & Market Response Intelligence System

## Objective
Create interactive Plotly HTML charts for generation behaviour, supply adequacy, ramping, event classification, and decision intelligence.

## Business Question
How can generator behaviour and market response insights be communicated visually for dashboard and portfolio presentation?

## Input Files
- `outputs/02_generator_market_features.csv`
- `outputs/04_generator_ramping_summary.csv`
- `outputs/07_generator_event_classification.csv`
- `outputs/08_market_decision_recommendations.csv`

## Output Files
Interactive HTML charts saved under `outputs/charts/`.
"""),
    code("""
from pathlib import Path

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

pd.set_option("display.max_columns", 100)
"""),
    md("""
## Step 1: Define Project Paths

### What we are doing
We are locating input CSV files and creating the chart output directory.

### Why it matters
The Plotly chart pack should be reproducible and saved as standalone HTML files for GitHub Pages or dashboard embedding.
"""),
    code("""
PROJECT_ROOT = (
    Path.cwd().parents[0]
    if Path.cwd().name == "notebooks"
    else Path.cwd()
)

OUTPUT_DIR = PROJECT_ROOT / "outputs"
CHART_DIR = OUTPUT_DIR / "charts"
CHART_DIR.mkdir(parents=True, exist_ok=True)

MARKET_FEATURES_FILE = OUTPUT_DIR / "02_generator_market_features.csv"
RAMPING_SUMMARY_FILE = OUTPUT_DIR / "04_generator_ramping_summary.csv"
EVENT_CLASSIFICATION_FILE = OUTPUT_DIR / "07_generator_event_classification.csv"
DECISION_RECOMMENDATIONS_FILE = OUTPUT_DIR / "08_market_decision_recommendations.csv"

print("Project root:", PROJECT_ROOT)
print("Chart directory:", CHART_DIR)
"""),
    md("""
## Step 2: Load Visualisation Inputs

### What we are doing
We are loading market features, ramping summary, event classification, and decision recommendations.

### Why it matters
These tables cover the full project narrative: market overview, generator ramping, supply adequacy, event classification, and decision intelligence.
"""),
    code("""
market_features = pd.read_csv(
    MARKET_FEATURES_FILE,
    parse_dates=["settlementdate"]
)

ramping_summary = pd.read_csv(RAMPING_SUMMARY_FILE)

event_classification = pd.read_csv(
    EVENT_CLASSIFICATION_FILE,
    parse_dates=["settlementdate"]
)

decision_recommendations = pd.read_csv(
    DECISION_RECOMMENDATIONS_FILE,
    parse_dates=["settlementdate"]
)

print("Market features:", market_features.shape)
print("Ramping summary:", ramping_summary.shape)
print("Event classification:", event_classification.shape)
print("Decision recommendations:", decision_recommendations.shape)
"""),
    code("""
def save_chart(fig, filename):
    path = CHART_DIR / filename
    fig.write_html(path, include_plotlyjs="cdn")
    print("Saved:", path)
    return path
"""),
    md("""
## Step 3: RRP And Supply Margin By Region

### What we are doing
We are plotting RRP and supply margin across the study period.

### Why it matters
This chart helps identify whether price outcomes appear to align with changing supply adequacy.
"""),
    code("""
fig = px.line(
    event_classification,
    x="settlementdate",
    y="rrp",
    color="event_class",
    facet_row="regionid",
    hover_data=[
        "supply_margin",
        "supply_margin_pct",
        "aggregate_absolute_ramp",
        "rapid_ramping_units",
    ],
    title="RRP By Event Classification"
)
fig.update_layout(height=850)
save_chart(fig, "09_rrp_by_event_classification.html")
fig.show()
"""),
    md("""
## Step 4: Available Generation Versus Demand

### What we are doing
We are comparing available generation with total demand by region.

### Why it matters
This is the core supply adequacy view. Tight separation between available generation and demand indicates reduced supply buffer.
"""),
    code("""
availability_plot = market_features.melt(
    id_vars=["settlementdate", "regionid"],
    value_vars=["totaldemand", "availablegeneration"],
    var_name="metric",
    value_name="mw"
)

fig = px.line(
    availability_plot,
    x="settlementdate",
    y="mw",
    color="metric",
    facet_row="regionid",
    title="Available Generation Versus Demand"
)
fig.update_layout(height=800)
save_chart(fig, "09_available_generation_vs_demand.html")
fig.show()
"""),
    md("""
## Step 5: Supply Margin Over Time

### What we are doing
We are plotting supply margin and colouring intervals by supply stress.

### Why it matters
Supply margin is a practical scarcity risk indicator for traders, analysts, and portfolio managers.
"""),
    code("""
fig = px.scatter(
    event_classification,
    x="settlementdate",
    y="supply_margin",
    color="event_class",
    facet_row="regionid",
    hover_data=["rrp", "supply_margin_pct", "event_explanation"],
    title="Supply Margin Over Time By Event Class"
)
fig.update_layout(height=850)
save_chart(fig, "09_supply_margin_by_event_class.html")
fig.show()
"""),
    md("""
## Step 6: Top Generator Ramping Units

### What we are doing
We are plotting the top DUIDs by 95th percentile absolute ramp.

### Why it matters
This identifies the units that showed the strongest material output movement during the study period.
"""),
    code("""
top_ramping = (
    ramping_summary
    .sort_values("p95_absolute_ramp_mw", ascending=False)
    .head(25)
)

fig = px.bar(
    top_ramping,
    x="p95_absolute_ramp_mw",
    y="duid",
    color="ramping_category" if "ramping_category" in top_ramping.columns else None,
    orientation="h",
    hover_data=[
        "average_output_mw",
        "max_absolute_ramp_mw",
        "rapid_ramping_intervals",
    ],
    title="Top Generator Ramping Units"
)
fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=800)
save_chart(fig, "09_top_generator_ramping_units.html")
fig.show()
"""),
    md("""
## Step 7: Event Classification Summary

### What we are doing
We are counting event classes by region.

### Why it matters
This gives a portfolio-level view of how often each type of market condition occurred.
"""),
    code("""
event_counts = (
    event_classification
    .groupby(["regionid", "event_class"])
    .agg(intervals=("settlementdate", "count"))
    .reset_index()
)

fig = px.bar(
    event_counts,
    x="event_class",
    y="intervals",
    color="regionid",
    barmode="group",
    title="Event Classification Counts By Region"
)
fig.update_layout(xaxis_title="", yaxis_title="Dispatch intervals")
save_chart(fig, "09_event_classification_counts.html")
fig.show()
"""),
    md("""
## Step 8: Decision Intelligence Priority View

### What we are doing
We are visualising decision priority by event class and region.

### Why it matters
This chart connects market classification to analyst action.
"""),
    code("""
priority_counts = (
    decision_recommendations
    .groupby(["regionid", "event_class", "priority"])
    .agg(intervals=("settlementdate", "count"))
    .reset_index()
)

fig = px.bar(
    priority_counts,
    x="event_class",
    y="intervals",
    color="priority",
    facet_row="regionid",
    title="Decision Intelligence Priority By Event Class"
)
fig.update_layout(height=850, xaxis_title="", yaxis_title="Dispatch intervals")
save_chart(fig, "09_decision_priority_by_event_class.html")
fig.show()
"""),
    md("""
## Step 9: Save Chart Inventory

### What we are doing
We are creating a small CSV inventory of generated chart files.

### Why it matters
This makes it easier to reference charts in the README, dashboard, or analyst report.
"""),
    code("""
chart_inventory = pd.DataFrame({
    "chart_file": sorted([path.name for path in CHART_DIR.glob("09_*.html")])
})

chart_inventory_output = OUTPUT_DIR / "09_plotly_chart_inventory.csv"
chart_inventory.to_csv(chart_inventory_output, index=False)

print("Saved:", chart_inventory_output)
chart_inventory
"""),
    md("""
## Notebook 09 Summary

| Step | What we did | Why it matters for NEM analysis | Output / Result |
|---|---|---|---|
| 1 | Loaded market, ramping, event, and decision tables | Brings the project narrative into one visual pack | Input CSVs loaded |
| 2 | Created RRP event classification chart | Shows price outcomes by event driver | `09_rrp_by_event_classification.html` |
| 3 | Created demand versus available generation chart | Shows supply adequacy visually | `09_available_generation_vs_demand.html` |
| 4 | Created supply margin chart | Highlights scarcity and stress conditions | `09_supply_margin_by_event_class.html` |
| 5 | Created top ramping units chart | Identifies flexible or variable DUIDs | `09_top_generator_ramping_units.html` |
| 6 | Created event count chart | Summarises event classes by region | `09_event_classification_counts.html` |
| 7 | Created decision priority chart | Links market events to analyst action | `09_decision_priority_by_event_class.html` |
| 8 | Saved chart inventory | Supports README and dashboard references | `09_plotly_chart_inventory.csv` |

### Conceptual takeaway

Notebook 09 turns the analytical outputs into an interactive visual story.

The goal is not only to produce charts, but to help users see how generator behaviour, supply adequacy, event classification, and decision intelligence connect.
"""),
    md("""
## Analyst Note

Notebook 09 created the interactive Plotly visualisation pack for the project.

The charts support the GitHub README, dashboard structure, Power BI design, and final analyst report by showing price events, supply margins, generator ramping, event classifications, and decision priorities.
"""),
])


def write_notebook(filename: str, notebook: dict) -> None:
    NOTEBOOK_DIR.mkdir(parents=True, exist_ok=True)
    path = NOTEBOOK_DIR / filename
    path.write_text(json.dumps(notebook, indent=2), encoding="utf-8")
    print("Wrote:", path)


def main() -> None:
    write_notebook("07_event_classification.ipynb", NOTEBOOK_07)
    write_notebook("08_decision_intelligence.ipynb", NOTEBOOK_08)
    write_notebook("09_plotly_visualisation_pack.ipynb", NOTEBOOK_09)


if __name__ == "__main__":
    main()
