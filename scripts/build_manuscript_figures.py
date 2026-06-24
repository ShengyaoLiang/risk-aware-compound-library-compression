"""Generate small vector PDF figures for the manuscript."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PAPER_ROOT = Path(__file__).resolve().parents[1]
FIGURE_DIR = PAPER_ROOT / "manuscript" / "figures"


def _dependencies() -> tuple[Any, Any, Any, Any, Any]:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import landscape, letter
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import inch
    except ImportError as exc:
        raise RuntimeError(
            "Figure generation requires reportlab. Run it with the stells backend Docker image."
        ) from exc
    return colors, landscape, letter, canvas, inch


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def draw_wrapped_lines(c: Any, x: float, y: float, lines: list[str], leading: float) -> None:
    text = c.beginText(x, y)
    text.setLeading(leading)
    for line in lines:
        text.textLine(line)
    c.drawText(text)


def draw_box(
    c: Any,
    colors: Any,
    x: float,
    y: float,
    w: float,
    h: float,
    title: str,
    body_lines: list[str],
) -> None:
    c.setStrokeColor(colors.HexColor("#355070"))
    c.setFillColor(colors.HexColor("#EEF3F8"))
    c.roundRect(x, y, w, h, 8, fill=1, stroke=1)
    c.setFillColor(colors.HexColor("#172033"))
    c.setFont("Helvetica-Bold", 8.7)
    draw_wrapped_lines(c, x + 10, y + h - 18, title.split("\n"), 10)
    c.setFont("Helvetica", 8)
    draw_wrapped_lines(c, x + 10, y + h - 43, body_lines, 9.5)


def draw_arrow(c: Any, colors: Any, x1: float, y1: float, x2: float, y2: float) -> None:
    c.setStrokeColor(colors.HexColor("#566B7F"))
    c.setLineWidth(1.5)
    c.line(x1, y1, x2, y2)
    c.setFillColor(colors.HexColor("#566B7F"))
    c.circle(x2, y2, 3, fill=1, stroke=0)


def workflow_figure(path: Path) -> None:
    colors, _, _, canvas, inch = _dependencies()
    width, height = 9.8 * inch, 5.25 * inch
    c = canvas.Canvas(str(path), pagesize=(width, height))
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(colors.HexColor("#172033"))
    c.drawString(0.3 * inch, height - 0.35 * inch, "Risk-aware compound-library compression workflow")
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor("#4B5F73"))
    c.drawString(0.3 * inch, height - 0.55 * inch, "The system ranks libraries before downstream assays while preserving uncertainty and risk evidence.")

    boxes = [
        ("Input\nlibrary", ["SMILES upload", "format checks", "deduplication"], 0.35, 1.78),
        ("Activity\nproxy", ["Morgan fingerprint", "RDKit descriptors", "MLP score"], 2.18, 1.78),
        ("Uncertainty\nand domain", ["conformal interval", "applicability domain", "similarity evidence"], 4.01, 1.78),
        ("Risk\nlayer", ["ADMET alerts", "structural alerts", "hard/soft flags"], 5.84, 1.78),
        ("Candidate\nexport", ["Top 0.1%-20%", "CSV/XLSX tables", "molecule PDFs"], 7.67, 1.78),
    ]
    for title, body, xi, yi in boxes:
        draw_box(c, colors, xi * inch, yi * inch, 1.42 * inch, 1.18 * inch, title, body)
    for left, right in zip(boxes, boxes[1:]):
        draw_arrow(c, colors, (left[2] + 1.42) * inch, (left[3] + 0.58) * inch, right[2] * inch, (right[3] + 0.58) * inch)

    draw_box(
        c,
        colors,
        2.45 * inch,
        0.25 * inch,
        5.0 * inch,
        0.95 * inch,
        "Evaluation gates",
        [
            "internal validation -> temporal holdout",
            "overlap-controlled benchmark -> label-hidden replay",
        ],
    )
    c.showPage()
    c.save()


def results_figure(path: Path) -> None:
    colors, _, _, canvas, inch = _dependencies()
    stats = load_json(PAPER_ROOT / "results" / "statistical_results.json")
    bootstrap = stats["bootstrap"]
    data = [
        (
            "Internal",
            bootstrap["ChEMBL36 internal validation"],
            colors.HexColor("#2B6CB0"),
        ),
        (
            "Temporal",
            bootstrap["ChEMBL36 temporal holdout"],
            colors.HexColor("#2C7A7B"),
        ),
        (
            "BACE strict",
            bootstrap["BACE scaffold-disjoint"],
            colors.HexColor("#6B46C1"),
        ),
        (
            "EGFR replay",
            bootstrap["EGFR scaffold-disjoint replay"],
            colors.HexColor("#B7791F"),
        ),
    ]
    width, height = 9.2 * inch, 5.6 * inch
    c = canvas.Canvas(str(path), pagesize=(width, height))
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(colors.HexColor("#172033"))
    c.drawString(0.35 * inch, height - 0.35 * inch, "Top-1% enrichment summary")
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor("#4B5F73"))
    c.drawString(0.35 * inch, height - 0.55 * inch, "Bars show fixed-model enrichment; strict subsets include bootstrap uncertainty where available.")

    x0 = 0.7 * inch
    y0 = 0.8 * inch
    chart_w = 7.8 * inch
    chart_h = 3.6 * inch
    max_v = 3.0
    c.setStrokeColor(colors.HexColor("#AAB7C4"))
    c.line(x0, y0, x0 + chart_w, y0)
    c.line(x0, y0, x0, y0 + chart_h)
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#566B7F"))
    for tick in [0, 1, 2, 3]:
        y = y0 + chart_h * tick / max_v
        c.setStrokeColor(colors.HexColor("#D4DEE8"))
        c.line(x0, y, x0 + chart_w, y)
        c.setFillColor(colors.HexColor("#566B7F"))
        c.drawRightString(x0 - 6, y - 3, str(tick))

    bar_w = 0.85 * inch
    gap = 0.65 * inch
    for i, (label, result, color) in enumerate(data):
        value = result["point"]["ef_1"]
        x = x0 + 0.55 * inch + i * (bar_w + gap)
        h = chart_h * min(value, max_v) / max_v
        c.setFillColor(color)
        c.rect(x, y0, bar_w, h, fill=1, stroke=0)
        interval = result.get("intervals", {}).get("ef_1")
        label_y = y0 + h + 8
        if interval:
            low = max(0.0, float(interval["lower_95"]))
            high = min(max_v, float(interval["upper_95"]))
            y_low = y0 + chart_h * low / max_v
            y_high = y0 + chart_h * high / max_v
            label_y = y_high + 8
            x_mid = x + bar_w / 2
            c.setStrokeColor(colors.HexColor("#172033"))
            c.setLineWidth(1)
            c.line(x_mid, y_low, x_mid, y_high)
            c.line(x_mid - 5, y_low, x_mid + 5, y_low)
            c.line(x_mid - 5, y_high, x_mid + 5, y_high)
        c.setFillColor(colors.HexColor("#172033"))
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(x + bar_w / 2, label_y, f"{value:.2f}\u00d7")
        c.setFont("Helvetica", 8)
        c.drawCentredString(x + bar_w / 2, y0 - 16, label)

    c.setFillColor(colors.HexColor("#4B5F73"))
    c.setFont("Helvetica", 8)
    c.drawString(x0, 0.22 * inch, "BACE uses the scaffold-disjoint external subset; EGFR uses the scaffold-disjoint same-source replay subset.")
    c.showPage()
    c.save()


def virtual_batch_trend_figure(path: Path) -> None:
    colors, _, _, canvas, inch = _dependencies()
    stats = load_json(PAPER_ROOT / "results" / "statistical_results.json")
    series = [
        (
            "Internal validation",
            "ChEMBL36 internal validation",
            colors.HexColor("#2B6CB0"),
        ),
        (
            "Temporal holdout",
            "ChEMBL36 temporal holdout",
            colors.HexColor("#2C7A7B"),
        ),
        (
            "BACE strict",
            "BACE scaffold-disjoint",
            colors.HexColor("#6B46C1"),
        ),
    ]
    batch_sizes = [100, 500, 1000]

    width, height = 9.2 * inch, 5.6 * inch
    c = canvas.Canvas(str(path), pagesize=(width, height))
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(colors.HexColor("#172033"))
    c.drawString(0.35 * inch, height - 0.35 * inch, "Virtual-batch EF@1% trend")
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor("#4B5F73"))
    c.drawString(
        0.35 * inch,
        height - 0.55 * inch,
        "Means and seed-level standard deviations across five library-shuffle seeds.",
    )

    x0 = 0.85 * inch
    y0 = 0.9 * inch
    chart_w = 7.2 * inch
    chart_h = 3.55 * inch
    min_v = 1.7
    max_v = 2.85

    def x_pos(batch_size: int) -> float:
        inner_margin = 0.18 * inch
        usable_w = chart_w - 2 * inner_margin
        return x0 + inner_margin + usable_w * (
            batch_sizes.index(batch_size) / (len(batch_sizes) - 1)
        )

    def y_pos(value: float) -> float:
        return y0 + chart_h * ((value - min_v) / (max_v - min_v))

    def y_value(position: float) -> float:
        return min_v + (position - y0) * (max_v - min_v) / chart_h

    c.setStrokeColor(colors.HexColor("#AAB7C4"))
    c.line(x0, y0, x0 + chart_w, y0)
    c.line(x0, y0, x0, y0 + chart_h)
    c.setFont("Helvetica", 8)
    for tick in [1.8, 2.0, 2.2, 2.4, 2.6, 2.8]:
        y = y_pos(tick)
        c.setStrokeColor(colors.HexColor("#D4DEE8"))
        c.line(x0, y, x0 + chart_w, y)
        c.setFillColor(colors.HexColor("#566B7F"))
        c.drawRightString(x0 - 6, y - 3, f"{tick:.1f}")
    c.setFillColor(colors.HexColor("#566B7F"))
    for batch_size in batch_sizes:
        x = x_pos(batch_size)
        c.drawCentredString(x, y0 - 16, str(batch_size))
    c.drawString(x0 + chart_w / 2 - 0.35 * inch, y0 - 35, "Virtual batch size")
    c.saveState()
    c.translate(0.22 * inch, y0 + chart_h / 2 + 0.3 * inch)
    c.rotate(90)
    c.drawString(0, 0, "EF@1%")
    c.restoreState()

    for label, key, color in series:
        points: list[tuple[float, float, float]] = []
        for batch_size in batch_sizes:
            metrics = stats["virtual_batches"][key][str(batch_size)]["metrics"]["ef_1"]
            points.append((x_pos(batch_size), y_pos(metrics["mean"]), metrics["sd"]))

        c.setStrokeColor(color)
        c.setLineWidth(1.7)
        for left, right in zip(points, points[1:]):
            c.line(left[0], left[1], right[0], right[1])
        for x, y, sd in points:
            mean = y_value(y)
            y_low = y_pos(max(min_v, mean - sd))
            y_high = y_pos(min(max_v, mean + sd))
            c.line(x, y_low, x, y_high)
            c.line(x - 3, y_low, x + 3, y_low)
            c.line(x - 3, y_high, x + 3, y_high)
            c.setFillColor(color)
            c.circle(x, y, 3.4, fill=1, stroke=0)

    legend_x = x0 + chart_w - 1.55 * inch
    legend_y = y0 + chart_h - 0.1 * inch
    c.setFont("Helvetica", 8)
    for idx, (label, _, color) in enumerate(series):
        y = legend_y - idx * 0.18 * inch
        c.setFillColor(color)
        c.rect(legend_x, y - 4, 8, 8, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#172033"))
        c.drawString(legend_x + 13, y - 3, label)

    c.setFillColor(colors.HexColor("#4B5F73"))
    c.setFont("Helvetica", 8)
    c.drawString(
        x0,
        0.24 * inch,
        "BACE strict has one near-complete 1,000-size batch because the scaffold-disjoint subset has 962 molecules.",
    )
    c.showPage()
    c.save()


def main() -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    workflow_figure(FIGURE_DIR / "workflow.pdf")
    results_figure(FIGURE_DIR / "top1_enrichment.pdf")
    virtual_batch_trend_figure(FIGURE_DIR / "virtual_batch_trend.pdf")
    print(FIGURE_DIR / "workflow.pdf")
    print(FIGURE_DIR / "top1_enrichment.pdf")
    print(FIGURE_DIR / "virtual_batch_trend.pdf")


if __name__ == "__main__":
    main()
