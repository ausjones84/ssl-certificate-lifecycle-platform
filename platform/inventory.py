#!/usr/bin/env python3
"""
platform/inventory.py
=====================
Phase 1 (Part 2): Inventory output generator.

Takes the list of CertificateRecord objects from discovery.py and
generates three output files:

  - reports/CertificateInventory.csv  (machine-readable)
  - reports/CertificateInventory.json (API-ready)
  - reports/CertificateInventory.md   (human-readable)

Usage:
    from platform.inventory import InventoryBuilder
    builder = InventoryBuilder(logger=log)
    builder.generate(records=cert_records, output_dir="reports")
"""

import csv
import json
import os
from datetime import datetime
from typing import List

from platform.logger import get_logger


CSV_HEADERS = [
    "Domain",
    "Certificate Name",
    "Key Vault",
    "Secret Name",
    "Resource Group",
    "Subscription",
    "App Service",
    "Expiration",
    "Days Until Expiry",
    "Risk Level",
    "Thumbprint",
    "Issuer",
    "Version",
    "Enabled",
    "Binding Status",
    "Last Checked",
    "Notes",
]

RISK_EMOJI = {
    "EXPIRED":  "🔴",
    "CRITICAL": "🔴",
    "HIGH":     "🟠",
    "MEDIUM":   "🟡",
    "LOW":      "🟢",
    "OK":       "✅",
    "UNKNOWN":  "⚪",
}


class InventoryBuilder:
    """Generates multi-format certificate inventory reports."""

    def __init__(self, logger=None):
        self.log = logger or get_logger()

    def generate(self, records: list, output_dir: str = "reports", timestamp: str = None) -> dict:
        """
        Generate all inventory output files.

        Args:
            records: List of CertificateRecord objects
            output_dir: Output directory (created if not exists)
            timestamp: Optional timestamp suffix for filenames

        Returns:
            Dict with paths to generated files
        """
        os.makedirs(output_dir, exist_ok=True)
        ts = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
        run_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        csv_path = os.path.join(output_dir, "CertificateInventory.csv")
        json_path = os.path.join(output_dir, "CertificateInventory.json")
        md_path = os.path.join(output_dir, "CertificateInventory.md")

        self._write_csv(records, csv_path)
        self._write_json(records, json_path, run_date)
        self._write_markdown(records, md_path, run_date)

        self.log.info("Inventory reports generated:")
        self.log.info("  CSV  : %s", csv_path)
        self.log.info("  JSON : %s", json_path)
        self.log.info("  MD   : %s", md_path)

        return {"csv": csv_path, "json": json_path, "md": md_path}

    def _write_csv(self, records: list, path: str):
        """Write inventory as CSV."""
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            writer.writeheader()
            for r in records:
                d = r.to_dict()
                writer.writerow({
                    "Domain": d["domain"],
                    "Certificate Name": d["cert_name"],
                    "Key Vault": d["key_vault"],
                    "Secret Name": d["secret_name"],
                    "Resource Group": d["resource_group"],
                    "Subscription": d["subscription"],
                    "App Service": d["app_service"],
                    "Expiration": d["expiration"],
                    "Days Until Expiry": d["days_until_expiry"],
                    "Risk Level": d["risk_level"],
                    "Thumbprint": d["thumbprint"],
                    "Issuer": d["issuer"],
                    "Version": d["version"],
                    "Enabled": d["enabled"],
                    "Binding Status": d["binding_status"],
                    "Last Checked": d["last_checked"],
                    "Notes": d["notes"],
                })

    def _write_json(self, records: list, path: str, run_date: str):
        """Write inventory as JSON."""
        payload = {
            "generated": run_date,
            "total_certificates": len(records),
            "risk_summary": self._risk_summary(records),
            "certificates": [r.to_dict() for r in records],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=str)

    def _write_markdown(self, records: list, path: str, run_date: str):
        """Write inventory as Markdown."""
        risk_summary = self._risk_summary(records)

        with open(path, "w", encoding="utf-8") as f:
            f.write("# Certificate Inventory\n\n")
            f.write(f"**Generated:** {run_date}  \n")
            f.write(f"**Total Certificates:** {len(records)}  \n\n")

            # Risk summary table
            f.write("## Risk Summary\n\n")
            f.write("| Risk Level | Count |\n|---|---|\n")
            for level in ["EXPIRED", "CRITICAL", "HIGH", "MEDIUM", "LOW", "OK", "UNKNOWN"]:
                count = risk_summary.get(level, 0)
                if count > 0:
                    emoji = RISK_EMOJI.get(level, "")
                    f.write(f"| {emoji} {level} | {count} |\n")
            f.write("\n")

            # Critical certs (<=30 days) highlighted first
            critical = [r for r in records if r.risk_level in ("EXPIRED", "CRITICAL", "HIGH")]
            if critical:
                f.write("## ⚠️ Action Required (≤ 30 Days)\n\n")
                f.write("| Domain | Certificate | Key Vault | App Service | Expires | Days Left |\n")
                f.write("|---|---|---|---|---|---|\n")
                for r in sorted(critical, key=lambda x: x.days_until_expiry or 0):
                    d = r.to_dict()
                    f.write(f"| {d['domain']} | {d['cert_name']} | {d['key_vault']} | {d['app_service']} | {d['expiration']} | **{d['days_until_expiry']}** |\n")
                f.write("\n")

            # Full inventory table
            f.write("## Full Certificate Inventory\n\n")
            f.write("| Domain | Certificate | Key Vault | App Service | Expiration | Days Left | Risk | Status |\n")
            f.write("|---|---|---|---|---|---|---|---|\n")
            for r in sorted(records, key=lambda x: x.days_until_expiry or 9999):
                d = r.to_dict()
                emoji = RISK_EMOJI.get(d["risk_level"], "")
                days = str(d["days_until_expiry"]) if d["days_until_expiry"] is not None else "?"
                f.write(f"| {d['domain']} | {d['cert_name']} | {d['key_vault']} | {d['app_service']} | {d['expiration']} | {days} | {emoji} {d['risk_level']} | {d['binding_status']} |\n")
            f.write("\n")
            f.write("---\n\n")
            f.write(f"*Generated by SSL Certificate Lifecycle Platform v1.0.0*\n")

    def _risk_summary(self, records: list) -> dict:
        summary = {}
        for r in records:
            summary[r.risk_level] = summary.get(r.risk_level, 0) + 1
        return summary

