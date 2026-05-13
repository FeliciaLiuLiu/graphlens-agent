from __future__ import annotations

import io
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from afc_network_narrative.harness.app.skill_loader import load_narrative_policy
from afc_network_narrative.harness.schemas.afc_output_schema import AFCNarrativeOutput

PAGE_WIDTH = 612
PAGE_HEIGHT = 792
LEFT_MARGIN = 54
RIGHT_MARGIN = 54
TOP_MARGIN = 54
BOTTOM_MARGIN = 54


@dataclass
class ReportLine:
    text: str
    font_size: int
    leading: int


def write_report_pdf(
    output: AFCNarrativeOutput | dict[str, Any],
    pdf_path: str | Path,
    *,
    input_name: str | None = None,
) -> Path:
    path = Path(pdf_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(build_report_pdf_bytes(output, input_name=input_name))
    return path


def build_report_pdf_bytes(
    output: AFCNarrativeOutput | dict[str, Any],
    *,
    input_name: str | None = None,
) -> bytes:
    payload = output.to_dict() if isinstance(output, AFCNarrativeOutput) else output
    policy = load_narrative_policy()["report_pdf"]
    lines = build_report_lines(payload, policy, input_name=input_name)
    pages = paginate_lines(lines)
    return build_pdf_document(pages)


def build_report_lines(
    payload: dict[str, Any],
    report_policy: dict[str, Any],
    *,
    input_name: str | None = None,
) -> list[ReportLine]:
    graph_summary = payload["graph_summary"]
    section_titles = report_policy["section_titles"]
    summary_templates = report_policy["summary_item_templates"]
    lines: list[ReportLine] = []

    lines.append(ReportLine(report_policy["title"], 18, 24))
    lines.append(ReportLine(report_policy["subtitle_template"].format(case_id=graph_summary.get("case_id", "unknown_case")), 11, 16))
    if input_name:
        lines.append(ReportLine(report_policy["input_reference_template"].format(input_name=input_name), 10, 14))
    lines.append(ReportLine("", 10, 12))

    lines.extend(render_section(section_titles["narrative"], [payload["narrative"]]))

    graph_summary_lines = [
        summary_templates["node_count"].format(value=graph_summary["node_count"]),
        summary_templates["edge_count"].format(value=graph_summary["edge_count"]),
        summary_templates["repeated_amount_score"].format(value=graph_summary["repeated_amount_score"]),
        summary_templates["repeated_amount_value"].format(value=graph_summary["repeated_amount_value"]),
        summary_templates["overall_extraction_confidence"].format(value=graph_summary["overall_extraction_confidence"]),
    ]
    lines.extend(render_section(section_titles["graph_summary"], graph_summary_lines, bullet=True))

    typology_lines = build_typology_lines(payload["detected_typologies"], report_policy)
    lines.extend(render_section(section_titles["detected_typologies"], typology_lines or ["No configured typology matched the graph structure."], bullet=True))

    alert_boost = payload["alert_boost"]
    boost_text = report_policy["alert_boost_template"].format(
        priority_band=alert_boost["priority_band"],
        score=alert_boost["score"],
        explanation=alert_boost["explanation"],
    )
    lines.extend(render_section(section_titles["alert_boost"], [boost_text]))

    lines.extend(render_section(section_titles["recommended_steps"], payload["recommended_investigation_steps"], bullet=True))
    lines.extend(render_section(section_titles["limitations"], payload["limitations"], bullet=True))
    evidence_lines = build_evidence_lines(payload["evidence"], report_policy)
    lines.extend(render_section(section_titles["evidence"], evidence_lines, bullet=True))
    return lines


def build_typology_lines(typologies: list[dict[str, Any]], report_policy: dict[str, Any]) -> list[str]:
    template = report_policy["typology_line_template"]
    lines = []
    for item in typologies:
        lines.append(
            template.format(
                name=item["name"],
                confidence=item["confidence"],
                interpretation=item["afc_interpretation"],
            )
        )
    return lines


def build_evidence_lines(evidence: list[dict[str, Any]], report_policy: dict[str, Any]) -> list[str]:
    max_items = int(report_policy["max_evidence_items"])
    template = report_policy["evidence_line_template"]
    lines: list[str] = []
    for item in evidence[:max_items]:
        label, details = evidence_label_and_details(item)
        lines.append(template.format(label=label, details=details))
    return lines


def evidence_label_and_details(item: dict[str, Any]) -> tuple[str, str]:
    if item.get("type") == "edge":
        amount = item.get("amount_text") or item.get("amount_value") or "unknown amount"
        return (
            "Visible graph image",
            f"{item['source']} -> {item['target']} amount {amount} direction_confidence={item['direction_confidence']}",
        )
    metric = item.get("metric", item.get("type", "evidence"))
    node_id = item.get("node_id")
    value = item.get("value")
    details = f"{metric}={value}"
    if item.get("amount_value") is not None:
        details += f" at amount {item['amount_value']}"
    if node_id:
        details += f" on node {node_id}"
    return ("Internal graph features", details)


def render_section(title: str, items: list[str], *, bullet: bool = False) -> list[ReportLine]:
    lines = [ReportLine(title, 13, 18)]
    if not items:
        lines.append(ReportLine("None.", 10, 14))
    else:
        for item in items:
            prefix = "- " if bullet else ""
            lines.extend(wrap_report_text(prefix + normalize_text(item), font_size=10, leading=14))
    lines.append(ReportLine("", 10, 12))
    return lines


def wrap_report_text(text: str, *, font_size: int, leading: int) -> list[ReportLine]:
    if not text:
        return [ReportLine("", font_size, leading)]
    width = max(20, int((PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN) / (font_size * 0.55)))
    wrapped = textwrap.wrap(text, width=width, replace_whitespace=False, drop_whitespace=False)
    return [ReportLine(line.rstrip(), font_size, leading) for line in wrapped] or [ReportLine("", font_size, leading)]


def paginate_lines(lines: list[ReportLine]) -> list[list[ReportLine]]:
    pages: list[list[ReportLine]] = []
    current: list[ReportLine] = []
    remaining_height = PAGE_HEIGHT - TOP_MARGIN - BOTTOM_MARGIN
    for line in lines:
        if line.leading > remaining_height and current:
            pages.append(current)
            current = []
            remaining_height = PAGE_HEIGHT - TOP_MARGIN - BOTTOM_MARGIN
        current.append(line)
        remaining_height -= line.leading
    if current:
        pages.append(current)
    return pages or [[ReportLine("Empty report.", 10, 14)]]


def build_pdf_document(pages: list[list[ReportLine]]) -> bytes:
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
    except ImportError as exc:
        raise RuntimeError("reportlab is required for PDF report generation. Install dependencies first.") from exc

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter, pageCompression=0)
    pdf.setTitle("AFC Network Narrative Report")

    for page_lines in pages:
        y = PAGE_HEIGHT - TOP_MARGIN
        for line in page_lines:
            pdf.setFont("Helvetica", line.font_size)
            pdf.drawString(LEFT_MARGIN, y, normalize_text(line.text))
            y -= line.leading
        pdf.showPage()

    pdf.save()
    return buffer.getvalue()


def normalize_text(text: Any) -> str:
    return str(text).replace("\n", " ").encode("latin-1", errors="replace").decode("latin-1")
