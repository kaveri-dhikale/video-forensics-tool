
from io import BytesIO
from datetime import datetime, timezone
from xml.sax.saxutils import escape

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)


def generate_pdf(information, sha256_hash, anomalies):
    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    content = []

    def paragraph(value, style="Normal"):
        # Escape special XML characters before adding text to a PDF.
        return Paragraph(escape(str(value)), styles[style])

    content.append(Paragraph(
        "Digital Video Forensics Report",
        styles["Title"]
    ))
    content.append(Spacer(1, 12))

    content.append(paragraph(
        "Generated (UTC): " +
        datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    ))
    content.append(Spacer(1, 16))

    # 1. Video information
    content.append(Paragraph(
        "1. Video Information", styles["Heading2"]
    ))

    rows = [
        [
            paragraph("Property", "Heading4"),
            paragraph("Value", "Heading4")
        ]
    ]

    for key, value in information.items():
        rows.append([
            paragraph(key),
            paragraph(value)
        ])

    table = Table(
        rows,
        colWidths=[170, 320],
        repeatRows=1,
        hAlign="LEFT"
    )

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))

    content.append(table)
    content.append(Spacer(1, 16))

    # 2. File integrity
    content.append(Paragraph(
        "2. File Integrity", styles["Heading2"]
    ))
    content.append(paragraph("SHA-256: " + sha256_hash))
    content.append(Spacer(1, 16))

    # 3. Frame difference analysis
    content.append(Paragraph(
        "3. Frame Difference Analysis",
        styles["Heading2"]
    ))

    # Accept the DataFrame returned by forensic.py.
    if isinstance(anomalies, pd.DataFrame):
        if (
            "Review Flag" in anomalies.columns
            and "Difference Score" in anomalies.columns
        ):
            flagged = anomalies[
                anomalies["Review Flag"] == "Review"
            ]
        else:
            flagged = anomalies.iloc[0:0]

        anomaly_records = flagged.to_dict(orient="records")

    else:
        # Also allow a list of dictionaries.
        anomaly_records = list(anomalies or [])

    content.append(paragraph(
        f"Intervals flagged for manual review: "
        f"{len(anomaly_records)}"
    ))
    content.append(Spacer(1, 8))

    if anomaly_records:
        anomaly_rows = [[
            paragraph("Time Interval", "Heading4"),
            paragraph("Difference Score", "Heading4")
        ]]

        for item in anomaly_records[:100]:
            start = item.get(
                "From Time (seconds)",
                item.get("Timestamp (s)", "N/A")
            )
            end = item.get("To Time (seconds")

            interval = (
                f"{start} - {end} seconds"
                if end is not None
                else f"{start} seconds"
            )

            anomaly_rows.append([
                paragraph(interval),
                paragraph(item.get("Difference Score", "N/A"))
            ])

        anomaly_table = Table(
            anomaly_rows,
            colWidths=[270, 220],
            repeatRows=1,
            hAlign="LEFT"
        )

        anomaly_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))

        content.append(anomaly_table)

    else:
        content.append(paragraph(
            "No intervals exceeded the configured screening "
            "threshold. This does not prove that the video "
            "is authentic."
        ))

    content.append(Spacer(1, 16))

    # 4. Limitations
    content.append(Paragraph(
        "4.  Conclusion",
        styles["Heading2"]
    ))

    content.append(paragraph(
        "This report documents automated video screening results. "
        "The SHA-256 hash identifies the exact file analyzed but "
        "cannot establish its history or authenticity without a "
        "trusted reference. Large frame differences can result "
        "from movement, scene transitions, lighting changes, or "
        "compression. Flagged intervals require manual examination "
        "and are not proof of manipulation. Metadata values read "
        "through OpenCV may be incomplete or approximate."
    ))

    document.build(content)
    return buffer.getvalue()
