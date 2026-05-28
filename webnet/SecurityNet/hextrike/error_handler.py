# -*- coding: utf-8 -*-
"""从 hexstrike_server.py 提取的独立模块（弥娅 SecurityNet 移植）"""

import json
import logging
import os
import re
import time
import socket
import subprocess
import traceback
import threading
import queue
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

try:
    import requests
    import psutil
except ImportError:
    requests = None
    psutil = None

logger = logging.getLogger(__name__)


class ModernVisualEngine:
    """Beautiful, modern output formatting with animations and colors"""

    # Enhanced color palette with reddish tones and better highlighting
    COLORS = {
        "MATRIX_GREEN": "\033[38;5;46m",
        "NEON_BLUE": "\033[38;5;51m",
        "ELECTRIC_PURPLE": "\033[38;5;129m",
        "CYBER_ORANGE": "\033[38;5;208m",
        "HACKER_RED": "\033[38;5;196m",
        "TERMINAL_GRAY": "\033[38;5;240m",
        "BRIGHT_WHITE": "\033[97m",
        "RESET": "\033[0m",
        "BOLD": "\033[1m",
        "DIM": "\033[2m",
        # New reddish tones and highlighting colors
        "BLOOD_RED": "\033[38;5;124m",
        "CRIMSON": "\033[38;5;160m",
        "DARK_RED": "\033[38;5;88m",
        "FIRE_RED": "\033[38;5;202m",
        "ROSE_RED": "\033[38;5;167m",
        "BURGUNDY": "\033[38;5;52m",
        "SCARLET": "\033[38;5;197m",
        "RUBY": "\033[38;5;161m",
        # Unified theme primary/secondary (used going forward instead of legacy blue/green accents)
        "PRIMARY_BORDER": "\033[38;5;160m",  # CRIMSON
        "ACCENT_LINE": "\033[38;5;196m",  # HACKER_RED
        "ACCENT_GRADIENT": "\033[38;5;124m",  # BLOOD_RED (for subtle alternation)
        # Highlighting colors
        "HIGHLIGHT_RED": "\033[48;5;196m\033[38;5;15m",  # Red background, white text
        "HIGHLIGHT_YELLOW": "\033[48;5;226m\033[38;5;16m",  # Yellow background, black text
        "HIGHLIGHT_GREEN": "\033[48;5;46m\033[38;5;16m",  # Green background, black text
        "HIGHLIGHT_BLUE": "\033[48;5;51m\033[38;5;16m",  # Blue background, black text
        "HIGHLIGHT_PURPLE": "\033[48;5;129m\033[38;5;15m",  # Purple background, white text
        # Status colors with reddish tones
        "SUCCESS": "\033[38;5;46m",  # Bright green
        "WARNING": "\033[38;5;208m",  # Orange
        "ERROR": "\033[38;5;196m",  # Bright red
        "CRITICAL": "\033[48;5;196m\033[38;5;15m\033[1m",  # Red background, white bold text
        "INFO": "\033[38;5;51m",  # Cyan
        "DEBUG": "\033[38;5;240m",  # Gray
        # Vulnerability severity colors
        "VULN_CRITICAL": "\033[48;5;124m\033[38;5;15m\033[1m",  # Dark red background
        "VULN_HIGH": "\033[38;5;196m\033[1m",  # Bright red bold
        "VULN_MEDIUM": "\033[38;5;208m\033[1m",  # Orange bold
        "VULN_LOW": "\033[38;5;226m",  # Yellow
        "VULN_INFO": "\033[38;5;51m",  # Cyan
        # Tool status colors
        "TOOL_RUNNING": "\033[38;5;46m\033[5m",  # Blinking green
        "TOOL_SUCCESS": "\033[38;5;46m\033[1m",  # Bold green
        "TOOL_FAILED": "\033[38;5;196m\033[1m",  # Bold red
        "TOOL_TIMEOUT": "\033[38;5;208m\033[1m",  # Bold orange
        "TOOL_RECOVERY": "\033[38;5;129m\033[1m",  # Bold purple
        # Progress and animation colors
        "PROGRESS_BAR": "\033[38;5;46m",  # Green
        "PROGRESS_EMPTY": "\033[38;5;240m",  # Gray
        "SPINNER": "\033[38;5;51m",  # Cyan
        "PULSE": "\033[38;5;196m\033[5m",  # Blinking red
    }

    # Progress animation styles
    PROGRESS_STYLES = {
        "dots": ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"],
        "bars": ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"],
        "arrows": ["←", "↖", "↑", "↗", "→", "↘", "↓", "↙"],
        "pulse": ["●", "◐", "◑", "◒", "◓", "◔", "◕", "◖", "◗", "◘"],
    }

    @staticmethod
    def create_banner() -> str:
        """Create the enhanced HexStrike banner"""
        # Build a blood-red themed border using primary/gradient alternation
        border_color = ModernVisualEngine.COLORS["PRIMARY_BORDER"]
        accent = ModernVisualEngine.COLORS["ACCENT_LINE"]
        gradient = ModernVisualEngine.COLORS["ACCENT_GRADIENT"]
        RESET = ModernVisualEngine.COLORS["RESET"]
        BOLD = ModernVisualEngine.COLORS["BOLD"]
        title_block = f"{accent}{BOLD}"
        banner = f"""
{title_block}
██╗  ██╗███████╗██╗  ██╗███████╗████████╗██████╗ ██╗██╗  ██╗███████╗
██║  ██║██╔════╝╚██╗██╔╝██╔════╝╚══██╔══╝██╔══██╗██║██║ ██╔╝██╔════╝
███████║█████╗   ╚███╔╝ ███████╗   ██║   ██████╔╝██║█████╔╝ █████╗
██╔══██║██╔══╝   ██╔██╗ ╚════██║   ██║   ██╔══██╗██║██╔═██╗ ██╔══╝
██║  ██║███████╗██╔╝ ██╗███████║   ██║   ██║  ██║██║██║  ██╗███████╗
╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝╚═╝  ╚═╝╚══════╝
{RESET}
{border_color}┌─────────────────────────────────────────────────────────────────────┐
│  {ModernVisualEngine.COLORS["BRIGHT_WHITE"]}🚀 HexStrike AI - Blood-Red Offensive Intelligence Core{border_color}        │
│  {accent}⚡ AI-Automated Recon | Exploitation | Analysis Pipeline{border_color}          │
│  {gradient}🎯 Bug Bounty | CTF | Red Team | Zero-Day Research{border_color}              │
└─────────────────────────────────────────────────────────────────────┘{RESET}

{ModernVisualEngine.COLORS["TERMINAL_GRAY"]}[INFO] Server starting on {getattr(ModernVisualEngine, "API_HOST", "localhost")}:{getattr(ModernVisualEngine, "API_PORT", "8080")}
[INFO] 150+ integrated modules | Adaptive AI decision engine active
[INFO] Blood-red theme engaged – unified offensive operations UI{RESET}
"""
        return banner

    @staticmethod
    def create_progress_bar(current: int, total: int, width: int = 50, tool: str = "") -> str:
        """Create a beautiful progress bar with cyberpunk styling"""
        percentage = 0 if total == 0 else min(100, (current / total) * 100)

        filled = int(width * percentage / 100)
        bar = "█" * filled + "░" * (width - filled)

        border = ModernVisualEngine.COLORS["PRIMARY_BORDER"]
        fill_col = ModernVisualEngine.COLORS["ACCENT_LINE"]
        return f"""
{border}┌─ {tool} ─{"─" * (width - len(tool) - 4)}┐
│ {fill_col}{bar}{border} │ {percentage:6.1f}%
└─{"─" * (width + 10)}┘{ModernVisualEngine.COLORS["RESET"]}"""

    @staticmethod
    def render_progress_bar(
        progress: float, width: int = 40, style: str = "cyber", label: str = "", eta: float = 0, speed: str = ""
    ) -> str:
        """Render a beautiful progress bar with multiple styles"""

        # Clamp progress between 0 and 1
        progress = max(0.0, min(1.0, progress))

        # Calculate filled and empty portions
        filled_width = int(width * progress)
        empty_width = width - filled_width

        # Style-specific rendering
        if style == "cyber":
            filled_char = "█"
            empty_char = "░"
            bar_color = ModernVisualEngine.COLORS["ACCENT_LINE"]
            progress_color = ModernVisualEngine.COLORS["PRIMARY_BORDER"]
        elif style == "matrix":
            filled_char = "▓"
            empty_char = "▒"
            bar_color = ModernVisualEngine.COLORS["ACCENT_LINE"]
            progress_color = ModernVisualEngine.COLORS["ACCENT_GRADIENT"]
        elif style == "neon":
            filled_char = "━"
            empty_char = "─"
            bar_color = ModernVisualEngine.COLORS["PRIMARY_BORDER"]
            progress_color = ModernVisualEngine.COLORS["CYBER_ORANGE"]
        else:  # default
            filled_char = "█"
            empty_char = "░"
            bar_color = ModernVisualEngine.COLORS["ACCENT_LINE"]
            progress_color = ModernVisualEngine.COLORS["PRIMARY_BORDER"]

        # Build the progress bar
        filled_part = bar_color + filled_char * filled_width
        empty_part = ModernVisualEngine.COLORS["TERMINAL_GRAY"] + empty_char * empty_width
        percentage = f"{progress * 100:.1f}%"

        # Add ETA and speed if provided
        extra_info = ""
        if eta > 0:
            extra_info += f" ETA: {eta:.1f}s"
        if speed:
            extra_info += f" Speed: {speed}"

        # Build final progress bar
        bar_display = f"[{filled_part}{empty_part}{ModernVisualEngine.COLORS['RESET']}] {progress_color}{percentage}{ModernVisualEngine.COLORS['RESET']}"

        if label:
            return f"{label}: {bar_display}{extra_info}"
        else:
            return f"{bar_display}{extra_info}"

    @staticmethod
    def create_live_dashboard(processes: Dict[int, Dict[str, Any]]) -> str:
        """Create a live dashboard showing all active processes"""

        if not processes:
            return f"""
{ModernVisualEngine.COLORS["PRIMARY_BORDER"]}╭─────────────────────────────────────────────────────────────────────────────╮
│ {ModernVisualEngine.COLORS["ACCENT_LINE"]}📊 HEXSTRIKE LIVE DASHBOARD{ModernVisualEngine.COLORS["PRIMARY_BORDER"]}                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│ {ModernVisualEngine.COLORS["TERMINAL_GRAY"]}No active processes currently running{ModernVisualEngine.COLORS["PRIMARY_BORDER"]}                                    │
╰─────────────────────────────────────────────────────────────────────────────╯{ModernVisualEngine.COLORS["RESET"]}
"""

        dashboard_lines = [
            f"{ModernVisualEngine.COLORS['PRIMARY_BORDER']}╭─────────────────────────────────────────────────────────────────────────────╮",
            f"│ {ModernVisualEngine.COLORS['ACCENT_LINE']}📊 HEXSTRIKE LIVE DASHBOARD{ModernVisualEngine.COLORS['PRIMARY_BORDER']}                                           │",
            f"├─────────────────────────────────────────────────────────────────────────────┤",
        ]

        for pid, proc_info in processes.items():
            status = proc_info.get("status", "unknown")
            command = (
                proc_info.get("command", "unknown")[:50] + "..."
                if len(proc_info.get("command", "")) > 50
                else proc_info.get("command", "unknown")
            )
            status_color = (
                ModernVisualEngine.COLORS["ACCENT_LINE"]
                if status == "running"
                else ModernVisualEngine.COLORS["HACKER_RED"]
            )

            dashboard_lines.append(
                f"│ {ModernVisualEngine.COLORS['CYBER_ORANGE']}PID {pid}{ModernVisualEngine.COLORS['PRIMARY_BORDER']} | {status_color}{status}{ModernVisualEngine.COLORS['PRIMARY_BORDER']} | {ModernVisualEngine.COLORS['BRIGHT_WHITE']}{command}{ModernVisualEngine.COLORS['PRIMARY_BORDER']} │"
            )

        dashboard_lines.append(
            f"╰─────────────────────────────────────────────────────────────────────────────╯{ModernVisualEngine.COLORS['RESET']}"
        )

        return "\n".join(dashboard_lines)

    @staticmethod
    def format_vulnerability_card(vuln_data: Dict[str, Any]) -> str:
        """Format vulnerability as a beautiful card"""
        severity = vuln_data.get("severity", "unknown").upper()
        name = vuln_data.get("name", "Unknown Vulnerability")
        description = vuln_data.get("description", "No description available")

        # Severity color mapping
        severity_colors = {
            "CRITICAL": ModernVisualEngine.COLORS["VULN_CRITICAL"],
            "HIGH": ModernVisualEngine.COLORS["HACKER_RED"],
            "MEDIUM": ModernVisualEngine.COLORS["ACCENT_GRADIENT"],
            "LOW": ModernVisualEngine.COLORS["CYBER_ORANGE"],
            "INFO": ModernVisualEngine.COLORS["TERMINAL_GRAY"],
        }

        color = severity_colors.get(severity, ModernVisualEngine.COLORS["TERMINAL_GRAY"])

        return f"""
{color}┌─ 🚨 VULNERABILITY DETECTED ─────────────────────────────────────┐
│ {ModernVisualEngine.COLORS["BRIGHT_WHITE"]}{name:<60}{color} │
│ {ModernVisualEngine.COLORS["TERMINAL_GRAY"]}Severity: {color}{severity:<52}{color} │
│ {ModernVisualEngine.COLORS["TERMINAL_GRAY"]}{description[:58]:<58}{color} │
└─────────────────────────────────────────────────────────────────┘{ModernVisualEngine.COLORS["RESET"]}"""

    @staticmethod
    def format_error_card(error_type: str, tool_name: str, error_message: str, recovery_action: str = "") -> str:
        """Format error information as a highlighted card with reddish tones"""
        error_colors = {
            "CRITICAL": ModernVisualEngine.COLORS["VULN_CRITICAL"],
            "ERROR": ModernVisualEngine.COLORS["TOOL_FAILED"],
            "TIMEOUT": ModernVisualEngine.COLORS["TOOL_TIMEOUT"],
            "RECOVERY": ModernVisualEngine.COLORS["TOOL_RECOVERY"],
            "WARNING": ModernVisualEngine.COLORS["WARNING"],
        }

        color = error_colors.get(error_type.upper(), ModernVisualEngine.COLORS["ERROR"])

        card = f"""
{color}┌─ 🔥 ERROR DETECTED ─────────────────────────────────────────────┐{ModernVisualEngine.COLORS["RESET"]}
{color}│ {ModernVisualEngine.COLORS["BRIGHT_WHITE"]}Tool: {tool_name:<55}{color} │{ModernVisualEngine.COLORS["RESET"]}
{color}│ {ModernVisualEngine.COLORS["BRIGHT_WHITE"]}Type: {error_type:<55}{color} │{ModernVisualEngine.COLORS["RESET"]}
{color}│ {ModernVisualEngine.COLORS["BRIGHT_WHITE"]}Error: {error_message[:53]:<53}{color} │{ModernVisualEngine.COLORS["RESET"]}"""

        if recovery_action:
            card += f"""
{color}│ {ModernVisualEngine.COLORS["TOOL_RECOVERY"]}Recovery: {recovery_action[:50]:<50}{color} │{ModernVisualEngine.COLORS["RESET"]}"""

        card += f"""
{color}└─────────────────────────────────────────────────────────────────┘{ModernVisualEngine.COLORS["RESET"]}"""

        return card

    @staticmethod
    def format_tool_status(tool_name: str, status: str, target: str = "", progress: float = 0.0) -> str:
        """Format tool execution status with enhanced highlighting"""
        status_colors = {
            "RUNNING": ModernVisualEngine.COLORS["TOOL_RUNNING"],
            "SUCCESS": ModernVisualEngine.COLORS["TOOL_SUCCESS"],
            "FAILED": ModernVisualEngine.COLORS["TOOL_FAILED"],
            "TIMEOUT": ModernVisualEngine.COLORS["TOOL_TIMEOUT"],
            "RECOVERY": ModernVisualEngine.COLORS["TOOL_RECOVERY"],
        }

        color = status_colors.get(status.upper(), ModernVisualEngine.COLORS["INFO"])

        # Create progress bar if progress > 0
        progress_bar = ""
        if progress > 0:
            filled = int(20 * progress)
            empty = 20 - filled
            progress_bar = f" [{ModernVisualEngine.COLORS['PROGRESS_BAR']}{'█' * filled}{ModernVisualEngine.COLORS['PROGRESS_EMPTY']}{'░' * empty}{ModernVisualEngine.COLORS['RESET']}] {progress * 100:.1f}%"

        return f"{color}🔧 {tool_name.upper()}{ModernVisualEngine.COLORS['RESET']} | {color}{status}{ModernVisualEngine.COLORS['RESET']} | {ModernVisualEngine.COLORS['BRIGHT_WHITE']}{target}{ModernVisualEngine.COLORS['RESET']}{progress_bar}"

    @staticmethod
    def format_highlighted_text(text: str, highlight_type: str = "RED") -> str:
        """Format text with highlighting background"""
        highlight_colors = {
            "RED": ModernVisualEngine.COLORS["HIGHLIGHT_RED"],
            "YELLOW": ModernVisualEngine.COLORS["HIGHLIGHT_YELLOW"],
            "GREEN": ModernVisualEngine.COLORS["HIGHLIGHT_GREEN"],
            "BLUE": ModernVisualEngine.COLORS["HIGHLIGHT_BLUE"],
            "PURPLE": ModernVisualEngine.COLORS["HIGHLIGHT_PURPLE"],
        }

        color = highlight_colors.get(highlight_type.upper(), ModernVisualEngine.COLORS["HIGHLIGHT_RED"])
        return f"{color} {text} {ModernVisualEngine.COLORS['RESET']}"

    @staticmethod
    def format_vulnerability_severity(severity: str, count: int = 0) -> str:
        """Format vulnerability severity with appropriate colors"""
        severity_colors = {
            "CRITICAL": ModernVisualEngine.COLORS["VULN_CRITICAL"],
            "HIGH": ModernVisualEngine.COLORS["VULN_HIGH"],
            "MEDIUM": ModernVisualEngine.COLORS["VULN_MEDIUM"],
            "LOW": ModernVisualEngine.COLORS["VULN_LOW"],
            "INFO": ModernVisualEngine.COLORS["VULN_INFO"],
        }

        color = severity_colors.get(severity.upper(), ModernVisualEngine.COLORS["INFO"])
        count_text = f" ({count})" if count > 0 else ""

        return f"{color}{severity.upper()}{count_text}{ModernVisualEngine.COLORS['RESET']}"

    @staticmethod
    def create_section_header(title: str, icon: str = "🔥", color: str = "FIRE_RED") -> str:
        """Create a section header with reddish styling"""
        header_color = ModernVisualEngine.COLORS.get(color, ModernVisualEngine.COLORS["FIRE_RED"])

        return f"""
{header_color}{"═" * 70}{ModernVisualEngine.COLORS["RESET"]}
{header_color}{icon} {title.upper()}{ModernVisualEngine.COLORS["RESET"]}
{header_color}{"═" * 70}{ModernVisualEngine.COLORS["RESET"]}"""

    @staticmethod
    def format_command_execution(command: str, status: str, duration: float = 0.0) -> str:
        """Format command execution with enhanced styling"""
        status_colors = {
            "STARTING": ModernVisualEngine.COLORS["INFO"],
            "RUNNING": ModernVisualEngine.COLORS["TOOL_RUNNING"],
            "SUCCESS": ModernVisualEngine.COLORS["TOOL_SUCCESS"],
            "FAILED": ModernVisualEngine.COLORS["TOOL_FAILED"],
            "TIMEOUT": ModernVisualEngine.COLORS["TOOL_TIMEOUT"],
        }

        color = status_colors.get(status.upper(), ModernVisualEngine.COLORS["INFO"])
        duration_text = f" ({duration:.2f}s)" if duration > 0 else ""

        return f"{color}▶ {command[:60]}{'...' if len(command) > 60 else ''} | {status.upper()}{duration_text}{ModernVisualEngine.COLORS['RESET']}"


# ============================================================================
# INTELLIGENT DECISION ENGINE (v6.0 ENHANCEMENT)
# ============================================================================


class ErrorType(Enum):
    """Enumeration of different error types for intelligent handling"""

    TIMEOUT = "timeout"
    PERMISSION_DENIED = "permission_denied"
    NETWORK_UNREACHABLE = "network_unreachable"
    RATE_LIMITED = "rate_limited"
    TOOL_NOT_FOUND = "tool_not_found"
    INVALID_PARAMETERS = "invalid_parameters"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    AUTHENTICATION_FAILED = "authentication_failed"
    TARGET_UNREACHABLE = "target_unreachable"
    PARSING_ERROR = "parsing_error"
    UNKNOWN = "unknown"


class RecoveryAction(Enum):
    """Types of recovery actions that can be taken"""

    RETRY_WITH_BACKOFF = "retry_with_backoff"
    RETRY_WITH_REDUCED_SCOPE = "retry_with_reduced_scope"
    SWITCH_TO_ALTERNATIVE_TOOL = "switch_to_alternative_tool"
    ADJUST_PARAMETERS = "adjust_parameters"
    ESCALATE_TO_HUMAN = "escalate_to_human"
    GRACEFUL_DEGRADATION = "graceful_degradation"
    ABORT_OPERATION = "abort_operation"


@dataclass
class ErrorContext:
    """Context information for error handling decisions"""

    tool_name: str
    target: str
    parameters: Dict[str, Any]
    error_type: ErrorType
    error_message: str
    attempt_count: int
    timestamp: datetime
    stack_trace: str
    system_resources: Dict[str, Any]
    previous_errors: List["ErrorContext"] = field(default_factory=list)


@dataclass
class RecoveryStrategy:
    """Recovery strategy with configuration"""

    action: RecoveryAction
    parameters: Dict[str, Any]
    max_attempts: int
    backoff_multiplier: float
    success_probability: float
    estimated_time: int  # seconds


class IntelligentErrorHandler:
    """Advanced error handling with automatic recovery strategies"""

    def __init__(self):
        self.error_patterns = self._initialize_error_patterns()
        self.recovery_strategies = self._initialize_recovery_strategies()
        self.tool_alternatives = self._initialize_tool_alternatives()
        self.parameter_adjustments = self._initialize_parameter_adjustments()
        self.error_history = []
        self.max_history_size = 1000

    def _initialize_error_patterns(self) -> Dict[str, ErrorType]:
        """Initialize error pattern recognition"""
        return {
            # Timeout patterns
            r"timeout|timed out|connection timeout|read timeout": ErrorType.TIMEOUT,
            r"operation timed out|command timeout": ErrorType.TIMEOUT,
            # Permission patterns
            r"permission denied|access denied|forbidden|not authorized": ErrorType.PERMISSION_DENIED,
            r"sudo required|root required|insufficient privileges": ErrorType.PERMISSION_DENIED,
            # Network patterns
            r"network unreachable|host unreachable|no route to host": ErrorType.NETWORK_UNREACHABLE,
            r"connection refused|connection reset|network error": ErrorType.NETWORK_UNREACHABLE,
            # Rate limiting patterns
            r"rate limit|too many requests|throttled|429": ErrorType.RATE_LIMITED,
            r"request limit exceeded|quota exceeded": ErrorType.RATE_LIMITED,
            # Tool not found patterns
            r"command not found|no such file or directory|not found": ErrorType.TOOL_NOT_FOUND,
            r"executable not found|binary not found": ErrorType.TOOL_NOT_FOUND,
            # Parameter patterns
            r"invalid argument|invalid option|unknown option": ErrorType.INVALID_PARAMETERS,
            r"bad parameter|invalid parameter|syntax error": ErrorType.INVALID_PARAMETERS,
            # Resource patterns
            r"out of memory|memory error|disk full|no space left": ErrorType.RESOURCE_EXHAUSTED,
            r"resource temporarily unavailable|too many open files": ErrorType.RESOURCE_EXHAUSTED,
            # Authentication patterns
            r"authentication failed|login failed|invalid credentials": ErrorType.AUTHENTICATION_FAILED,
            r"unauthorized|invalid token|expired token": ErrorType.AUTHENTICATION_FAILED,
            # Target patterns
            r"target unreachable|target not responding|target down": ErrorType.TARGET_UNREACHABLE,
            r"host not found|dns resolution failed": ErrorType.TARGET_UNREACHABLE,
            # Parsing patterns
            r"parse error|parsing failed|invalid format|malformed": ErrorType.PARSING_ERROR,
            r"json decode error|xml parse error|invalid json": ErrorType.PARSING_ERROR,
        }

    def _initialize_recovery_strategies(self) -> Dict[ErrorType, List[RecoveryStrategy]]:
        """Initialize recovery strategies for different error types"""
        return {
            ErrorType.TIMEOUT: [
                RecoveryStrategy(
                    action=RecoveryAction.RETRY_WITH_BACKOFF,
                    parameters={"initial_delay": 5, "max_delay": 60},
                    max_attempts=3,
                    backoff_multiplier=2.0,
                    success_probability=0.7,
                    estimated_time=30,
                ),
                RecoveryStrategy(
                    action=RecoveryAction.RETRY_WITH_REDUCED_SCOPE,
                    parameters={"reduce_threads": True, "reduce_timeout": True},
                    max_attempts=2,
                    backoff_multiplier=1.0,
                    success_probability=0.8,
                    estimated_time=45,
                ),
                RecoveryStrategy(
                    action=RecoveryAction.SWITCH_TO_ALTERNATIVE_TOOL,
                    parameters={"prefer_faster_tools": True},
                    max_attempts=1,
                    backoff_multiplier=1.0,
                    success_probability=0.6,
                    estimated_time=60,
                ),
            ],
            ErrorType.PERMISSION_DENIED: [
                RecoveryStrategy(
                    action=RecoveryAction.ESCALATE_TO_HUMAN,
                    parameters={"message": "Privilege escalation required", "urgency": "medium"},
                    max_attempts=1,
                    backoff_multiplier=1.0,
                    success_probability=0.9,
                    estimated_time=300,
                ),
                RecoveryStrategy(
                    action=RecoveryAction.SWITCH_TO_ALTERNATIVE_TOOL,
                    parameters={"require_no_privileges": True},
                    max_attempts=1,
                    backoff_multiplier=1.0,
                    success_probability=0.5,
                    estimated_time=30,
                ),
            ],
            ErrorType.NETWORK_UNREACHABLE: [
                RecoveryStrategy(
                    action=RecoveryAction.RETRY_WITH_BACKOFF,
                    parameters={"initial_delay": 10, "max_delay": 120},
                    max_attempts=3,
                    backoff_multiplier=2.0,
                    success_probability=0.6,
                    estimated_time=60,
                ),
                RecoveryStrategy(
                    action=RecoveryAction.SWITCH_TO_ALTERNATIVE_TOOL,
                    parameters={"prefer_offline_tools": True},
                    max_attempts=1,
                    backoff_multiplier=1.0,
                    success_probability=0.4,
                    estimated_time=30,
                ),
            ],
            ErrorType.RATE_LIMITED: [
                RecoveryStrategy(
                    action=RecoveryAction.RETRY_WITH_BACKOFF,
                    parameters={"initial_delay": 30, "max_delay": 300},
                    max_attempts=5,
                    backoff_multiplier=1.5,
                    success_probability=0.9,
                    estimated_time=180,
                ),
                RecoveryStrategy(
                    action=RecoveryAction.ADJUST_PARAMETERS,
                    parameters={"reduce_rate": True, "increase_delays": True},
                    max_attempts=2,
                    backoff_multiplier=1.0,
                    success_probability=0.8,
                    estimated_time=120,
                ),
            ],
            ErrorType.TOOL_NOT_FOUND: [
                RecoveryStrategy(
                    action=RecoveryAction.SWITCH_TO_ALTERNATIVE_TOOL,
                    parameters={"find_equivalent": True},
                    max_attempts=1,
                    backoff_multiplier=1.0,
                    success_probability=0.7,
                    estimated_time=15,
                ),
                RecoveryStrategy(
                    action=RecoveryAction.ESCALATE_TO_HUMAN,
                    parameters={"message": "Tool installation required", "urgency": "low"},
                    max_attempts=1,
                    backoff_multiplier=1.0,
                    success_probability=0.9,
                    estimated_time=600,
                ),
            ],
            ErrorType.INVALID_PARAMETERS: [
                RecoveryStrategy(
                    action=RecoveryAction.ADJUST_PARAMETERS,
                    parameters={"use_defaults": True, "remove_invalid": True},
                    max_attempts=3,
                    backoff_multiplier=1.0,
                    success_probability=0.8,
                    estimated_time=10,
                ),
                RecoveryStrategy(
                    action=RecoveryAction.SWITCH_TO_ALTERNATIVE_TOOL,
                    parameters={"simpler_interface": True},
                    max_attempts=1,
                    backoff_multiplier=1.0,
                    success_probability=0.6,
                    estimated_time=30,
                ),
            ],
            ErrorType.RESOURCE_EXHAUSTED: [
                RecoveryStrategy(
                    action=RecoveryAction.RETRY_WITH_REDUCED_SCOPE,
                    parameters={"reduce_memory": True, "reduce_threads": True},
                    max_attempts=2,
                    backoff_multiplier=1.0,
                    success_probability=0.7,
                    estimated_time=60,
                ),
                RecoveryStrategy(
                    action=RecoveryAction.RETRY_WITH_BACKOFF,
                    parameters={"initial_delay": 60, "max_delay": 300},
                    max_attempts=2,
                    backoff_multiplier=2.0,
                    success_probability=0.5,
                    estimated_time=180,
                ),
            ],
            ErrorType.AUTHENTICATION_FAILED: [
                RecoveryStrategy(
                    action=RecoveryAction.ESCALATE_TO_HUMAN,
                    parameters={"message": "Authentication credentials required", "urgency": "high"},
                    max_attempts=1,
                    backoff_multiplier=1.0,
                    success_probability=0.9,
                    estimated_time=300,
                ),
                RecoveryStrategy(
                    action=RecoveryAction.SWITCH_TO_ALTERNATIVE_TOOL,
                    parameters={"no_auth_required": True},
                    max_attempts=1,
                    backoff_multiplier=1.0,
                    success_probability=0.4,
                    estimated_time=30,
                ),
            ],
            ErrorType.TARGET_UNREACHABLE: [
                RecoveryStrategy(
                    action=RecoveryAction.RETRY_WITH_BACKOFF,
                    parameters={"initial_delay": 15, "max_delay": 180},
                    max_attempts=3,
                    backoff_multiplier=2.0,
                    success_probability=0.6,
                    estimated_time=90,
                ),
                RecoveryStrategy(
                    action=RecoveryAction.GRACEFUL_DEGRADATION,
                    parameters={"skip_target": True, "continue_with_others": True},
                    max_attempts=1,
                    backoff_multiplier=1.0,
                    success_probability=1.0,
                    estimated_time=5,
                ),
            ],
            ErrorType.PARSING_ERROR: [
                RecoveryStrategy(
                    action=RecoveryAction.ADJUST_PARAMETERS,
                    parameters={"change_output_format": True, "add_parsing_flags": True},
                    max_attempts=2,
                    backoff_multiplier=1.0,
                    success_probability=0.7,
                    estimated_time=20,
                ),
                RecoveryStrategy(
                    action=RecoveryAction.SWITCH_TO_ALTERNATIVE_TOOL,
                    parameters={"better_output_format": True},
                    max_attempts=1,
                    backoff_multiplier=1.0,
                    success_probability=0.6,
                    estimated_time=30,
                ),
            ],
            ErrorType.UNKNOWN: [
                RecoveryStrategy(
                    action=RecoveryAction.RETRY_WITH_BACKOFF,
                    parameters={"initial_delay": 5, "max_delay": 30},
                    max_attempts=2,
                    backoff_multiplier=2.0,
                    success_probability=0.3,
                    estimated_time=45,
                ),
                RecoveryStrategy(
                    action=RecoveryAction.ESCALATE_TO_HUMAN,
                    parameters={"message": "Unknown error encountered", "urgency": "medium"},
                    max_attempts=1,
                    backoff_multiplier=1.0,
                    success_probability=0.9,
                    estimated_time=300,
                ),
            ],
        }

    def _initialize_tool_alternatives(self) -> Dict[str, List[str]]:
        """Initialize alternative tools for fallback scenarios"""
        return {
            # Network scanning alternatives
            "nmap": ["rustscan", "masscan", "zmap"],
            "rustscan": ["nmap", "masscan"],
            "masscan": ["nmap", "rustscan", "zmap"],
            # Directory/file discovery alternatives
            "gobuster": ["feroxbuster", "dirsearch", "ffuf", "dirb"],
            "feroxbuster": ["gobuster", "dirsearch", "ffuf"],
            "dirsearch": ["gobuster", "feroxbuster", "ffuf"],
            "ffuf": ["gobuster", "feroxbuster", "dirsearch"],
            # Vulnerability scanning alternatives
            "nuclei": ["jaeles", "nikto", "w3af"],
            "jaeles": ["nuclei", "nikto"],
            "nikto": ["nuclei", "jaeles", "w3af"],
            # Web crawling alternatives
            "katana": ["gau", "waybackurls", "hakrawler"],
            "gau": ["katana", "waybackurls", "hakrawler"],
            "waybackurls": ["gau", "katana", "hakrawler"],
            # Parameter discovery alternatives
            "arjun": ["paramspider", "x8", "ffuf"],
            "paramspider": ["arjun", "x8"],
            "x8": ["arjun", "paramspider"],
            # SQL injection alternatives
            "sqlmap": ["sqlninja", "jsql-injection"],
            # XSS testing alternatives
            "dalfox": ["xsser", "xsstrike"],
            # Subdomain enumeration alternatives
            "subfinder": ["amass", "assetfinder", "findomain"],
            "amass": ["subfinder", "assetfinder", "findomain"],
            "assetfinder": ["subfinder", "amass", "findomain"],
            # Cloud security alternatives
            "prowler": ["scout-suite", "cloudmapper"],
            "scout-suite": ["prowler", "cloudmapper"],
            # Container security alternatives
            "trivy": ["clair", "docker-bench-security"],
            "clair": ["trivy", "docker-bench-security"],
            # Binary analysis alternatives
            "ghidra": ["radare2", "ida", "binary-ninja"],
            "radare2": ["ghidra", "objdump", "gdb"],
            "gdb": ["radare2", "lldb"],
            # Exploitation alternatives
            "pwntools": ["ropper", "ropgadget"],
            "ropper": ["ropgadget", "pwntools"],
            "ropgadget": ["ropper", "pwntools"],
        }

    def _initialize_parameter_adjustments(self) -> Dict[str, Dict[ErrorType, Dict[str, Any]]]:
        """Initialize parameter adjustments for different error types and tools"""
        return {
            "nmap": {
                ErrorType.TIMEOUT: {"timing": "-T2", "reduce_ports": True},
                ErrorType.RATE_LIMITED: {"timing": "-T1", "delay": "1000ms"},
                ErrorType.RESOURCE_EXHAUSTED: {"max_parallelism": "10"},
            },
            "gobuster": {
                ErrorType.TIMEOUT: {"threads": "10", "timeout": "30s"},
                ErrorType.RATE_LIMITED: {"threads": "5", "delay": "1s"},
                ErrorType.RESOURCE_EXHAUSTED: {"threads": "5"},
            },
            "nuclei": {
                ErrorType.TIMEOUT: {"concurrency": "10", "timeout": "30"},
                ErrorType.RATE_LIMITED: {"rate-limit": "10", "concurrency": "5"},
                ErrorType.RESOURCE_EXHAUSTED: {"concurrency": "5"},
            },
            "feroxbuster": {
                ErrorType.TIMEOUT: {"threads": "10", "timeout": "30"},
                ErrorType.RATE_LIMITED: {"threads": "5", "rate-limit": "10"},
                ErrorType.RESOURCE_EXHAUSTED: {"threads": "5"},
            },
            "ffuf": {
                ErrorType.TIMEOUT: {"threads": "10", "timeout": "30"},
                ErrorType.RATE_LIMITED: {"threads": "5", "rate": "10"},
                ErrorType.RESOURCE_EXHAUSTED: {"threads": "5"},
            },
        }

    def classify_error(self, error_message: str, exception: Exception = None) -> ErrorType:
        """Classify error based on message and exception type"""
        error_text = error_message.lower()

        # Check exception type first
        if exception:
            if isinstance(exception, TimeoutError):
                return ErrorType.TIMEOUT
            elif isinstance(exception, PermissionError):
                return ErrorType.PERMISSION_DENIED
            elif isinstance(exception, ConnectionError):
                return ErrorType.NETWORK_UNREACHABLE
            elif isinstance(exception, FileNotFoundError):
                return ErrorType.TOOL_NOT_FOUND

        # Check error patterns
        for pattern, error_type in self.error_patterns.items():
            if re.search(pattern, error_text, re.IGNORECASE):
                return error_type

        return ErrorType.UNKNOWN

    def handle_tool_failure(self, tool: str, error: Exception, context: Dict[str, Any]) -> RecoveryStrategy:
        """Determine best recovery action for tool failures"""
        error_message = str(error)
        error_type = self.classify_error(error_message, error)

        # Create error context
        error_context = ErrorContext(
            tool_name=tool,
            target=context.get("target", "unknown"),
            parameters=context.get("parameters", {}),
            error_type=error_type,
            error_message=error_message,
            attempt_count=context.get("attempt_count", 1),
            timestamp=datetime.now(),
            stack_trace=traceback.format_exc(),
            system_resources=self._get_system_resources(),
        )

        # Add to error history
        self._add_to_history(error_context)

        # Get recovery strategies for this error type
        strategies = self.recovery_strategies.get(error_type, self.recovery_strategies[ErrorType.UNKNOWN])

        # Select best strategy based on context
        best_strategy = self._select_best_strategy(strategies, error_context)

        error_message = f"{error_type.value} - Applying {best_strategy.action.value}"
        logger.warning(f"{ModernVisualEngine.format_error_card('RECOVERY', tool, error_message)}")

        return best_strategy

    def _select_best_strategy(self, strategies: List[RecoveryStrategy], context: ErrorContext) -> RecoveryStrategy:
        """Select the best recovery strategy based on context"""
        # Filter strategies based on attempt count
        viable_strategies = [s for s in strategies if context.attempt_count <= s.max_attempts]

        if not viable_strategies:
            # If all strategies exhausted, escalate to human
            return RecoveryStrategy(
                action=RecoveryAction.ESCALATE_TO_HUMAN,
                parameters={"message": f"All recovery strategies exhausted for {context.tool_name}", "urgency": "high"},
                max_attempts=1,
                backoff_multiplier=1.0,
                success_probability=0.9,
                estimated_time=300,
            )

        # Score strategies based on success probability and estimated time
        scored_strategies = []
        for strategy in viable_strategies:
            # Adjust success probability based on previous failures
            adjusted_probability = strategy.success_probability * (0.9 ** (context.attempt_count - 1))

            # Prefer strategies with higher success probability and lower time
            score = adjusted_probability - (strategy.estimated_time / 1000.0)
            scored_strategies.append((score, strategy))

        # Return strategy with highest score
        scored_strategies.sort(key=lambda x: x[0], reverse=True)
        return scored_strategies[0][1]

    def auto_adjust_parameters(
        self, tool: str, error_type: ErrorType, original_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Automatically adjust tool parameters based on error patterns"""
        adjustments = self.parameter_adjustments.get(tool, {}).get(error_type, {})

        if not adjustments:
            # Generic adjustments based on error type
            if error_type == ErrorType.TIMEOUT:
                adjustments = {"timeout": "60", "threads": "5"}
            elif error_type == ErrorType.RATE_LIMITED:
                adjustments = {"delay": "2s", "threads": "3"}
            elif error_type == ErrorType.RESOURCE_EXHAUSTED:
                adjustments = {"threads": "3", "memory_limit": "1G"}

        # Apply adjustments to original parameters
        adjusted_params = original_params.copy()
        adjusted_params.update(adjustments)

        adjustment_info = f"Parameters adjusted: {adjustments}"
        logger.info(f"{ModernVisualEngine.format_tool_status(tool, 'RECOVERY', adjustment_info)}")

        return adjusted_params

    def get_alternative_tool(self, failed_tool: str, context: Dict[str, Any]) -> Optional[str]:
        """Get alternative tool for failed tool"""
        alternatives = self.tool_alternatives.get(failed_tool, [])

        if not alternatives:
            return None

        # Filter alternatives based on context requirements
        filtered_alternatives = []
        for alt in alternatives:
            if context.get("require_no_privileges") and alt in ["nmap", "masscan"]:
                continue  # Skip tools that typically require privileges
            if context.get("prefer_faster_tools") and alt in ["amass", "w3af"]:
                continue  # Skip slower tools
            filtered_alternatives.append(alt)

        if not filtered_alternatives:
            filtered_alternatives = alternatives

        # Return first available alternative
        return filtered_alternatives[0] if filtered_alternatives else None

    def escalate_to_human(self, context: ErrorContext, urgency: str = "medium") -> Dict[str, Any]:
        """Escalate complex errors to human operator with full context"""
        escalation_data = {
            "timestamp": context.timestamp.isoformat(),
            "tool": context.tool_name,
            "target": context.target,
            "error_type": context.error_type.value,
            "error_message": context.error_message,
            "attempt_count": context.attempt_count,
            "urgency": urgency,
            "suggested_actions": self._get_human_suggestions(context),
            "context": {
                "parameters": context.parameters,
                "system_resources": context.system_resources,
                "recent_errors": [e.error_message for e in context.previous_errors[-5:]],
            },
        }

        # Log escalation with enhanced formatting
        logger.error(
            f"{ModernVisualEngine.format_error_card('CRITICAL', context.tool_name, context.error_message, 'HUMAN ESCALATION REQUIRED')}"
        )
        logger.error(f"{ModernVisualEngine.format_highlighted_text('ESCALATION DETAILS', 'RED')}")
        logger.error(f"{json.dumps(escalation_data, indent=2)}")

        return escalation_data

    def _get_human_suggestions(self, context: ErrorContext) -> List[str]:
        """Get human-readable suggestions for error resolution"""
        suggestions = []

        if context.error_type == ErrorType.PERMISSION_DENIED:
            suggestions.extend(
                [
                    "Run the command with sudo privileges",
                    "Check file/directory permissions",
                    "Verify user is in required groups",
                ]
            )
        elif context.error_type == ErrorType.TOOL_NOT_FOUND:
            suggestions.extend(
                [
                    f"Install {context.tool_name} using package manager",
                    "Check if tool is in PATH",
                    "Verify tool installation",
                ]
            )
        elif context.error_type == ErrorType.NETWORK_UNREACHABLE:
            suggestions.extend(["Check network connectivity", "Verify target is accessible", "Check firewall rules"])
        elif context.error_type == ErrorType.RATE_LIMITED:
            suggestions.extend(["Wait before retrying", "Use slower scan rates", "Check API rate limits"])
        else:
            suggestions.append("Review error details and logs")

        return suggestions

    def _get_system_resources(self) -> Dict[str, Any]:
        """Get current system resource information"""
        try:
            return {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage("/").percent,
                "load_average": os.getloadavg() if hasattr(os, "getloadavg") else None,
                "active_processes": len(psutil.pids()),
            }
        except Exception:
            return {"error": "Unable to get system resources"}

    def _add_to_history(self, error_context: ErrorContext):
        """Add error context to history"""
        self.error_history.append(error_context)

        # Maintain history size limit
        if len(self.error_history) > self.max_history_size:
            self.error_history = self.error_history[-self.max_history_size :]

    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics for monitoring"""
        if not self.error_history:
            return {"total_errors": 0}

        error_counts = {}
        tool_errors = {}
        recent_errors = []

        # Count errors by type and tool
        for error in self.error_history:
            error_type = error.error_type.value
            tool = error.tool_name

            error_counts[error_type] = error_counts.get(error_type, 0) + 1
            tool_errors[tool] = tool_errors.get(tool, 0) + 1

            # Recent errors (last hour)
            if (datetime.now() - error.timestamp).total_seconds() < 3600:
                recent_errors.append({"tool": tool, "error_type": error_type, "timestamp": error.timestamp.isoformat()})

        return {
            "total_errors": len(self.error_history),
            "error_counts_by_type": error_counts,
            "error_counts_by_tool": tool_errors,
            "recent_errors_count": len(recent_errors),
            "recent_errors": recent_errors[-10:],  # Last 10 recent errors
        }


class GracefulDegradation:
    """Ensure system continues operating even with partial tool failures"""

    def __init__(self):
        self.fallback_chains = self._initialize_fallback_chains()
        self.critical_operations = self._initialize_critical_operations()

    def _initialize_fallback_chains(self) -> Dict[str, List[List[str]]]:
        """Initialize fallback tool chains for critical operations"""
        return {
            "network_discovery": [
                ["nmap", "rustscan", "masscan"],
                ["rustscan", "nmap"],
                ["ping", "telnet"],  # Basic fallback
            ],
            "web_discovery": [
                ["gobuster", "feroxbuster", "dirsearch"],
                ["feroxbuster", "ffuf"],
                ["curl", "wget"],  # Basic fallback
            ],
            "vulnerability_scanning": [
                ["nuclei", "jaeles", "nikto"],
                ["nikto", "w3af"],
                ["curl"],  # Basic manual testing
            ],
            "subdomain_enumeration": [
                ["subfinder", "amass", "assetfinder"],
                ["amass", "findomain"],
                ["dig", "nslookup"],  # Basic DNS tools
            ],
            "parameter_discovery": [
                ["arjun", "paramspider", "x8"],
                ["ffuf", "wfuzz"],
                ["manual_testing"],  # Manual parameter testing
            ],
        }

    def _initialize_critical_operations(self) -> Set[str]:
        """Initialize set of critical operations that must not fail completely"""
        return {"network_discovery", "web_discovery", "vulnerability_scanning", "subdomain_enumeration"}

    def create_fallback_chain(self, operation: str, failed_tools: List[str] = None) -> List[str]:
        """Create fallback tool chain for critical operations"""
        if failed_tools is None:
            failed_tools = []

        chains = self.fallback_chains.get(operation, [])

        # Find first chain that doesn't contain failed tools
        for chain in chains:
            viable_chain = [tool for tool in chain if tool not in failed_tools]
            if viable_chain:
                logger.info(f"🔄 Fallback chain for {operation}: {viable_chain}")
                return viable_chain

        # If no viable chain found, return basic fallback
        basic_fallbacks = {
            "network_discovery": ["ping"],
            "web_discovery": ["curl"],
            "vulnerability_scanning": ["curl"],
            "subdomain_enumeration": ["dig"],
        }

        fallback = basic_fallbacks.get(operation, ["manual_testing"])
        logger.warning(f"⚠️  Using basic fallback for {operation}: {fallback}")
        return fallback

    def handle_partial_failure(
        self, operation: str, partial_results: Dict[str, Any], failed_components: List[str]
    ) -> Dict[str, Any]:
        """Handle partial results and fill gaps with alternative methods"""

        enhanced_results = partial_results.copy()
        enhanced_results["degradation_info"] = {
            "operation": operation,
            "failed_components": failed_components,
            "partial_success": True,
            "fallback_applied": True,
            "timestamp": datetime.now().isoformat(),
        }

        # Try to fill gaps based on operation type
        if operation == "network_discovery" and "open_ports" not in partial_results:
            # Try basic port check if full scan failed
            enhanced_results["open_ports"] = self._basic_port_check(partial_results.get("target"))

        elif operation == "web_discovery" and "directories" not in partial_results:
            # Try basic directory check
            enhanced_results["directories"] = self._basic_directory_check(partial_results.get("target"))

        elif operation == "vulnerability_scanning" and "vulnerabilities" not in partial_results:
            # Provide basic security headers check
            enhanced_results["vulnerabilities"] = self._basic_security_check(partial_results.get("target"))

        # Add recommendations for manual follow-up
        enhanced_results["manual_recommendations"] = self._get_manual_recommendations(operation, failed_components)

        logger.info(f"🛡️  Graceful degradation applied for {operation}")
        return enhanced_results

    def _basic_port_check(self, target: str) -> List[int]:
        """Basic port connectivity check"""
        if not target:
            return []

        common_ports = [21, 22, 23, 25, 53, 80, 110, 143, 443, 993, 995]
        open_ports = []

        for port in common_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex((target, port))
                if result == 0:
                    open_ports.append(port)
                sock.close()
            except Exception:
                continue

        return open_ports

    def _basic_directory_check(self, target: str) -> List[str]:
        """Basic directory existence check"""
        if not target:
            return []

        common_dirs = ["/admin", "/login", "/api", "/wp-admin", "/phpmyadmin", "/robots.txt"]
        found_dirs = []

        for directory in common_dirs:
            try:
                url = f"{target.rstrip('/')}{directory}"
                response = requests.head(url, timeout=5, allow_redirects=True)
                if response.status_code in [200, 301, 302, 403]:
                    found_dirs.append(directory)
            except Exception:
                continue

        return found_dirs

    def _basic_security_check(self, target: str) -> List[Dict[str, Any]]:
        """Basic security headers check"""
        if not target:
            return []

        vulnerabilities = []

        try:
            response = requests.get(target, timeout=10)
            headers = response.headers

            # Check for missing security headers
            security_headers = {
                "X-Frame-Options": "Clickjacking protection missing",
                "X-Content-Type-Options": "MIME type sniffing protection missing",
                "X-XSS-Protection": "XSS protection missing",
                "Strict-Transport-Security": "HTTPS enforcement missing",
                "Content-Security-Policy": "Content Security Policy missing",
            }

            for header, description in security_headers.items():
                if header not in headers:
                    vulnerabilities.append(
                        {
                            "type": "missing_security_header",
                            "severity": "medium",
                            "description": description,
                            "header": header,
                        }
                    )

        except Exception as e:
            vulnerabilities.append(
                {
                    "type": "connection_error",
                    "severity": "info",
                    "description": f"Could not perform basic security check: {str(e)}",
                }
            )

        return vulnerabilities

    def _get_manual_recommendations(self, operation: str, failed_components: List[str]) -> List[str]:
        """Get manual recommendations for failed operations"""
        recommendations = []

        base_recommendations = {
            "network_discovery": [
                "Manually test common ports using telnet or nc",
                "Check for service banners manually",
                "Use online port scanners as alternative",
            ],
            "web_discovery": [
                "Manually browse common directories",
                "Check robots.txt and sitemap.xml",
                "Use browser developer tools for endpoint discovery",
            ],
            "vulnerability_scanning": [
                "Manually test for common vulnerabilities",
                "Check security headers using browser tools",
                "Perform manual input validation testing",
            ],
            "subdomain_enumeration": [
                "Use online subdomain discovery tools",
                "Check certificate transparency logs",
                "Perform manual DNS queries",
            ],
        }

        recommendations.extend(base_recommendations.get(operation, []))

        # Add specific recommendations based on failed components
        for component in failed_components:
            if component == "nmap":
                recommendations.append("Consider using online port scanners")
            elif component == "gobuster":
                recommendations.append("Try manual directory browsing")
            elif component == "nuclei":
                recommendations.append("Perform manual vulnerability testing")

        return recommendations

    def is_critical_operation(self, operation: str) -> bool:
        """Check if operation is critical and requires fallback"""
        return operation in self.critical_operations


# Global error handler and degradation manager instances
error_handler = IntelligentErrorHandler()
degradation_manager = GracefulDegradation()
