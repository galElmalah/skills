# Catalog Project

Small Node project with intentionally bad production code paths.

Use it to test `autoresearch-create` against a latency-style metric.

## Goal

Create a cheap benchmark with the skill, then reduce runtime without changing observable behavior.

## Benchmark Setup

This project does not ship a benchmark harness.

Use `autoresearch-create` to define and scaffold the first cheap benchmark, then freeze it before you start mutating the catalog logic.

Suggested scalar metric once the harness exists:

- metric: `total_duration_ms`
- direction: `min`

## Intentionally Inefficient Areas

- repeated deep cloning of product metadata
- repeated full-list scans during tokenized search
- nested product x event scans for trending scores
- nested product x order scans for revenue aggregation
- repeated `find` lookups when ranking recommendations
- repeated bundle analysis across all orders for every candidate

## Suggested Mutable Scope

- `src/catalog.js`

## Suggested Frozen Scope

- `src/data.js`
- the benchmark harness created during setup

The project is small enough to scaffold quickly, but rich enough that obvious improvements should show up once the skill creates a usable benchmark.
