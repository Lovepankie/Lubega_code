# ADR-002: 15-Minute Aggregation Window Instead of Raw 10-Second Data

## Status
Accepted

## Context
The meter is polled every 10 seconds. At this rate, storing every reading would produce ~8,640 rows/day per meter — ~3.15M rows/year — and ~25 MB/day of CSV data per meter.

Two storage strategies were considered:

1. **Store every 10-second reading** — maximum temporal resolution, but extreme disk usage, complex log rotation, and noisy data for ML inference
2. **Buffer 10-second readings and write one 15-minute aggregate row** — 96 rows/day, ~10-15 KB/day, averaging reduces noise, aligns with utility billing cadence

## Decision
Buffer 10-second readings in `FifteenMinuteAggregator` and write one averaged row per 15 minutes. The ML model is trained and infers at the 15-minute granularity.

Energy accuracy is preserved via trapezoidal integration in `energy_calc.py` over the 15-minute window, avoiding reliance on the meter's cumulative register alone for per-phase billing.

## Consequences

**Better:**
- 99% disk reduction vs. raw logging (96 vs. 8,640 rows/day)
- Log files last ~17 months before rotation (50,000 row limit)
- Averaging reduces transient noise — theft bypass patterns are structural, not momentary
- 15-min granularity matches most East African utility billing cycles
- CSV files are small enough to attach to email for offline analysis

**Worse:**
- Theft that occurs and is corrected within a single 15-minute window may be missed (attacker bypasses and removes in <15 min)
- Loss of sub-15-minute temporal detail for anomaly forensics
- `detect.py` inference latency is up to 15 minutes (one window) — not second-by-second

**Accepted risk:** Sub-15-minute bypass-and-remove theft is technically possible but operationally uncommon. The 15-minute window is adequate for the target scenario (sustained tampering to reduce bills over days/weeks). If sub-minute detection is required in the future, a parallel raw-data inference path can be added without changing the aggregated CSV pipeline.
