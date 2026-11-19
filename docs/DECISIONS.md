# Decisions

One line per methodological decision: what you chose, why, and what it changed.
Agents append here via the `/new-feature` skill; you append here by hand.

- Exclude `casual`, `registered`: they sum to `cnt` exactly. Leaky model R^2 1.000 -> honest ridge 0.583.
- Exclude `cnt_2d_bfr`: a shipped 2-day lag we cannot test the alignment of. Build our own lags instead.
- Exclude `instant`, `yr`, `days_since_2011`: time indexes let a tree predict a flat constant past 2011 and a linear model extrapolate a trend we have no grounds for.
- Split 2011 / H1 2012 / H2 2012 by date. Test set touched once, after all feature work.
- Report mean and persistence baselines with every score. Persistence (test R^2 0.510, MAE 840) is within 0.07 R^2 of ridge and beats it on MAE; that caveat goes in the report.
- 2026-11-18: Chose hosted Claude Sonnet instead of Ollama for agent execution. Preserved the starter hooks, permissions, and verification workflow; will identify the model in REPORT.md Attribution.
- 2026-11-18: I tested cnt_lag_2, the count from two calendar days earlier. This information is available before prediction day d and does not introduce target leakage. Ridge validation R² decreased from 0.6475 to 0.6453, while HGB improved from 0.2185 to 0.2481. However, HGB still performed worse than the persistence baseline (0.4507) and Ridge remained the strongest model but worsened slightly. I decide to reject cnt_lag_2 as a model input. This is because Ridge is still the strongest model, so the feature doesn't provide any meaningful improvement. The implementation of it and test will remain for verification.
- 2026-11-18: The training command displayed test metrics during experimentation. My feature-selection decision was based on validation results, not test results.
- 2026-11-18: I chose to exclude season, mnth, and weekday as redundant calendar inputs because the pipeline already derives calendar features from dteday. I classified them separately from target leakage and preserved the existing model features.
- 2026-11-18: Updated CLAUDE.md to name `/seed-fault` as the project's custom fault-injection skill, keeping all existing leakage, temporal-split, baseline, and style rules. Documented its first run in docs/SEEDED_FAULTS.md. This is a tooling and documentation change only; no modelling decision changed.
