# Prohibited Claims Skill Contract

This document defines the boundary between the prohibited claims skill file and the Python harness.

## Ownership Boundary

- SME-owned:
  - additional prohibited phrases
  - wording adjustments to prohibited phrases

- Engineering-owned:
  - baseline safety coverage
  - validation that critical prohibited claims remain present
  - runtime enforcement

## Files

- Skill definition: `prohibited_claims.yaml`
- Machine contract: `prohibited_claims.schema.json`

## Required Structure

`prohibited_claims.yaml` must define:

- `prohibited_claims`

This must be an array of non-empty strings.

## Required Baseline Claims

The harness requires these exact baseline phrases to remain present:

- `confirmed money laundering`
- `committed money laundering`
- `SAR required`

Additional prohibited phrases are allowed.

## Semantic Rules

- prohibited claims must be unique, case-insensitively
- required baseline claims must be present

Invalid prohibited-claims files should fail early during loading.
