#!/usr/bin/env python3
"""
platform/main.py - SSL Certificate Lifecycle Platform CLI Entry Point

All commands route through this file.

Usage:
  python platform/main.py health-check
  python platform/main.py discover [--subscription NAME] [--all-subscriptions]
  python platform/main.py ai-report [--days 90]
  python platform/main.py executive-summary
  python platform/main.py import --cert CERT_NAME [--preview|--dry-run|--execute]
  python platform/main.py validate --cert CERT_NAME [--all]
  python platform/main.py jira-update --cert CERT_NAME --stage STAGE
  python platform/main.py report [--format all|md|html|csv|json]
"""

import argparse
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from platform.logger import setup_logging, log_banner
from platform.azure_client import AzureClient
from platform.discovery import CertificateDiscovery
from platform.inventory import InventoryBuilder
from platform.keyvault_ops import KeyVaultOps
from platform.validator import PostImportValidator
from platform.ai_layer import AIOperationsLayer
from platform.reporting import ReportGenerator
from platform.jira_templates import JiraTemplates
from platform.notifications import NotificationEngine

VERSION = "1.0.0"
CONFIG_PATH = "config/settings.json"


def load_config(path: str = CONFIG_PATH) -> dict:
    if not os.path.isfile(path):
        print(f"WARNING: Config not found at {path}")
        print(f"  Run: cp config/settings.json.example config/settings.json")
        print(f"  Then edit config/settings.json with your environment details.")
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def cmd_health_check(args, client, log, config):
    log_banner(log, f"SSL Certificate Lifecycle Platform v{VERSION}", "Health Check")
    checks = []
    
    # Python version
    import sys as _sys
    py_ok = _sys.version_info >= (3, 10)
    checks.append(("Python 3.10+", py_ok, f"Python {_sys.version.split()[0]}"))
    
    # Azure CLI
    az_result = client.run(["version"])
    checks.append(("Azure CLI", az_result is not None, "az installed" if az_result else "az not found"))
    
    # Azure login
    acct = client.run(["account", "show"])
    checks.append(("Azure authenticated", acct is not None,
                   acct.get("name", "") if acct else "Not logged in — run: az login --use-device-code"))
    
    # OpenSSL
    import shutil
    openssl = shutil.which("openssl")
    checks.append(("OpenSSL", openssl is not None, openssl or "openssl not found — install from https://slproweb.com"))
    
    # Config file
    cfg_ok = os.path.isfile(CONFIG_PATH)
    checks.append(("Config file", cfg_ok, CONFIG_PATH if cfg_ok else f"Not found — copy from {CONFIG_PATH}.example"))
    
    # Reports directory
    os.makedirs("reports", exist_ok=True)
    checks.append(("Reports directory", True, "reports/"))
    
    # Key Vault access
    vault = config.get("key_vault_name", "")
    if vault:
        kv_ok = client.test_keyvault_access(vault)
        checks.append(("Key Vault accessible", kv_ok, vault))
    
    passed = sum(1 for _, ok, _ in checks if ok)
    failed = len(checks) - passed
    log.info("")
    for name, ok, detail in checks:
        status = "[PASS]" if ok else "[FAIL]"
        log.info("  %s %s — %s", status, name, detail)
    log.info("")
    log.info("Result: %d/%d checks passed", passed, len(checks))
    if failed == 0:
        log.info("All checks passed. Platform is ready.")
    else:
        log.warning("%d check(s) failed. See details above.", failed)
    return failed == 0


def cmd_discover(args, client, log, config):
    log_banner(log, f"SSL Certificate Lifecycle Platform v{VERSION}", "Phase 1: Discovery")
    client.validate_login()
    discovery = CertificateDiscovery(client=client, logger=log, config=config)
    records = discovery.run(
        subscription=getattr(args, "subscription", None) or config.get("subscription_name"),
        all_subscriptions=getattr(args, "all_subscriptions", False),
        resource_group=getattr(args, "resource_group", None),
    )
    builder = InventoryBuilder(logger=log)
    paths = builder.generate(records, output_dir=config.get("report_output_dir", "reports"))
    log.info("Discovery complete. %d certificates found.", len(records))
    log.info("Reports: %s", paths)
    
    # Send notification if configured
    if config.get("smtp_server") and config.get("notification_email"):
        from platform.ai_layer import AIOperationsLayer
        ai = AIOperationsLayer(logger=log)
        analysis = ai.analyze_inventory(records, 90)
        notifier = NotificationEngine(config=config, logger=log)
        notifier.send_risk_alert(analysis, attachments=[paths.get("md", "")])
    
    return records


def cmd_ai_report(args, client, log, config):
    log_banner(log, f"SSL Certificate Lifecycle Platform v{VERSION}", "Phase 6: AI Risk Analysis")
    days = getattr(args, "days", 90)
    
    # Load or re-discover records
    records = _load_or_discover(args, client, log, config)
    if not records:
        log.error("No certificate records available. Run 'discover' first.")
        return
    
    openai_key = os.environ.get("OPENAI_API_KEY", config.get("openai_api_key", ""))
    ai = AIOperationsLayer(logger=log, openai_api_key=openai_key)
    report_path = ai.write_risk_report(records, output_dir=config.get("report_output_dir", "reports"), days=days)
    
    analysis = ai.analyze_inventory(records, days)
    log.info("")
    log.info("RISK SUMMARY (%d day threshold)", days)
    log.info("  Overall Risk  : %s", analysis["overall_risk"])
    log.info("  Expiring Soon : %d", analysis["expiring_soon"])
    log.info("  Expired       : %d", analysis["expired"])
    log.info("")
    for cert in analysis.get("certificates_at_risk", []):
        log.info("  [%s] %s — %s", cert["risk_level"], cert["cert_name"], cert["narrative"])
    log.info("")
    log.info("Full report: %s", report_path)


def cmd_executive_summary(args, client, log, config):
    records = _load_or_discover(args, client, log, config)
    if not records:
        log.error("No certificate records available.")
        return
    ai = AIOperationsLayer(logger=log)
    summary = ai.generate_executive_summary(records)
    print(summary)
    path = os.path.join(config.get("report_output_dir", "reports"), "ExecutiveSummary.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(summary)
    log.info("Executive summary: %s", path)


def cmd_import(args, client, log, config):
    log_banner(log, f"SSL Certificate Lifecycle Platform v{VERSION}", "Phase 4: Key Vault Import")
    client.validate_login()
    
    cert_name = getattr(args, "cert", "") or config.get("cert_name", "")
    vault_name = getattr(args, "vault", "") or config.get("key_vault_name", "")
    pfx_path = getattr(args, "pfx", "") or config.get("pfx_path", "")
    
    mode = "preview"
    if getattr(args, "dry_run", False): mode = "dry-run"
    if getattr(args, "execute", False): mode = "execute"
    
    if not all([cert_name, vault_name, pfx_path]):
        log.error("Required: --cert, --vault (or config), --pfx")
        log.error("Example: python platform/main.py import --cert king-wildcard --vault tgna-kv-king-ctrl --pfx C:/certs/king5.pfx --preview")
        return
    
    kv_ops = KeyVaultOps(client=client, logger=log, config=config)
    result = kv_ops.import_certificate(
        vault_name=vault_name,
        cert_name=cert_name,
        pfx_path=pfx_path,
        mode=mode,
    )
    log.info("Import result: %s — %s", result["status"], result["message"])
    return result


def cmd_validate(args, client, log, config):
    log_banner(log, f"SSL Certificate Lifecycle Platform v{VERSION}", "Phase 5: Post-Import Validation")
    client.validate_login()
    cert_name = getattr(args, "cert", "") or config.get("cert_name", "")
    vault_name = getattr(args, "vault", "") or config.get("key_vault_name", "")
    app_svc = getattr(args, "app_service", "") or config.get("app_service_name", "")
    hostname = getattr(args, "hostname", "") or config.get("hostname", "")
    rg = getattr(args, "resource_group", "") or config.get("resource_group", "")
    
    validator = PostImportValidator(client=client, logger=log)
    results = validator.validate(
        vault_name=vault_name, cert_name=cert_name,
        app_service_name=app_svc, hostname=hostname, resource_group=rg,
    )
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    
    if config.get("smtp_server"):
        notifier = NotificationEngine(config=config, logger=log)
        notifier.send_validation_result(cert_name, vault_name, failed == 0, "reports/ValidationReport.md")
    return results


def cmd_jira_update(args, client, log, config):
    cert_name = getattr(args, "cert", "")
    stage = getattr(args, "stage", "")
    if not cert_name or not stage:
        log.error("Required: --cert CERT_NAME --stage STAGE")
        log.error("Stages: discovery-complete | renewal-started | renewal-complete | validation-complete | issue-detected | failure | risk-identified")
        return
    jt = JiraTemplates(logger=log)
    details = {"key_vault": config.get("key_vault_name", ""), "app_service": config.get("app_service_name", "")}
    template = jt.generate(cert_name, stage, details)
    print("")
    print("=" * 70)
    print("JIRA UPDATE (copy-paste ready)")
    print("=" * 70)
    print(template)
    print("=" * 70)
    path = os.path.join(config.get("report_output_dir", "reports"), f"JiraUpdate_{cert_name}_{stage}.md")
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(template)
    log.info("Jira update saved: %s", path)


def cmd_report(args, client, log, config):
    records = _load_or_discover(args, client, log, config)
    if not records:
        log.error("No records available.")
        return
    ai = AIOperationsLayer(logger=log)
    analysis = ai.analyze_inventory(records, 90)
    generator = ReportGenerator(logger=log)
    paths = generator.generate_all(records, analysis, config.get("report_output_dir", "reports"))
    log.info("All reports generated.")


def _load_or_discover(args, client, log, config):
    """Load records from inventory JSON if available, otherwise run discovery."""
    inv_path = os.path.join(config.get("report_output_dir", "reports"), "CertificateInventory.json")
    if os.path.isfile(inv_path):
        log.debug("Loading inventory from: %s", inv_path)
        with open(inv_path, encoding="utf-8") as f:
            data = json.load(f)
        from platform.discovery import CertificateRecord
        records = []
        for item in data.get("certificates", []):
            r = CertificateRecord()
            for k, v in item.items():
                if hasattr(r, k):
                    setattr(r, k, v)
            r.calculate_risk()
            records.append(r)
        return records
    log.info("No inventory found. Running discovery...")
    client.validate_login()
    discovery = CertificateDiscovery(client=client, logger=log, config=config)
    return discovery.run(subscription=config.get("subscription_name"))


def build_parser():
    parser = argparse.ArgumentParser(
        description=f"SSL Certificate Lifecycle Platform v{VERSION}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  health-check        Verify all prerequisites are met
  discover            Scan Azure and build certificate inventory
  ai-report           Generate AI-powered risk analysis report
  executive-summary   Generate executive-level summary
  import              Import certificate into Key Vault (preview/dry-run/execute)
  validate            Run post-import validation checks
  jira-update         Generate Jira ticket update text
  report              Generate all report formats

Examples:
  python platform/main.py health-check
  python platform/main.py discover --subscription "TGNA-PROD-C1"
  python platform/main.py ai-report --days 90
  python platform/main.py import --cert king-wildcard --pfx C:/certs/king5.pfx --preview
  python platform/main.py import --cert king-wildcard --pfx C:/certs/king5.pfx --execute
  python platform/main.py validate --cert king-wildcard --hostname king5.com
  python platform/main.py jira-update --cert king-wildcard --stage renewal-complete
""")
    sub = parser.add_subparsers(dest="command")
    
    sub.add_parser("health-check")
    
    disc = sub.add_parser("discover")
    disc.add_argument("--subscription", help="Azure subscription name")
    disc.add_argument("--all-subscriptions", action="store_true")
    disc.add_argument("--resource-group", help="Limit to resource group")
    
    ai = sub.add_parser("ai-report")
    ai.add_argument("--days", type=int, default=90)
    
    sub.add_parser("executive-summary")
    
    imp = sub.add_parser("import")
    imp.add_argument("--cert", required=True, help="Certificate name in Key Vault")
    imp.add_argument("--vault", help="Key Vault name (overrides config)")
    imp.add_argument("--pfx", help="Path to PFX file")
    imp.add_argument("--preview", action="store_true", default=False)
    imp.add_argument("--dry-run", dest="dry_run", action="store_true", default=False)
    imp.add_argument("--execute", action="store_true", default=False)
    
    val = sub.add_parser("validate")
    val.add_argument("--cert", help="Certificate name")
    val.add_argument("--vault", help="Key Vault name")
    val.add_argument("--app-service", dest="app_service")
    val.add_argument("--hostname")
    val.add_argument("--all", action="store_true")
    
    jira = sub.add_parser("jira-update")
    jira.add_argument("--cert", required=True)
    jira.add_argument("--stage", required=True)
    
    sub.add_parser("report")
    
    return parser


def main():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log, log_path = setup_logging(timestamp=ts)
    config = load_config()
    client = AzureClient(logger=log)
    
    parser = build_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    commands = {
        "health-check": cmd_health_check,
        "discover": cmd_discover,
        "ai-report": cmd_ai_report,
        "executive-summary": cmd_executive_summary,
        "import": cmd_import,
        "validate": cmd_validate,
        "jira-update": cmd_jira_update,
        "report": cmd_report,
    }
    
    fn = commands.get(args.command)
    if fn:
        fn(args, client, log, config)
    else:
        log.error("Unknown command: %s", args.command)
        parser.print_help()


if __name__ == "__main__":
    main()

