"""Native Python honeypots for NeuroTrap (no Docker required)."""

from .base import BaseHoneypot, HoneypotSession
from .ftp_honeypot import FTPHoneypot
from .http_honeypot import HTTPHoneypot
from .manager import HONEYPOT_TYPES, HoneypotManager
from .ssh_honeypot import SSHHoneypot, PARAMIKO_AVAILABLE
from .telnet_honeypot import TelnetHoneypot

__all__ = [
    "BaseHoneypot",
    "HoneypotSession",
    "HoneypotManager",
    "HONEYPOT_TYPES",
    "SSHHoneypot",
    "HTTPHoneypot",
    "FTPHoneypot",
    "TelnetHoneypot",
    "PARAMIKO_AVAILABLE",
]
