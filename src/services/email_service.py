"""Email service for sending notifications and reports."""
import logging
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import List, Optional

import aiosmtplib

from src.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending email notifications and reports."""

    # Stakeholder email groups
    STAKEHOLDERS = {
        "executive": [
            "cfo@healthcare.local",
            "cmo@healthcare.local",
            "ceo@healthcare.local",
        ],
        "analytics": [
            "analytics-team@healthcare.local",
            "data-science@healthcare.local",
        ],
        "operations": [
            "care-coordinators@healthcare.local",
            "clinical-ops@healthcare.local",
        ],
    }

    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None
    ):
        """Initialize the email service."""
        self.smtp_host = smtp_host or settings.smtp_host
        self.smtp_port = smtp_port or settings.smtp_port

    async def health_check(self) -> bool:
        """Check if SMTP server is accessible."""
        try:
            async with aiosmtplib.SMTP(
                hostname=self.smtp_host,
                port=self.smtp_port
            ) as smtp:
                await smtp.noop()
            return True
        except Exception as e:
            logger.error(f"SMTP health check failed: {e}")
            return False

    async def send_email(
        self,
        to_addresses: List[str],
        subject: str,
        html_body: str,
        attachments: Optional[List[Path]] = None,
        from_address: str = "analytics-pipeline@healthcare.local"
    ) -> bool:
        """
        Send an email with optional attachments.

        Args:
            to_addresses: List of recipient email addresses
            subject: Email subject line
            html_body: HTML content of the email body
            attachments: Optional list of file paths to attach
            from_address: Sender email address

        Returns:
            True if email was sent successfully
        """
        try:
            message = MIMEMultipart()
            message["From"] = from_address
            message["To"] = ", ".join(to_addresses)
            message["Subject"] = subject

            # Add HTML body
            message.attach(MIMEText(html_body, "html"))

            # Add attachments
            if attachments:
                for attachment_path in attachments:
                    if attachment_path.exists():
                        with open(attachment_path, "rb") as f:
                            part = MIMEApplication(f.read(), Name=attachment_path.name)
                        part["Content-Disposition"] = f'attachment; filename="{attachment_path.name}"'
                        message.attach(part)
                        logger.debug(f"Attached file: {attachment_path.name}")

            # Send email
            async with aiosmtplib.SMTP(
                hostname=self.smtp_host,
                port=self.smtp_port
            ) as smtp:
                await smtp.send_message(message)

            logger.info(f"Email sent to {to_addresses}: {subject}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    async def send_workflow_completion(
        self,
        workflow_id: str,
        contract_id: str,
        performance_year: int,
        performance_month: int,
        summary: dict,
        report_path: Optional[Path] = None,
        report_type: str = "executive"
    ) -> bool:
        """Send workflow completion notification with report."""
        recipients = self.STAKEHOLDERS.get(report_type, self.STAKEHOLDERS["analytics"])

        # Build HTML email body
        html_body = self._build_completion_email(
            workflow_id=workflow_id,
            contract_id=contract_id,
            performance_year=performance_year,
            performance_month=performance_month,
            summary=summary,
        )

        subject = (
            f"[MSSP Analytics] {contract_id} - "
            f"{performance_year} M{performance_month:02d} Report Ready"
        )

        attachments = [report_path] if report_path and report_path.exists() else None

        return await self.send_email(
            to_addresses=recipients,
            subject=subject,
            html_body=html_body,
            attachments=attachments,
        )

    async def send_workflow_failure(
        self,
        workflow_id: str,
        contract_id: str,
        error_message: str,
        errors: List[dict]
    ) -> bool:
        """Send workflow failure notification."""
        recipients = self.STAKEHOLDERS["analytics"]

        html_body = self._build_failure_email(
            workflow_id=workflow_id,
            contract_id=contract_id,
            error_message=error_message,
            errors=errors,
        )

        subject = f"[MSSP Analytics] FAILED: {contract_id} Workflow {workflow_id}"

        return await self.send_email(
            to_addresses=recipients,
            subject=subject,
            html_body=html_body,
        )

    def _build_completion_email(
        self,
        workflow_id: str,
        contract_id: str,
        performance_year: int,
        performance_month: int,
        summary: dict,
    ) -> str:
        """Build HTML email body for workflow completion."""
        financial = summary.get("financial", {})
        quality = summary.get("quality", {})

        savings = financial.get("total_savings", 0)
        savings_pct = financial.get("savings_percentage", 0)
        quality_score = quality.get("composite_score", 0)
        quality_status = quality.get("quality_gate_status", "pending")

        # Determine status color
        if savings > 0 and quality_status == "eligible":
            status_color = "#28a745"
            status_text = "On Track"
        elif quality_status == "at_risk" or savings < 0:
            status_color = "#ffc107"
            status_text = "At Risk"
        else:
            status_color = "#dc3545"
            status_text = "Needs Attention"

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #2c3e50; color: white; padding: 20px; text-align: center; }}
                .status {{ display: inline-block; padding: 5px 15px; border-radius: 20px;
                          background: {status_color}; color: white; font-weight: bold; }}
                .metrics {{ display: flex; justify-content: space-around; margin: 20px 0; }}
                .metric {{ text-align: center; padding: 15px; background: #f8f9fa; border-radius: 8px; }}
                .metric-value {{ font-size: 24px; font-weight: bold; color: #2c3e50; }}
                .metric-label {{ font-size: 12px; color: #666; text-transform: uppercase; }}
                .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>MSSP Analytics Report</h1>
                    <p>{contract_id} | {performance_year} M{performance_month:02d}</p>
                    <span class="status">{status_text}</span>
                </div>

                <div class="metrics">
                    <div class="metric">
                        <div class="metric-value">${savings:,.0f}</div>
                        <div class="metric-label">Total Savings</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{savings_pct:.1f}%</div>
                        <div class="metric-label">Below Baseline</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{quality_score:.1f}%</div>
                        <div class="metric-label">Quality Score</div>
                    </div>
                </div>

                <h3>Summary</h3>
                <ul>
                    <li>Workflow ID: {workflow_id}</li>
                    <li>Members: {financial.get('average_members', 0):,}</li>
                    <li>ER Visits/1000: {financial.get('er_visits_per_1000', 0):.0f}</li>
                    <li>Admits/1000: {financial.get('admits_per_1000', 0):.0f}</li>
                </ul>

                <p>See the attached PowerPoint report for detailed analysis.</p>

                <div class="footer">
                    <p>This is an automated message from the MSSP Analytics Pipeline.</p>
                    <p>Workflow ID: {workflow_id}</p>
                </div>
            </div>
        </body>
        </html>
        """

    def _build_failure_email(
        self,
        workflow_id: str,
        contract_id: str,
        error_message: str,
        errors: List[dict],
    ) -> str:
        """Build HTML email body for workflow failure."""
        error_list = "".join(
            f"<li><strong>{e.get('agent', 'Unknown')}:</strong> {e.get('message', 'No details')}</li>"
            for e in errors[:5]
        )

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #dc3545; color: white; padding: 20px; text-align: center; }}
                .error-box {{ background: #fff3cd; border: 1px solid #ffc107; padding: 15px;
                             border-radius: 8px; margin: 20px 0; }}
                .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Workflow Failed</h1>
                    <p>{contract_id}</p>
                </div>

                <div class="error-box">
                    <h3>Error Summary</h3>
                    <p>{error_message}</p>
                </div>

                <h3>Error Details</h3>
                <ul>
                    {error_list}
                </ul>

                <p>Please investigate and retry the workflow.</p>

                <div class="footer">
                    <p>Workflow ID: {workflow_id}</p>
                </div>
            </div>
        </body>
        </html>
        """
