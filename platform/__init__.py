"""SSL Certificate Lifecycle Platform - Python Package."""

from platform.logger import setup_logging, get_logger
from platform.azure_client import AzureClient
from platform.discovery import CertificateDiscovery, CertificateRecord
from platform.inventory import InventoryBuilder
from platform.keyvault_ops import KeyVaultOps
from platform.validator import PostImportValidator
from platform.ai_layer import AIOperationsLayer
from platform.reporting import ReportGenerator
from platform.jira_templates import JiraTemplates
from platform.notifications import NotificationEngine

__version__ = "1.0.0"
__all__ = [
    "setup_logging", "get_logger",
    "AzureClient",
    "CertificateDiscovery", "CertificateRecord",
    "InventoryBuilder",
    "KeyVaultOps",
    "PostImportValidator",
    "AIOperationsLayer",
    "ReportGenerator",
    "JiraTemplates",
    "NotificationEngine",
]
