#!/usr/bin/env python3
"""platform/ai_layer.py - Phase 6: AI-assisted operations and risk analysis."""

import json
import os
from datetime import datetime
from platform.logger import get_logger


RISK_THRESHOLDS = {"CRITICAL": 14, "HIGH": 30, "MEDIUM": 60, "LOW": 90}


class AIOperationsLayer:
    """
    AI-assisted certificate operations.
    
    Without OpenAI API key: uses built-in rule-based analysis.
    With OpenAI API key: enhances with GPT-generated narratives.
    """

    def __init__(self, logger=None, openai_api_key: str = ""):
        self.log = logger or get_logger()
        self.openai_key = openai_api_key
        self._openai_available = False
        if openai_api_key:
            try:
                import openai
                self._openai_client = openai.OpenAI(api_key=openai_api_key)
                self._openai_available = True
                self.log.info("AI layer: OpenAI enabled")
            except ImportError:
                self.log.warning("AI layer: openai package not installed. Using rule-based analysis.")

    def analyze_inventory(self, records: list, days_threshold: int = 90) -> dict:
        """Analyze certificate inventory and return risk analysis."""
        self.log.info("AI OPERATIONS: Analyzing %d certificates (threshold: %d days)", len(records), days_threshold)
        
        expiring = [r for r in records if r.days_until_expiry is not None and r.days_until_expiry <= days_threshold]
        expired = [r for r in records if r.days_until_expiry is not None and r.days_until_expiry < 0]
        critical = [r for r in records if r.risk_level in ("CRITICAL", "HIGH")]
        
        analysis = {
            "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "threshold_days": days_threshold,
            "total_certificates": len(records),
            "expiring_soon": len(expiring),
            "expired": len(expired),
            "critical": len(critical),
            "certificates_at_risk": [self._analyze_single(r) for r in expiring],
            "overall_risk": self._overall_risk(expired, critical, expiring),
            "recommendations": self._generate_recommendations(records, expiring),
        }
        return analysis

    def _analyze_single(self, record) -> dict:
        d = record.to_dict()
        days = d.get("days_until_expiry", 0)
        narrative = self._generate_narrative(
            cert_name=d["cert_name"],
            key_vault=d["key_vault"],
            app_service=d["app_service"],
            days=days,
            risk=d["risk_level"],
            domain=d["domain"],
        )
        return {
            "cert_name": d["cert_name"],
            "domain": d["domain"],
            "key_vault": d["key_vault"],
            "app_service": d["app_service"],
            "days_until_expiry": days,
            "risk_level": d["risk_level"],
            "narrative": narrative,
            "action": self._recommended_action(days),
        }

    def _generate_narrative(self, cert_name, key_vault, app_service, days, risk, domain):
        if self._openai_available:
            return self._openai_narrative(cert_name, key_vault, app_service, days, risk, domain)
        return self._rule_narrative(cert_name, key_vault, app_service, days, risk)

    def _rule_narrative(self, cert_name, key_vault, app_service, days, risk):
        if days < 0:
            return (f"Certificate {cert_name} EXPIRED {abs(days)} days ago. "
                    f"App Service {app_service} is consuming this certificate from Key Vault {key_vault}. "
                    f"Immediate action required. Services may be presenting an invalid certificate.")
        urgency = {
            "CRITICAL": "Immediate renewal is required.",
            "HIGH": "Renewal should begin today.",
            "MEDIUM": "Schedule renewal this week.",
            "LOW": "Add to the renewal backlog.",
        }.get(risk, "Review recommended.")
        app_part = f"App Service {app_service} is consuming this certificate from Key Vault {key_vault}. " if app_service else f"Certificate is stored in Key Vault {key_vault}. "
        return (f"Certificate {cert_name} expires in {days} days. " + app_part + urgency)

    def _openai_narrative(self, cert_name, key_vault, app_service, days, risk, domain):
        try:
            prompt = (f"Write a concise, professional one-paragraph operational alert for an engineer. "
                      f"Certificate '{cert_name}' for domain '{domain}' expires in {days} days. "
                      f"It is stored in Azure Key Vault '{key_vault}' and bound to App Service '{app_service}'. "
                      f"Risk level: {risk}. Include: what needs to be done, urgency level, and potential business impact.")
            response = self._openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            self.log.debug("OpenAI narrative failed: %s", e)
            return self._rule_narrative(cert_name, key_vault, "", days, risk)

    def _recommended_action(self, days):
        if days < 0: return "URGENT: Certificate expired. Renew and import immediately."
        if days <= 14: return "CRITICAL: Begin renewal process today. Aim to complete within 24-48 hours."
        if days <= 30: return "HIGH: Schedule renewal this week."
        if days <= 60: return "MEDIUM: Schedule renewal in the next 2 weeks."
        return "LOW: Add to upcoming renewal queue."

    def _overall_risk(self, expired, critical, expiring):
        if expired: return "CRITICAL"
        if len([r for r in expiring if r.risk_level == "CRITICAL"]): return "HIGH"
        if len([r for r in expiring if r.risk_level == "HIGH"]): return "MEDIUM"
        return "LOW"

    def _generate_recommendations(self, records, expiring):
        recs = []
        if any(r.days_until_expiry is not None and r.days_until_expiry < 0 for r in records):
            recs.append("URGENT: One or more certificates have already expired. Begin emergency renewal immediately.")
        critical = [r for r in expiring if r.risk_level in ("CRITICAL",)]
        if critical:
            recs.append(f"Begin renewal for {len(critical)} certificate(s) expiring within 14 days.")
        if len(expiring) > 0:
            recs.append(f"Schedule renewal windows for {len(expiring)} certificate(s) expiring within {max(r.days_until_expiry or 0 for r in expiring)} days.")
        recs.append("Set up automated expiry monitoring and alerts at 90, 60, 30, and 14 days.")
        recs.append("Validate App Service synchronization after each Key Vault import.")
        return recs

    def generate_executive_summary(self, records: list) -> str:
        analysis = self.analyze_inventory(records, 90)
        today = datetime.now().strftime("%Y-%m-%d")
        lines = [
            f"# Executive Certificate Risk Summary",
            f"**Date:** {today}",
            f"",
            f"## Portfolio Overview",
            f"| Metric | Value |",
            f"|---|---|",
            f"| Total Certificates | {analysis['total_certificates']} |",
            f"| Expiring in 90 Days | {analysis['expiring_soon']} |",
            f"| Expired | {analysis['expired']} |",
            f"| Overall Risk | **{analysis['overall_risk']}** |",
            f"",
            f"## Recommendations",
        ]
        for rec in analysis["recommendations"]:
            lines.append(f"- {rec}")
        return "\n".join(lines)

    def generate_jira_update(self, cert_name: str, stage: str, details: dict = None) -> str:
        from platform.jira_templates import JiraTemplates
        jt = JiraTemplates(logger=self.log)
        return jt.generate(cert_name, stage, details or {})

    def write_risk_report(self, records: list, output_dir: str = "reports", days: int = 90):
        analysis = self.analyze_inventory(records, days)
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, "RiskReport.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# Certificate Risk Report\n\n")
            f.write(f"**Generated:** {analysis['generated']} | **Threshold:** {days} days\n\n")
            f.write(f"**Overall Risk:** {analysis['overall_risk']}\n\n")
            f.write(f"## Summary\n\n")
            f.write(f"| Metric | Value |\n|---|---|\n")
            f.write(f"| Total | {analysis['total_certificates']} |\n")
            f.write(f"| Expiring (≤{days}d) | {analysis['expiring_soon']} |\n")
            f.write(f"| Expired | {analysis['expired']} |\n\n")
            if analysis["certificates_at_risk"]:
                f.write(f"## Certificates Requiring Action\n\n")
                for cert in sorted(analysis["certificates_at_risk"], key=lambda x: x["days_until_expiry"] or 0):
                    f.write(f"### {cert['cert_name']} ({cert['risk_level']})\n\n")
                    f.write(f"{cert['narrative']}\n\n")
                    f.write(f"**Action:** {cert['action']}\n\n")
            f.write("## Recommendations\n\n")
            for rec in analysis["recommendations"]:
                f.write(f"- {rec}\n")
        self.log.info("Risk report: %s", path)
        return path

