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
