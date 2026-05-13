Extract only visible network graph facts.
Return JSON only.
Do not infer AML, AFC, fraud, sanctions, suspicious activity, or typology.

Return:
- case_id
- nodes: id, label, visible_color, role_hint_from_label, confidence
- edges: source, target, amount_text, amount_value, currency, visible_color, direction_confidence, amount_confidence
- visual_signals
- extraction_uncertainties

Follow arrowheads for edge direction. If edge direction is uncertain, use direction_confidence below 0.6.
Normalize visible amounts, for example "$10.0k" becomes 10000.0 and currency "USD".
