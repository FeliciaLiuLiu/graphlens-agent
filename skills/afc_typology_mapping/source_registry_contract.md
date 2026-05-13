# Source Registry Skill Contract

This document defines the boundary between the typology source registry skill file and the Python harness.

## Ownership Boundary

- SME-owned:
  - human-readable descriptions for registered evidence sources

- Engineering-owned:
  - required source ids
  - evidence source id emission in runtime output
  - validation and traceability enforcement

## Files

- Skill definition: `source_registry.yaml`
- Machine contract: `source_registry.schema.json`

## Required Structure

`source_registry.yaml` must define:

- `sources`

`sources` must be an array of objects with:

- `id`
- `description`

## Required Source IDs

The harness currently requires these source ids to exist:

- `internal_graph_features`
- `visible_graph_image`

These ids are engineering-owned because runtime evidence output depends on them. SME can change the descriptions, but not remove or rename the required ids.

## Semantic Rules

- source ids must be unique
- descriptions must be non-empty
- required ids must be present

Invalid source registries should fail early during loading.
