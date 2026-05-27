"""
Peanut 3.0 - HTML Email Templates
Professional HTML email templates with inline styles for maximum email client compatibility.
"""

from datetime import datetime, timezone


def render_contact_email(
    name: str,
    email: str,
    designation: str,
    company: str,
    message: str,
) -> str:
    """
    Render a professional HTML contact inquiry email.

    Colours
    -------
    - Background : #1a1a2e (dark navy)
    - Accent     : #e94560 (vibrant red)
    - Text       : #ffffff / #e0e0e0
    """
    timestamp = datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Peanut AI – New Contact Inquiry</title>
</head>
<body style="margin:0;padding:0;background-color:#0f0f23;font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f0f23;">
    <tr>
      <td align="center" style="padding:32px 16px;">

        <!-- Main card -->
        <table role="presentation" width="600" cellpadding="0" cellspacing="0"
               style="background-color:#1a1a2e;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.4);">

          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,#e94560 0%,#c23152 100%);padding:32px 40px;">
              <h1 style="margin:0;color:#ffffff;font-size:26px;font-weight:700;letter-spacing:0.5px;">
                🥜 Peanut AI
              </h1>
              <p style="margin:8px 0 0;color:rgba(255,255,255,0.85);font-size:14px;">
                New Contact Inquiry Received
              </p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:32px 40px;">

              <!-- Greeting -->
              <p style="color:#e0e0e0;font-size:15px;line-height:1.6;margin:0 0 24px;">
                You have received a new contact inquiry through the Peanut AI platform.
              </p>

              <!-- Sender details table -->
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                     style="background-color:#16213e;border-radius:8px;overflow:hidden;margin-bottom:24px;">
                <tr>
                  <td style="padding:20px 24px;">
                    <h2 style="margin:0 0 16px;color:#e94560;font-size:16px;font-weight:600;text-transform:uppercase;letter-spacing:1px;">
                      Sender Details
                    </h2>
                    <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td style="padding:8px 0;color:#8892b0;font-size:13px;width:120px;vertical-align:top;">Name</td>
                        <td style="padding:8px 0;color:#ffffff;font-size:14px;font-weight:500;">{_escape(name)}</td>
                      </tr>
                      <tr>
                        <td style="padding:8px 0;color:#8892b0;font-size:13px;vertical-align:top;">Email</td>
                        <td style="padding:8px 0;">
                          <a href="mailto:{_escape(email)}" style="color:#e94560;text-decoration:none;font-size:14px;">{_escape(email)}</a>
                        </td>
                      </tr>
                      <tr>
                        <td style="padding:8px 0;color:#8892b0;font-size:13px;vertical-align:top;">Designation</td>
                        <td style="padding:8px 0;color:#ffffff;font-size:14px;">{_escape(designation)}</td>
                      </tr>
                      <tr>
                        <td style="padding:8px 0;color:#8892b0;font-size:13px;vertical-align:top;">Company</td>
                        <td style="padding:8px 0;color:#ffffff;font-size:14px;font-weight:500;">{_escape(company)}</td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>

              <!-- Message body -->
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                     style="background-color:#16213e;border-radius:8px;overflow:hidden;margin-bottom:24px;">
                <tr>
                  <td style="padding:20px 24px;">
                    <h2 style="margin:0 0 12px;color:#e94560;font-size:16px;font-weight:600;text-transform:uppercase;letter-spacing:1px;">
                      Message
                    </h2>
                    <p style="color:#e0e0e0;font-size:14px;line-height:1.7;margin:0;white-space:pre-wrap;">{_escape(message)}</p>
                  </td>
                </tr>
              </table>

              <!-- Timestamp -->
              <p style="color:#8892b0;font-size:12px;margin:0;text-align:right;">
                📅 Received on {timestamp}
              </p>

            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background-color:#0f0f23;padding:20px 40px;border-top:1px solid #2a2a4a;">
              <p style="margin:0;color:#8892b0;font-size:12px;text-align:center;">
                This email was sent automatically by
                <span style="color:#e94560;font-weight:600;">Peanut AI Platform</span>.
                Please do not reply to this email.
              </p>
              <p style="margin:8px 0 0;color:#555;font-size:11px;text-align:center;">
                &copy; {datetime.now(timezone.utc).year} Peanut AI &mdash; Semantic AI Operating System
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _escape(text: str) -> str:
    """Minimal HTML-escape for untrusted user input in email context."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )
