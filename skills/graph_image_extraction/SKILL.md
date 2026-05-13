# Graph Image Extraction Skill

Purpose: instruct Qwen2.5-VL to extract only visible network graph facts from PNG/JPEG network graph images.

Rules:
- Return JSON only.
- Extract node labels, visible colors, directed edges, arrow direction, and visible amount labels.
- Normalize visible amount text where possible.
- If direction is uncertain, set `direction_confidence` below `0.6`.
- Do not infer AML, AFC, fraud, sanctions, suspicious activity, typology, intent, or risk.
- Do not add timestamps, customer attributes, geography, device, IP, or channel data unless visibly present.

Contract:
- human-readable contract: `graph_image_extraction_contract.md`
- machine-readable schema contract: `graph_schema_contract.schema.json`

The harness validates both `graph_schema.json` and required `extraction_prompt.md` instruction fragments before model execution.
