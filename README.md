# Data Contracts and Observability Platform

A seven-day data engineering project that demonstrates how to detect
breaking data changes and monitor the quality of an orders dataset.

## Business problem

Changes to upstream data can break downstream reporting or cause
incorrect results. Delayed deliveries, unexpected volume changes, and
missing values can also affect analytics even when a pipeline succeeds.

## Project goals

- Define producer data contracts in YAML.
- Check proposed schema changes in GitHub Actions.
- Build tested dbt models in PostgreSQL.
- Validate data with Great Expectations.
- Monitor freshness, volume, and null rates.
- Capture supported lineage with OpenLineage.
- Test alerting and measure detection times using controlled scenarios.

## Planned technology

Python, PostgreSQL, Docker, dbt, Great Expectations, GitHub Actions,
OpenLineage, and Slack.

The project uses synthetic data and a local runtime simulation.

## Project status

Day 1: Project initialized. Implementation is in progress.
