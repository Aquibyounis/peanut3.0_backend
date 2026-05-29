"""
Peanut 3.0 - Async Email Service
Sends formatted contact inquiry emails via SMTP (aiosmtplib).
"""

import resend

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
    ) -> tuple[bool, str]:
        """Send formatted contact inquiry email.

        Returns (True, "") on success, (False, error_msg) on failure.
        """
        try:
            html_content = render_contact_email(
                name=name,
                email=email,
                designation=designation,
                company=company,
                message=message,
            )

            if not settings.resend_api_key:
                logger.warning(
                    "Resend API key not configured. Mocking email send.",
                    to=settings.contact_recipient_email,
                    from_name=name,
                )
                return True, "Mock email sent successfully."

            resend.api_key = settings.resend_api_key
            
            response = resend.Emails.send({
                "from": settings.resend_from_email,
                "to": settings.contact_recipient_email,
                "subject": f"Peanut AI - New Contact from {name} ({company})",
                "html": html_content
            })

            logger.info(
                "Contact email sent via Resend",
                to=settings.contact_recipient_email,
                from_name=name,
            )
            return True, ""
        except Exception as e:
            logger.error("Email send failed via Resend", error=str(e))
            return False, str(e)


email_service = EmailService()
