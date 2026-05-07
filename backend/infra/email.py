import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv

load_dotenv()


def _otp_html(otp: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#F7F8FC;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:40px 16px;">
      <table width="480" cellpadding="0" cellspacing="0"
             style="background:#fff;border-radius:12px;border:1px solid #E4E7EF;overflow:hidden;">
        <tr>
          <td style="background:#4F46E5;padding:20px 28px;">
            <span style="color:#fff;font-size:18px;font-weight:700;letter-spacing:-.3px;">
              &#9889; Source<strong>Assist</strong>
            </span>
          </td>
        </tr>
        <tr>
          <td style="padding:32px 28px;">
            <h2 style="margin:0 0 8px;color:#111827;font-size:20px;">Verify your email</h2>
            <p style="margin:0 0 24px;color:#6B7280;font-size:14px;">
              Use the code below to complete your registration.
            </p>
            <div style="background:#EEF2FF;border:2px solid #C7D2FE;border-radius:10px;
                        padding:28px;text-align:center;margin-bottom:24px;">
              <span style="font-size:40px;font-weight:800;letter-spacing:12px;color:#4F46E5;">
                {otp}
              </span>
            </div>
            <p style="margin:0;color:#9CA3AF;font-size:12px;line-height:1.6;">
              This code expires in <strong style="color:#111827;">10 minutes</strong>.<br>
              If you did not request this, please ignore this email.
            </p>
          </td>
        </tr>
        <tr>
          <td style="padding:16px 28px;background:#F7F8FC;border-top:1px solid #E4E7EF;">
            <p style="margin:0;color:#9CA3AF;font-size:11px;">
              &copy; 2026 Joules to Watts &middot; SourceAssist
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _reset_html(otp: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#F7F8FC;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:40px 16px;">
      <table width="480" cellpadding="0" cellspacing="0"
             style="background:#fff;border-radius:12px;border:1px solid #E4E7EF;overflow:hidden;">
        <tr>
          <td style="background:#4F46E5;padding:20px 28px;">
            <span style="color:#fff;font-size:18px;font-weight:700;letter-spacing:-.3px;">
              &#9889; Source<strong>Assist</strong>
            </span>
          </td>
        </tr>
        <tr>
          <td style="padding:32px 28px;">
            <h2 style="margin:0 0 8px;color:#111827;font-size:20px;">Reset your password</h2>
            <p style="margin:0 0 24px;color:#6B7280;font-size:14px;">
              Use the code below to reset your password. If you didn't request this, ignore this email.
            </p>
            <div style="background:#FEF3C7;border:2px solid #FCD34D;border-radius:10px;
                        padding:28px;text-align:center;margin-bottom:24px;">
              <span style="font-size:40px;font-weight:800;letter-spacing:12px;color:#D97706;">
                {otp}
              </span>
            </div>
            <p style="margin:0;color:#9CA3AF;font-size:12px;line-height:1.6;">
              This code expires in <strong style="color:#111827;">10 minutes</strong>.<br>
              If you did not request this, your account is safe — please ignore this email.
            </p>
          </td>
        </tr>
        <tr>
          <td style="padding:16px 28px;background:#F7F8FC;border-top:1px solid #E4E7EF;">
            <p style="margin:0;color:#9CA3AF;font-size:11px;">
              &copy; 2026 Joules to Watts &middot; SourceAssist
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _send(to_email: str, subject: str, html: str) -> None:
    # Read at call time so .env changes don't require restart
    gmail_user = os.getenv("GMAIL_USER", "").strip()
    gmail_pass = os.getenv("GMAIL_APP_PASSWORD", "").strip()
    smtp_host  = os.getenv("SMTP_HOST", "").strip()
    smtp_port  = int(os.getenv("SMTP_PORT", "2525"))
    smtp_user  = os.getenv("SMTP_USERNAME", "").strip()
    smtp_pass  = os.getenv("SMTP_PASSWORD", "").strip()
    # .env key may be lowercase "from_email" — try both
    from_email = (
        os.getenv("FROM_EMAIL")
        or os.getenv("from_email")
        or "talentsphere@joulestowatts.com"
    ).strip()

    msg            = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["To"]      = to_email
    msg.attach(MIMEText(html, "html"))

    if gmail_user and gmail_pass:
        msg["From"] = gmail_user
        print(f"[email] sending via Gmail as {gmail_user} → {to_email}")
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.login(gmail_user, gmail_pass)
            server.send_message(msg)
        print(f"[email] sent ✓")

    elif smtp_host and smtp_user and smtp_pass:
        msg["From"] = from_email
        print(f"[email] sending via SMTP {smtp_host}:{smtp_port} as {from_email} → {to_email}")
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        print(f"[email] sent ✓")

    else:
        raise RuntimeError(
            f"No email credentials found. "
            f"GMAIL_USER={repr(gmail_user)} SMTP_HOST={repr(smtp_host)} "
            f"SMTP_USERNAME={repr(smtp_user)}"
        )


def send_activation_email(to_email: str, otp: str) -> None:
    _send(to_email, "SourceAssist – Verify your email", _otp_html(otp))


def send_password_reset_email(to_email: str, otp: str) -> None:
    _send(to_email, "SourceAssist – Reset your password", _reset_html(otp))
