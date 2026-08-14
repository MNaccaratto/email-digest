"""
send_email.py
--------------
Responsibility: send an already-built HTML string as an email. That's it.

This file doesn't know what a "task" or a "digest" is -- it just takes
a subject and an HTML body and sends them via SMTP. Keeping it this
generic means you could reuse it for any future project that needs to
email something, not just this one.
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_html_email(
    subject: str,
    html_body: str,
    from_addr: str,
    to_addr: str,
    app_password: str,
    smtp_server: str = "smtp.gmail.com",
    smtp_port: int = 587,
) -> None:
    """
    Send an HTML email via SMTP using STARTTLS.

    Parameters:
        subject: the email subject line
        html_body: the HTML content to send (from format_digest.py)
        from_addr: the Gmail address sending the email
        to_addr: the address receiving it (can be the same as from_addr)
        app_password: a Gmail "App Password" -- NOT your normal Gmail
                       password. See README for how to generate one.
        smtp_server / smtp_port: defaults work for Gmail. Change these if
                       you use a different email provider.
    """
    # MIMEMultipart lets an email carry multiple content types (we only
    # use "alternative" with one HTML part here, but this is the standard
    # container email libraries expect).
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = from_addr
    message["To"] = to_addr
    message.attach(MIMEText(html_body, "html"))

    # "with" ensures the connection is closed automatically, even if
    # something goes wrong partway through sending.
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()  # upgrade to an encrypted connection before login
        server.login(from_addr, app_password)
        server.sendmail(from_addr, to_addr, message.as_string())
