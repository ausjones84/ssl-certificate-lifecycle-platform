#!/usr/bin/env python3
"""platform/notifications.py - Email notification engine with SMTP support."""

import os, smtplib, logging
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from platform.logger import get_logger


class NotificationEngine:

    def __init__(self, config: dict = None, logger=None):
        self.config = config or {}
        self.log = logger or get_logger()

    def send_risk_alert(self, analysis: dict, attachments: list = None):
        subject = (f"[CERT ALERT] {analysis.get('overall_risk','UNKNOWN')} Risk | "
                   f"{analysis.get('expiring_soon',0)} expiring | "
                   f"{datetime.now().strftime('%Y-%m-%d')}")
        body = self._build_risk_html(analysis)
        self._send(subject, body, attachments or [])

    def send_validation_result(self, cert_name: str, vault: str, passed: bool, report_path: str = ""):
        status = "PASSED" if passed else "FAILED"
        subject = f"[CERT VALIDATION] {status} | {cert_name} | {datetime.now().strftime('%Y-%m-%d')}"
        body = self._build_validation_html(cert_name, vault, status)
        attachments = [report_path] if report_path and os.path.isfile(report_path) else []
        self._send(subject, body, attachments)

    def send_import_complete(self, cert_name: str, vault: str, success: bool, details: dict = None):
        status = "SUCCESS" if success else "FAILED"
        subject = f"[CERT IMPORT] {status} | {cert_name} | {vault} | {datetime.now().strftime('%Y-%m-%d')}"
        body = f"<h2>Certificate Import {status}</h2><p>Certificate: {cert_name}<br>Vault: {vault}</p>"
        if details:
            body += "<table border='1'>" + "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k,v in details.items()) + "</table>"
        self._send(subject, body, [])

    def _build_risk_html(self, analysis):
        expiring = analysis.get("expiring_soon", 0)
        expired = analysis.get("expired", 0)
        total = analysis.get("total_certificates", 0)
        risk = analysis.get("overall_risk", "UNKNOWN")
        colour = {"CRITICAL":"#9C0006","HIGH":"#9C6500","MEDIUM":"#7D6608","LOW":"#276221","OK":"#276221"}.get(risk,"#333")
        rows = ""
        for c in analysis.get("certificates_at_risk", []):
            rows += f"<tr><td>{c['cert_name']}</td><td>{c['key_vault']}</td><td>{c.get('app_service','')}</td><td>{c['days_until_expiry']}</td><td style='color:{colour};font-weight:bold'>{c['risk_level']}</td></tr>"
        return f"""<html><body style='font-family:Calibri;color:#333'>
<h2 style='color:#1F4E79'>SSL Certificate Risk Alert</h2>
<p><b>Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')} | <b>Overall Risk:</b> <span style='color:{colour};font-weight:bold'>{risk}</span></p>
<table><tr><td>Total Certificates</td><td>{total}</td></tr>
<tr><td>Expiring Soon</td><td>{expiring}</td></tr>
<tr><td>Expired</td><td style='color:#9C0006'>{expired}</td></tr></table>
<h3>Certificates Requiring Action</h3>
<table border='1' cellpadding='6' style='border-collapse:collapse'>
<tr style='background:#1F4E79;color:#fff'><th>Certificate</th><th>Key Vault</th><th>App Service</th><th>Days Left</th><th>Risk</th></tr>
{rows}</table>
<p style='color:#888;font-size:11px'>SSL Certificate Lifecycle Platform v1.0.0</p>
</body></html>"""

    def _build_validation_html(self, cert_name, vault, status):
        colour = "#276221" if status == "PASSED" else "#9C0006"
        return f"""<html><body style='font-family:Calibri;color:#333'>
<h2 style='color:{colour}'>Post-Import Validation: {status}</h2>
<p><b>Certificate:</b> {cert_name}<br><b>Key Vault:</b> {vault}<br>
<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
<p>See attached ValidationReport.md for full details.</p>
<p style='color:#888;font-size:11px'>SSL Certificate Lifecycle Platform v1.0.0</p>
</body></html>"""

    def _send(self, subject: str, html_body: str, attachments: list):
        cfg = self.config
        smtp_server = cfg.get("smtp_server", "")
        if not smtp_server:
            self.log.debug("SMTP not configured — skipping email notification")
            return
        to_email = cfg.get("notification_email", "")
        from_email = cfg.get("smtp_from", to_email)
        if not to_email:
            self.log.warning("notification_email not set — skipping email")
            return
        msg = MIMEMultipart("mixed")
        msg["From"] = from_email
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body, "html"))
        for fp in attachments:
            if not os.path.isfile(fp):
                continue
            with open(fp, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(fp)}")
            msg.attach(part)
        try:
            port = int(cfg.get("smtp_port", 587))
            with smtplib.SMTP(smtp_server, port, timeout=15) as s:
                if cfg.get("smtp_tls", True):
                    s.starttls()
                smtp_user = cfg.get("smtp_user", "")
                smtp_pass = cfg.get("smtp_pass", "")
                if smtp_user and smtp_pass:
                    s.login(smtp_user, smtp_pass)
                s.sendmail(from_email, [e.strip() for e in to_email.split(",")], msg.as_string())
            self.log.info("Email sent to %s", to_email)
        except Exception as e:
            self.log.error("Email failed: %s", e)

