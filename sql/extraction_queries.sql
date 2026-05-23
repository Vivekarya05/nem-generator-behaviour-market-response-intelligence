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
