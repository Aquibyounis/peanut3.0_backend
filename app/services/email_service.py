"""
Peanut 3.0 - Async Email Service
Sends formatted contact inquiry emails via SMTP (aiosmtplib).
"""

import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import settings
from app.core.logging.logger import get_logger
from app.utils.email_templates import render_contact_email

logger = get_logger(__name__)


class EmailService:
    """Async email service for sending formatted contact inquiries."""

    async def send_contact_email(
        self,
        name: str,
        email: str,
        designation: str,
        company: str,
        message: str,
    ) -> bool:
        """Send formatted contact inquiry email.

        Returns True on success, False on failure.
        """
        try:
            html_content = render_contact_email(
                name=name,
                email=email,
                designation=designation,
                company=company,
                message=message,
            )

            if not settings.smtp_user or not settings.smtp_password:
                logger.warning(
                    "SMTP credentials not configured. Mocking email send.",
                    to=settings.contact_recipient_email,
                    from_name=name,
                )
                return True

            msg = MIMEMultipart("alternative")
            msg["From"] = settings.smtp_from_email or settings.smtp_user
            msg["To"] = settings.contact_recipient_email
            msg["Subject"] = f"Peanut AI - New Contact from {name} ({company})"

            msg.attach(MIMEText(html_content, "html"))

            await aiosmtplib.send(
                msg,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_user,
                password=settings.smtp_password,
                use_tls=False,
                start_tls=True,
            )

            logger.info(
                "Contact email sent",
                to=settings.contact_recipient_email,
                from_name=name,
            )
            return True
        except Exception as e:
            logger.error("Email send failed", error=str(e))
            return False


email_service = EmailService()
