# Project 03 Learning And Interview Report

# NEM Generator Behaviour & Market Response Intelligence System

## 1. Project In One Sentence

This project analyses how generators in the Australian National Electricity Market respond to changing market conditions, especially price spikes, negative prices, volatility, supply tightness, and ramping periods.

In simple words:

> I used NEM dispatch data to understand what generators were doing when the market became stressed.

## 2. Why This Project Matters

Electricity prices in the NEM can change quickly because supply and demand must balance in real time.

When prices spike, fall below zero, or become volatile, a market analyst wants to know:

- Was supply tight?
- Was demand high?
- Were generators ramping up or down?
- Did available generation provide enough buffer?
- Were many units moving at the same time?
- Was the event caused by one clear driver or multiple drivers?

This project helps answer those questions using operational dispatch data.

The aim is not only to create charts. The aim is to convert raw market data into explanation and decision intelligence.

## 3. Business Question

The main business question is:

> How do generators respond to changing market conditions in the NEM, and how do generation behaviour, supply adequacy, and ramping influence prices, volatility, and market risk?

This question is relevant for:

- energy market analysts
- traders
- asset operators
- energy modellers
- generation portfolio managers
- commercial analytics teams

## 4. Data Used

The project uses three core NEM dispatch datasets loaded into PostgreSQL.

| Dataset | PostgreSQL Table | Why It Is Used |
|---|---|---|
| DISPATCHPRICE | `raw.dispatch_price` | Provides regional RRP, used for price spikes, negative prices, and volatility |
| DISPATCHREGIONSUM | `raw.dispatch_regionsum` | Provides demand, available generation, and net interchange |
| DISPATCH_UNIT_SCADA | `raw.dispatch_unit_scada` | Provides DUID-level generator output |

The project focuses on:

| Item | Value |
|---|---|
| Date range | 2026-02-01 to 2026-03-01 |
| Regions | NSW1 and VIC1 |
| Dispatch interval | 5 minutes |
| Main toolset | Python, pandas, PostgreSQL, Plotly |

Bid data is not used yet. That is intentional.

This project focuses on physical generator behaviour, not bidding intent.

## 5. Important Data Decision

Before analysing SCADA, the project inspects the actual database schema of:

```text
raw.dispatch_unit_scada
```

The actual columns found were:

```text
settlementdate
duid
scadavalue
lastchanged
raw_source_file
raw_table_name
```

Important point:

> The SCADA table did not contain an `intervention` column, so the project does not filter SCADA by intervention.

Intervention filtering is applied to:

```text
dispatch_price
dispatch_regionsum
```

This is a strong interview point because it shows that the logic was adapted to the actual database schema instead of assuming the table structure.

## 6. Overall Workflow

The project follows this workflow:

```text
PostgreSQL extraction
→ data cleaning
→ feature engineering
→ generation mix analysis
→ generator ramping analysis
→ supply adequacy analysis
→ generator response to price events
→ event classification
→ decision intelligence
→ Plotly visualisations
```

The simple version is:

```text
Data → Features → Analysis → Classification → Recommendations
```

That is the version to remember for interviews.

## 7. Notebook Summary

| Notebook | Main Purpose | Simple Explanation |
|---|---|---|
| 01 | Data extraction and market context | Get clean price, demand, available generation, and SCADA data |
| 02 | Generator market feature engineering | Create market and generator features |
| 03 | Generation mix analysis | Compare generation behaviour across market conditions |
| 04 | Generator ramping analysis | Identify which DUIDs changed output most rapidly |
| 05 | Supply adequacy analysis | Analyse supply margin and tight supply periods |
| 06 | Generator response to price events | Check what generators did during price spikes, negative prices, volatility, and stress |
| 07 | Event classification | Classify intervals into event driver types |
| 08 | Decision intelligence | Convert events into recommendations, risks, and confidence |
| 09 | Plotly visualisation pack | Create interactive charts |

## 8. Notebook 01: Data Extraction And Generator Market Context

### What This Notebook Does

Notebook 01 connects to PostgreSQL and extracts:

- regional price data
- regional demand and available generation data
- DUID-level SCADA output

It creates two clean base tables:

```text
01_base_generator_market_context.csv
01_scada_unit_output_clean.csv
```

### Why It Matters

The rest of the project depends on clean dispatch interval data.

If the data has duplicate intervals, missing timestamps, or unclean SCADA values, the ramping analysis could become misleading.

### Main Cleaning Steps

For price and region summary:

- convert `settlementdate` to timestamp
- standardise `regionid`
- convert numeric columns
- filter intervention records
- remove duplicate region-interval rows

For SCADA:

- convert `settlementdate` to timestamp
- standardise `duid`
- convert `scadavalue` to numeric
- remove missing DUID or SCADA records
- remove duplicate DUID-interval rows

### Key Concept

Notebook 01 answers:

> Do we have clean, aligned data to begin generator behaviour analysis?

## 9. Notebook 02: Generator Market Feature Engineering

### What This Notebook Does

Notebook 02 creates the main analytical features.

It uses:

```text
01_base_generator_market_context.csv
01_scada_unit_output_clean.csv
```

### Market Features Created

| Feature | Meaning |
|---|---|
| `supply_margin` | Available generation minus demand |
| `supply_margin_pct` | Supply margin divided by demand |
| `price_spike_flag` | RRP greater than $300/MWh |
| `negative_price_flag` | RRP below $0/MWh |
| `high_price_flag` | RRP greater than $100/MWh |
| `price_change` | Change in RRP from previous interval |
| `rolling_rrp_volatility_1h` | One-hour rolling price volatility |
| `volatility_flag` | High volatility interval |
| `hour`, `weekday`, `is_weekend` | Time features |

### Generator Features Created

| Feature | Meaning |
|---|---|
| `generation_change` | Change in DUID output from previous interval |
| `generation_ramp_rate` | 5-minute change converted to MW/hour proxy |
| `rolling_generation_avg` | One-hour rolling average output |
| `generator_utilisation_proxy` | Output divided by observed maximum output |
| `absolute_generation_change` | Absolute MW movement |
| `rapid_ramp_flag` | Output movement above DUID's 95th percentile |

### Key Concept: Supply Margin

```text
supply_margin = availablegeneration - totaldemand
```

If supply margin is low, the market has less spare available generation above demand.

This can increase scarcity pricing risk.

### Key Concept: Generator Ramping

```text
generation_change = current output - previous output
```

This tells us whether a generator increased or decreased output.

The ramp rate normalises this into a MW/hour proxy:

```text
generation_ramp_rate = generation_change / (5 / 60)
```

### Key Concept: Utilisation Proxy

The project does not yet use true registered capacity.

So it creates:

```text
generator_utilisation_proxy = scadavalue / observed maximum scadavalue
```

Important limitation:

> This is not true capacity utilisation. It is only an observed output proxy.

### Main Output

The most important output is:

```text
02_generator_market_features.csv
```

This is the main table used in later notebooks.

## 10. Notebook 03: Generation Mix Analysis

### What This Notebook Does

Notebook 03 compares aggregate generation behaviour across different market conditions:

- normal intervals
- high-price intervals
- price spikes
- negative prices
- high volatility

### Why It Matters

Prices should not be analysed alone.

This notebook asks:

> Did generation output, demand, supply margin, or ramping look different during price events?

### Key Analysis

The notebook creates market condition labels and compares:

- average RRP
- average demand
- average available generation
- average supply margin
- total generation output
- aggregate ramping
- rapid ramping units

### Key Concept

Notebook 03 moves from feature creation to market interpretation.

It helps explain whether price outcomes are associated with different generation and supply conditions.

## 11. Notebook 04: Generator Ramping Analysis

### What This Notebook Does

Notebook 04 analyses DUID-level ramping behaviour.

It identifies which generators changed output most rapidly.

### Why It Matters

In electricity markets, flexibility matters.

A generator that can change output quickly may help respond to:

- price spikes
- demand ramps
- volatility
- tight supply
- evening peak periods

### Key Metrics

| Metric | Meaning |
|---|---|
| average output | Typical output level |
| max output | Highest observed output |
| average absolute ramp | Average output movement |
| p95 absolute ramp | Material high-end movement |
| max absolute ramp | Largest observed movement |
| rapid ramping intervals | Number of intervals flagged as rapid ramping |

### Why Use 95th Percentile Ramp?

The 95th percentile helps identify material ramping behaviour without relying only on one extreme outlier.

### Evening Ramp Window

The notebook also analyses:

```text
16:00 to 20:59
```

This period is important because solar output usually declines while demand can remain high.

### Key Concept

Notebook 04 answers:

> Which generators were most flexible or most variable?

## 12. Notebook 05: Supply Adequacy Analysis

### What This Notebook Does

Notebook 05 focuses on whether available generation was sufficient relative to demand.

### Why It Matters

Supply adequacy is one of the most important drivers of scarcity risk.

If supply margin is low, prices can become more sensitive to:

- generator outages
- renewable reductions
- interconnector changes
- ramping constraints

### Supply Condition Labels

The notebook classifies supply conditions:

| Label | Rule |
|---|---|
| Very Tight Supply | supply margin percentage below 10% |
| Tight Supply | below 15% |
| Moderate Supply Buffer | below 25% |
| Comfortable Supply Buffer | 25% or above |

### Key Concept

Notebook 05 answers:

> Were high prices or volatility associated with tight supply margins?

## 13. Notebook 06: Generator Response To Price Events

### What This Notebook Does

Notebook 06 connects DUID-level generator behaviour to market events.

It asks what generators were doing during:

- price spikes
- high prices
- negative prices
- volatility
- supply stress

### Why It Matters

This is where the project becomes very market-relevant.

Instead of only saying:

> Price spiked.

The project asks:

> Which generators moved during the spike?

### Event Type Labels

The notebook creates:

- Price Spike
- Negative Price
- Supply Stress
- High Volatility
- High Price
- Normal

### Key Outputs

| Output | Purpose |
|---|---|
| `06_generator_response_by_event_type.csv` | Summarises each DUID by event type |
| `06_top_price_spike_responders.csv` | Identifies units responding during price spikes |
| `06_negative_price_generator_behaviour.csv` | Shows output during negative prices |
| `06_volatility_response_summary.csv` | Shows generator movement during volatility |
| `06_event_interval_generator_response.csv` | Drill-through table for event intervals |

### Key Concept

Notebook 06 answers:

> Which generators responded during important market conditions?

## 14. Notebook 07: Event Classification

### What This Notebook Does

Notebook 07 classifies each market interval into event driver types.

### Event Classes

| Event Class | Meaning |
|---|---|
| Supply Tightness Event | Supply margin is tight relative to demand |
| Generator Ramping Event | Aggregate generator movement is elevated |
| High Volatility Event | Price volatility is elevated |
| Oversupply Event | Negative price and healthy supply buffer |
| Renewable Dominance Event | Negative price with high aggregate output proxy |
| Mixed Driver Event | Multiple drivers active |
| Normal Dispatch Interval | No major event signal |

### Why It Matters

Event classification turns data into market narrative.

It helps explain what kind of event occurred, not just that an event occurred.

### Important Limitation

Renewable dominance is only a proxy because fuel type mapping has not been added yet.

The project can say:

> This looks consistent with renewable-led oversupply.

But it should not say:

> This was definitely caused by renewables.

## 15. Notebook 08: Decision Intelligence

### What This Notebook Does

Notebook 08 converts event classes into decision-ready recommendations.

For each event, it creates:

- Market Situation
- Insight
- Recommendation
- Risk
- Confidence
- Priority

### Example

For a supply tightness event:

| Field | Example |
|---|---|
| Market Situation | Supply margin tightening |
| Insight | Available generation buffer is low relative to demand |
| Recommendation | Monitor scarcity pricing risk |
| Risk | Outage or renewable reduction could amplify prices |
| Confidence | Medium-High |
| Priority | High |

### Why It Matters

This notebook is what makes the project business-facing.

It turns analysis into practical market commentary.

### Key Concept

Notebook 08 answers:

> What should a market analyst or trader do with this information?

## 16. Notebook 09: Plotly Visualisation Pack

### What This Notebook Does

Notebook 09 creates interactive HTML charts.

### Charts Created

- RRP by event classification
- available generation versus demand
- supply margin by event class
- top generator ramping units
- event classification counts
- decision priority by event class

### Why It Matters

Charts help communicate the project clearly in:

- GitHub README
- portfolio presentation
- Power BI dashboard
- interview discussion
- analyst report

## 17. Main Features Explained Simply

| Feature | Simple Meaning | Why It Matters |
|---|---|---|
| `rrp` | Regional price | Shows market outcome |
| `totaldemand` | Regional demand | Higher demand can tighten supply |
| `availablegeneration` | Available regional generation | Shows available supply capability |
| `netinterchange` | Net imports or exports | Helps understand regional balance |
| `supply_margin` | Available generation minus demand | Key scarcity risk signal |
| `supply_margin_pct` | Supply margin relative to demand | Allows comparison across regions |
| `price_spike_flag` | RRP above $300/MWh | Identifies high price events |
| `negative_price_flag` | RRP below $0/MWh | Identifies oversupply or inflexible generation conditions |
| `volatility_flag` | High rolling price volatility | Identifies unstable price periods |
| `generation_change` | DUID output change | Shows generator response |
| `generation_ramp_rate` | Output change as MW/hour proxy | Compares speed of response |
| `rapid_ramp_flag` | Unusually high movement for that DUID | Identifies material ramping |
| `event_class` | Classified market driver | Converts features into explanation |

## 18. How To Explain This Project In An Interview

Use this answer:

> This project is a NEM generator behaviour and market response intelligence system. I used PostgreSQL and Python to analyse February 2026 dispatch data for NSW1 and VIC1. The core datasets were dispatch price, regional demand and available generation, and unit SCADA output. After cleaning and aligning the data to 5-minute intervals, I created features such as supply margin, price spike flags, volatility, generator output change, ramp rate, utilisation proxy, and rapid ramping flags. Then I analysed how generation and ramping behaviour changed during price spikes, negative prices, volatile periods, and tight supply intervals. The final layer classifies events into supply tightness, generator ramping, high volatility, oversupply, renewable dominance proxy, or mixed driver events, and turns them into decision-ready recommendations for market analysts and traders.

## 19. How To Explain The Technical Workflow

Say:

> I first extracted price, region summary, and SCADA data from PostgreSQL. I cleaned timestamps, intervention flags, duplicates, missing values, and aligned everything to dispatch intervals. Then I engineered market features and DUID-level generator features. Since price and demand are regional but SCADA is unit-level, I created both DUID-level outputs and aggregate interval-level generator summaries. This allowed me to analyse individual generator ramping as well as regional market conditions.

## 20. How To Explain The Market Value

Say:

> The value of the project is that it moves from raw dispatch data to market explanation. It does not just show that price spiked. It helps identify whether the spike was associated with tight supply, generator ramping, volatility, oversupply, or mixed drivers.

## 21. How To Explain Limitations

Be honest and professional:

> The current version does not include bid data, so it does not explain bidding intent. It also does not yet include DUID fuel mapping, so renewable dominance is only a proxy. The next extension would add bid bands, fuel type mapping, storage classification, and network constraint context.

This is a strong answer because it shows maturity.

You understand what your model can and cannot claim.

## 22. Interview Questions And Answers

### Question: Why did you use SCADA data?

Answer:

> SCADA gives DUID-level generator output at dispatch interval level. It allows me to see how individual units changed output during price spikes, negative prices, volatility, and supply stress.

### Question: Why did you create supply margin?

Answer:

> Supply margin measures the available generation buffer above demand. A low margin can indicate tighter market conditions and greater scarcity pricing risk.

### Question: Why did you use ramp rate?

Answer:

> Ramping shows how quickly generator output changed between dispatch intervals. It helps identify flexible units and understand supply-side response during market events.

### Question: Why is price volatility important?

Answer:

> Volatility shows unstable market conditions. A price spike is one event, but volatility tells us whether prices were moving sharply over the recent period.

### Question: Why not use bid data?

Answer:

> This version focuses on physical generator behaviour using SCADA. Bid data is the next extension because bidding intent is a separate analytical layer.

### Question: What was the hardest part?

Answer:

> The main challenge was connecting regional market data with DUID-level SCADA. I solved this by creating DUID-level generator features and aggregate dispatch interval summaries that could be joined to the regional market table.

### Question: What would you improve next?

Answer:

> I would add DUID fuel mapping, bid data, storage classification, and constraint context. That would allow me to separate physical response, bidding behaviour, technology type, and network effects.

## 23. What You Should Remember

Do not try to memorise every notebook.

Remember this:

```text
Notebook 01 = clean data
Notebook 02 = create features
Notebook 03 = generation mix
Notebook 04 = ramping
Notebook 05 = supply adequacy
Notebook 06 = generator response to events
Notebook 07 = event classification
Notebook 08 = recommendations
Notebook 09 = charts
```

And remember the core story:

> I built a Python and PostgreSQL market intelligence system that explains how NEM generators respond to price events, volatility, supply tightness, and ramping conditions.

## 24. Final Confidence Statement

If you are explaining this project, you do not need to sound like you know everything about the NEM.

You need to show that you can:

- extract operational market data
- clean it properly
- engineer meaningful features
- connect generator behaviour to market outcomes
- explain uncertainty and limitations
- turn analysis into business recommendations

That is exactly what this project demonstrates.
