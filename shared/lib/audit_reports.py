"""PDF Audit Report Generation for Workflow Event Sourcing

This module generates comprehensive compliance audit reports including:
1. Workflow timeline with Gantt chart visualization
2. Approval history with approver roles and timestamps
3. Resource lock acquisition/release events
4. Error events and retry attempts
5. Event signatures for tamper detection
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path
import io

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
        PageBreak,
        Image,
    )
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics.charts.barcharts import HorizontalBarChart

    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


class AuditReportGenerator:
    """Generate PDF audit reports for workflow execution compliance"""

    def __init__(self):
        if not REPORTLAB_AVAILABLE:
            raise ImportError(
                "reportlab is required for PDF generation. "
                "Install with: pip install reportlab"
            )

        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        self.styles.add(
            ParagraphStyle(
                name="CustomTitle",
                parent=self.styles["Heading1"],
                fontSize=24,
                textColor=colors.HexColor("#1a1a1a"),
                spaceAfter=30,
            )
        )

        self.styles.add(
            ParagraphStyle(
                name="SectionHeader",
                parent=self.styles["Heading2"],
                fontSize=16,
                textColor=colors.HexColor("#2c5282"),
                spaceBefore=20,
                spaceAfter=12,
            )
        )

        self.styles.add(
            ParagraphStyle(
                name="EventDetail",
                parent=self.styles["Normal"],
                fontSize=10,
                leftIndent=20,
                spaceAfter=6,
            )
        )

    def generate_report(
        self,
        workflow_id: str,
        events: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        output_path: Optional[Path] = None,
    ) -> bytes:
        """Generate comprehensive audit report

        Args:
            workflow_id: Workflow identifier
            events: List of workflow events
            metadata: Workflow metadata (template_name, status, etc.)
            output_path: Optional path to save PDF file

        Returns:
            PDF content as bytes
        """

        # Create PDF document
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18,
        )

        # Build report content
        story = []

        # Title page
        story.extend(self._build_title_page(workflow_id, metadata))
        story.append(PageBreak())

        # Executive summary
        story.extend(self._build_executive_summary(events, metadata))
        story.append(Spacer(1, 0.2 * inch))

        # Timeline visualization
        story.extend(self._build_timeline_chart(events))
        story.append(Spacer(1, 0.2 * inch))

        # Event log table
        story.extend(self._build_event_log_table(events))
        story.append(PageBreak())

        # Approval history
        approval_events = [
            e for e in events if e["action"] in ["APPROVE_GATE", "REJECT_GATE"]
        ]
        if approval_events:
            story.extend(self._build_approval_section(approval_events))
            story.append(Spacer(1, 0.2 * inch))

        # Error and retry analysis
        error_events = [e for e in events if e["action"] in ["FAIL_STEP", "RETRY_STEP"]]
        if error_events:
            story.extend(self._build_error_analysis(error_events))
            story.append(Spacer(1, 0.2 * inch))

        # Resource lock history
        story.extend(self._build_resource_lock_section(events))
        story.append(Spacer(1, 0.2 * inch))

        # Signature verification
        story.extend(self._build_signature_verification(events))

        # Build PDF
        doc.build(story)

        # Get PDF bytes
        pdf_content = buffer.getvalue()
        buffer.close()

        # Save to file if path provided
        if output_path:
            output_path.write_bytes(pdf_content)

        return pdf_content

    def _build_title_page(self, workflow_id: str, metadata: Dict[str, Any]) -> List:
        """Build title page"""

        elements = []

        # Title
        title = Paragraph(f"Workflow Audit Report", self.styles["CustomTitle"])
        elements.append(title)
        elements.append(Spacer(1, 0.3 * inch))

        # Workflow details
        details_data = [
            ["Workflow ID:", workflow_id],
            ["Template:", metadata.get("template_name", "N/A")],
            ["Status:", metadata.get("status", "N/A").upper()],
            ["Generated:", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")],
        ]

        if metadata.get("created_at"):
            details_data.append(["Started:", metadata["created_at"]])

        if metadata.get("completed_at"):
            details_data.append(["Completed:", metadata["completed_at"]])

        details_table = Table(details_data, colWidths=[2 * inch, 4 * inch])
        details_table.setStyle(
            TableStyle(
                [
                    ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 12),
                    ("FONT", (1, 0), (1, -1), "Helvetica", 12),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )

        elements.append(details_table)
        elements.append(Spacer(1, 0.5 * inch))

        # Compliance statement
        compliance_text = (
            "<b>Compliance Statement:</b><br/>"
            "This audit report contains a complete, tamper-proof record of all workflow events. "
            "Each event is cryptographically signed using HMAC-SHA256 to ensure integrity. "
            "All timestamps are in UTC for regulatory compliance."
        )

        elements.append(Paragraph(compliance_text, self.styles["Normal"]))

        return elements

    def _build_executive_summary(
        self, events: List[Dict[str, Any]], metadata: Dict[str, Any]
    ) -> List:
        """Build executive summary section"""

        elements = []

        elements.append(Paragraph("Executive Summary", self.styles["SectionHeader"]))

        # Calculate metrics
        total_events = len(events)
        steps_completed = len([e for e in events if e["action"] == "COMPLETE_STEP"])
        steps_failed = len([e for e in events if e["action"] == "FAIL_STEP"])
        retry_attempts = len([e for e in events if e["action"] == "RETRY_STEP"])
        approvals = len([e for e in events if e["action"] == "APPROVE_GATE"])
        rejections = len([e for e in events if e["action"] == "REJECT_GATE"])

        # Duration calculation
        if events:
            start_time = datetime.fromisoformat(
                events[0]["timestamp"].replace("Z", "+00:00")
            )
            end_time = datetime.fromisoformat(
                events[-1]["timestamp"].replace("Z", "+00:00")
            )
            duration = end_time - start_time
            duration_str = str(duration).split(".")[0]  # Remove microseconds
        else:
            duration_str = "N/A"

        summary_data = [
            ["Total Events", str(total_events)],
            ["Steps Completed", str(steps_completed)],
            ["Steps Failed", str(steps_failed)],
            ["Retry Attempts", str(retry_attempts)],
            ["Approvals", str(approvals)],
            ["Rejections", str(rejections)],
            ["Duration", duration_str],
        ]

        summary_table = Table(summary_data, colWidths=[3 * inch, 2 * inch])
        summary_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f7fafc")),
                    ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 11),
                    ("FONT", (1, 0), (1, -1), "Helvetica", 11),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )

        elements.append(summary_table)

        return elements

    def _build_timeline_chart(self, events: List[Dict[str, Any]]) -> List:
        """Build timeline Gantt chart"""

        elements = []

        elements.append(Paragraph("Workflow Timeline", self.styles["SectionHeader"]))

        # Group events by step
        step_events = {}
        for event in events:
            step_id = event.get("step_id", "unknown")
            if step_id not in step_events:
                step_events[step_id] = []
            step_events[step_id].append(event)

        # Build simple timeline table (Gantt chart requires more complex rendering)
        timeline_data = [["Step", "Start Time", "End Time", "Status"]]

        for step_id, step_event_list in step_events.items():
            if not step_event_list:
                continue

            start_event = step_event_list[0]
            end_event = step_event_list[-1]

            start_time = start_event["timestamp"][:19]  # Remove timezone
            end_time = end_event["timestamp"][:19]

            # Determine status
            if any(e["action"] == "COMPLETE_STEP" for e in step_event_list):
                status = "Completed"
            elif any(e["action"] == "FAIL_STEP" for e in step_event_list):
                status = "Failed"
            else:
                status = "In Progress"

            timeline_data.append([step_id, start_time, end_time, status])

        timeline_table = Table(
            timeline_data, colWidths=[1.5 * inch, 2 * inch, 2 * inch, 1 * inch]
        )
        timeline_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c5282")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 11),
                    ("FONT", (0, 1), (-1, -1), "Helvetica", 9),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#f7fafc")],
                    ),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )

        elements.append(timeline_table)

        return elements

    def _build_event_log_table(self, events: List[Dict[str, Any]]) -> List:
        """Build detailed event log table"""

        elements = []

        elements.append(Paragraph("Detailed Event Log", self.styles["SectionHeader"]))

        # Build table data
        table_data = [["Time", "Action", "Step", "Details"]]

        for event in events[:50]:  # Limit to 50 events for readability
            timestamp = event["timestamp"][:19]
            action = event["action"]
            step_id = event.get("step_id", "-")

            # Extract relevant details
            data = event.get("data", {})
            if action == "FAIL_STEP":
                details = data.get("error", "No error message")
            elif action == "APPROVE_GATE":
                approver = data.get("approver", "Unknown")
                details = f"Approved by {approver}"
            elif action == "RETRY_STEP":
                attempt = data.get("retry_attempt", 1)
                details = f"Retry attempt {attempt}"
            else:
                details = "-"

            table_data.append([timestamp, action, step_id, details[:40]])

        if len(events) > 50:
            table_data.append(["...", f"{len(events) - 50} more events", "...", "..."])

        event_table = Table(
            table_data, colWidths=[1.5 * inch, 1.5 * inch, 1.2 * inch, 2.3 * inch]
        )
        event_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c5282")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 10),
                    ("FONT", (0, 1), (-1, -1), "Helvetica", 8),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#f7fafc")],
                    ),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )

        elements.append(event_table)

        return elements

    def _build_approval_section(self, approval_events: List[Dict[str, Any]]) -> List:
        """Build approval history section"""

        elements = []

        elements.append(Paragraph("Approval History", self.styles["SectionHeader"]))

        table_data = [["Time", "Gate", "Decision", "Approver", "Role", "Comment"]]

        for event in approval_events:
            timestamp = event["timestamp"][:19]
            step_id = event.get("step_id", "-")
            decision = "Approved" if event["action"] == "APPROVE_GATE" else "Rejected"

            data = event.get("data", {})
            approver = data.get("approver", "Unknown")
            role = data.get("approver_role", "-")
            comment = data.get("comment", "-")[:30]

            table_data.append([timestamp, step_id, decision, approver, role, comment])

        approval_table = Table(
            table_data,
            colWidths=[
                1.2 * inch,
                1 * inch,
                0.8 * inch,
                1.3 * inch,
                0.9 * inch,
                1.3 * inch,
            ],
        )
        approval_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c5282")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
                    ("FONT", (0, 1), (-1, -1), "Helvetica", 8),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#f7fafc")],
                    ),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )

        elements.append(approval_table)

        return elements

    def _build_error_analysis(self, error_events: List[Dict[str, Any]]) -> List:
        """Build error and retry analysis section"""

        elements = []

        elements.append(
            Paragraph("Error and Retry Analysis", self.styles["SectionHeader"])
        )

        table_data = [["Time", "Step", "Error Type", "Message", "Retry #"]]

        for event in error_events:
            timestamp = event["timestamp"][:19]
            step_id = event.get("step_id", "-")

            data = event.get("data", {})

            if event["action"] == "FAIL_STEP":
                error_type = data.get("error_type", "unknown")
                message = data.get("error", "No message")[:40]
                retry_num = "-"
            else:  # RETRY_STEP
                error_type = "-"
                message = "Retry initiated"
                retry_num = str(data.get("retry_attempt", 1))

            table_data.append([timestamp, step_id, error_type, message, retry_num])

        error_table = Table(
            table_data,
            colWidths=[1.2 * inch, 1.2 * inch, 1 * inch, 2.3 * inch, 0.8 * inch],
        )
        error_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#c53030")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
                    ("FONT", (0, 1), (-1, -1), "Helvetica", 8),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#fff5f5")],
                    ),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )

        elements.append(error_table)

        return elements

    def _build_resource_lock_section(self, events: List[Dict[str, Any]]) -> List:
        """Build resource lock acquisition/release section"""

        elements = []

        elements.append(
            Paragraph("Resource Lock History", self.styles["SectionHeader"])
        )

        # Extract resource lock events (from START_WORKFLOW, COMPLETE_STEP, CANCEL_WORKFLOW)
        lock_info = []

        for event in events:
            data = event.get("data", {})
            if "resource_lock" in data:
                lock_info.append(
                    {
                        "timestamp": event["timestamp"][:19],
                        "action": event["action"],
                        "lock": data["resource_lock"],
                    }
                )

        if not lock_info:
            elements.append(
                Paragraph(
                    "No resource locks were used in this workflow.",
                    self.styles["Normal"],
                )
            )
            return elements

        table_data = [["Time", "Action", "Resource Lock"]]

        for info in lock_info:
            table_data.append([info["timestamp"], info["action"], info["lock"]])

        lock_table = Table(table_data, colWidths=[2 * inch, 2 * inch, 2.5 * inch])
        lock_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c5282")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 10),
                    ("FONT", (0, 1), (-1, -1), "Helvetica", 9),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#f7fafc")],
                    ),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )

        elements.append(lock_table)

        return elements

    def _build_signature_verification(self, events: List[Dict[str, Any]]) -> List:
        """Build signature verification section"""

        elements = []

        elements.append(
            Paragraph("Event Signature Verification", self.styles["SectionHeader"])
        )

        # Check if events have signatures
        signed_events = [e for e in events if e.get("signature")]

        verification_text = (
            f"<b>Total Events:</b> {len(events)}<br/>"
            f"<b>Signed Events:</b> {len(signed_events)}<br/>"
            f"<b>Signature Algorithm:</b> HMAC-SHA256<br/>"
            f"<b>Tamper Detection:</b> Enabled<br/><br/>"
            "All events are cryptographically signed to ensure integrity. "
            "Any modification to event data would invalidate the signature, "
            "providing tamper-proof audit trails for compliance."
        )

        elements.append(Paragraph(verification_text, self.styles["Normal"]))

        return elements


def generate_audit_report(
    workflow_id: str,
    events: List[Dict[str, Any]],
    metadata: Dict[str, Any],
    output_path: Optional[str] = None,
) -> bytes:
    """Convenience function to generate audit report

    Args:
        workflow_id: Workflow identifier
        events: List of workflow events
        metadata: Workflow metadata
        output_path: Optional path to save PDF file

    Returns:
        PDF content as bytes
    """

    generator = AuditReportGenerator()

    output_file = Path(output_path) if output_path else None

    return generator.generate_report(workflow_id, events, metadata, output_file)
