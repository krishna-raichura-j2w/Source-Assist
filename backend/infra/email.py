import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def _html_body(otp: str) -> str:
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
              Use the code below to verify your email and set your password.
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


def send_otp_email(to_email: str, otp: str):
    msg            = MIMEMultipart("alternative")
    msg["Subject"] = "SourceAssist – Your OTP Code"
    msg["To"]      = to_email

    gmail_user = os.getenv("GMAIL_USER", "").strip()
    gmail_pass = os.getenv("GMAIL_APP_PASSWORD", "").strip()

    if gmail_user and gmail_pass:
        msg["From"] = f"SourceAssist <{gmail_user}>"
        msg.attach(MIMEText(_html_body(otp), "html"))
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.login(gmail_user, gmail_pass)
            server.send_message(msg)
    else:
        msg["From"] = os.getenv("FROM_EMAIL", "noreply@joulestowatts.com")
        msg.attach(MIMEText(_html_body(otp), "html"))
        with smtplib.SMTP(os.getenv("SMTP_HOST"), int(os.getenv("SMTP_PORT", 2525))) as server:
            server.ehlo()
            server.starttls()
            server.login(os.getenv("SMTP_USERNAME"), os.getenv("SMTP_PASSWORD"))
            server.send_message(msg)
