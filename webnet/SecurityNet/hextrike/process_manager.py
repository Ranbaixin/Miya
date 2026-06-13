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

from .decision_engine import TargetProfile, TargetType, TechnologyStack


class TechnologyDetector:
    """Advanced technology detection system for context-aware parameter selection"""

    def __init__(self):
        self.detection_patterns = {
            "web_servers": {
                "apache": ["Apache", "apache", "httpd"],
                "nginx": ["nginx", "Nginx"],
                "iis": ["Microsoft-IIS", "IIS"],
                "tomcat": ["Tomcat", "Apache-Coyote"],
                "jetty": ["Jetty"],
                "lighttpd": ["lighttpd"],
            },
            "frameworks": {
                "django": ["Django", "django", "csrftoken"],
                "flask": ["Flask", "Werkzeug"],
                "express": ["Express", "X-Powered-By: Express"],
                "laravel": ["Laravel", "laravel_session"],
                "symfony": ["Symfony", "symfony"],
                "rails": ["Ruby on Rails", "rails", "_session_id"],
                "spring": ["Spring", "JSESSIONID"],
                "struts": ["Struts", "struts"],
            },
            "cms": {
                "wordpress": ["wp-content", "wp-includes", "WordPress", "/wp-admin/"],
                "drupal": ["Drupal", "drupal", "/sites/default/", "X-Drupal-Cache"],
                "joomla": ["Joomla", "joomla", "/administrator/", "com_content"],
                "magento": ["Magento", "magento", "Mage.Cookies"],
                "prestashop": ["PrestaShop", "prestashop"],
                "opencart": ["OpenCart", "opencart"],
            },
            "databases": {
                "mysql": ["MySQL", "mysql", "phpMyAdmin"],
                "postgresql": ["PostgreSQL", "postgres"],
                "mssql": ["Microsoft SQL Server", "MSSQL"],
                "oracle": ["Oracle", "oracle"],
                "mongodb": ["MongoDB", "mongo"],
                "redis": ["Redis", "redis"],
            },
            "languages": {
                "php": ["PHP", "php", ".php", "X-Powered-By: PHP"],
                "python": ["Python", "python", ".py"],
                "java": ["Java", "java", ".jsp", ".do"],
                "dotnet": ["ASP.NET", ".aspx", ".asp", "X-AspNet-Version"],
                "nodejs": ["Node.js", "node", ".js"],
                "ruby": ["Ruby", "ruby", ".rb"],
                "go": ["Go", "golang"],
                "rust": ["Rust", "rust"],
            },
            "security": {
                "waf": ["cloudflare", "CloudFlare", "X-CF-Ray", "incapsula", "Incapsula", "sucuri", "Sucuri"],
                "load_balancer": ["F5", "BigIP", "HAProxy", "nginx", "AWS-ALB"],
                "cdn": ["CloudFront", "Fastly", "KeyCDN", "MaxCDN", "Cloudflare"],
            },
        }

        self.port_services = {
            21: "ftp",
            22: "ssh",
            23: "telnet",
            25: "smtp",
            53: "dns",
            80: "http",
            110: "pop3",
            143: "imap",
            443: "https",
            993: "imaps",
            995: "pop3s",
            1433: "mssql",
            3306: "mysql",
            5432: "postgresql",
            6379: "redis",
            27017: "mongodb",
            8080: "http-alt",
            8443: "https-alt",
            9200: "elasticsearch",
            11211: "memcached",
        }

    def detect_technologies(
        self, target: str, headers: Dict[str, str] = None, content: str = "", ports: List[int] = None
    ) -> Dict[str, List[str]]:
        """Comprehensive technology detection"""
        detected = {
            "web_servers": [],
            "frameworks": [],
            "cms": [],
            "databases": [],
            "languages": [],
            "security": [],
            "services": [],
        }

        # Header-based detection
        if headers:
            for category, tech_patterns in self.detection_patterns.items():
                for tech, patterns in tech_patterns.items():
                    for header_name, header_value in headers.items():
                        for pattern in patterns:
                            if pattern.lower() in header_value.lower() or pattern.lower() in header_name.lower():
                                if tech not in detected[category]:
                                    detected[category].append(tech)

        # Content-based detection
        if content:
            content_lower = content.lower()
            for category, tech_patterns in self.detection_patterns.items():
                for tech, patterns in tech_patterns.items():
                    for pattern in patterns:
                        if pattern.lower() in content_lower:
                            if tech not in detected[category]:
                                detected[category].append(tech)

        # Port-based service detection
        if ports:
            for port in ports:
                if port in self.port_services:
                    service = self.port_services[port]
                    if service not in detected["services"]:
                        detected["services"].append(service)

        return detected


class RateLimitDetector:
    """Intelligent rate limiting detection and automatic timing adjustment"""

    def __init__(self):
        self.rate_limit_indicators = [
            "rate limit",
            "too many requests",
            "429",
            "throttle",
            "slow down",
            "retry after",
            "quota exceeded",
            "api limit",
            "request limit",
        ]

        self.timing_profiles = {
            "aggressive": {"delay": 0.1, "threads": 50, "timeout": 5},
            "normal": {"delay": 0.5, "threads": 20, "timeout": 10},
            "conservative": {"delay": 1.0, "threads": 10, "timeout": 15},
            "stealth": {"delay": 2.0, "threads": 5, "timeout": 30},
        }

    def detect_rate_limiting(
        self, response_text: str, status_code: int, headers: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """Detect rate limiting from response"""
        rate_limit_detected = False
        confidence = 0.0
        indicators_found = []

        # Status code check
        if status_code == 429:
            rate_limit_detected = True
            confidence += 0.8
            indicators_found.append("HTTP 429 status")

        # Response text check
        response_lower = response_text.lower()
        for indicator in self.rate_limit_indicators:
            if indicator in response_lower:
                rate_limit_detected = True
                confidence += 0.2
                indicators_found.append(f"Text: '{indicator}'")

        # Header check
        if headers:
            rate_limit_headers = ["x-ratelimit", "retry-after", "x-rate-limit"]
            for header_name in headers.keys():
                for rl_header in rate_limit_headers:
                    if rl_header.lower() in header_name.lower():
                        rate_limit_detected = True
                        confidence += 0.3
                        indicators_found.append(f"Header: {header_name}")

        confidence = min(1.0, confidence)

        return {
            "detected": rate_limit_detected,
            "confidence": confidence,
            "indicators": indicators_found,
            "recommended_profile": self._recommend_timing_profile(confidence),
        }

    def _recommend_timing_profile(self, confidence: float) -> str:
        """Recommend timing profile based on rate limit confidence"""
        if confidence >= 0.8:
            return "stealth"
        elif confidence >= 0.5:
            return "conservative"
        elif confidence >= 0.2:
            return "normal"
        else:
            return "aggressive"

    def adjust_timing(self, current_params: Dict[str, Any], profile: str) -> Dict[str, Any]:
        """Adjust timing parameters based on profile"""
        timing = self.timing_profiles.get(profile, self.timing_profiles["normal"])

        adjusted_params = current_params.copy()

        # Adjust common parameters
        if "threads" in adjusted_params:
            adjusted_params["threads"] = timing["threads"]
        if "delay" in adjusted_params:
            adjusted_params["delay"] = timing["delay"]
        if "timeout" in adjusted_params:
            adjusted_params["timeout"] = timing["timeout"]

        # Tool-specific adjustments
        if "additional_args" in adjusted_params:
            args = adjusted_params["additional_args"]

            # Remove existing timing arguments
            args = re.sub(r"-t\s+\d+", "", args)
            args = re.sub(r"--threads\s+\d+", "", args)
            args = re.sub(r"--delay\s+[\d.]+", "", args)

            # Add new timing arguments
            args += f" -t {timing['threads']}"
            if timing["delay"] > 0:
                args += f" --delay {timing['delay']}"

            adjusted_params["additional_args"] = args.strip()

        return adjusted_params


class FailureRecoverySystem:
    """Intelligent failure recovery with alternative tool selection"""

    def __init__(self):
        self.tool_alternatives = {
            "nmap": ["rustscan", "masscan", "zmap"],
            "gobuster": ["dirsearch", "feroxbuster", "dirb"],
            "sqlmap": ["sqlninja", "bbqsql", "jsql-injection"],
            "nuclei": ["nikto", "w3af", "skipfish"],
            "hydra": ["medusa", "ncrack", "patator"],
            "hashcat": ["john", "ophcrack", "rainbowcrack"],
            "amass": ["subfinder", "sublist3r", "assetfinder"],
            "ffuf": ["wfuzz", "gobuster", "dirb"],
        }

        self.failure_patterns = {
            "timeout": ["timeout", "timed out", "connection timeout"],
            "permission_denied": ["permission denied", "access denied", "forbidden"],
            "not_found": ["not found", "command not found", "no such file"],
            "network_error": ["network unreachable", "connection refused", "host unreachable"],
            "rate_limited": ["rate limit", "too many requests", "throttled"],
            "authentication_required": ["authentication required", "unauthorized", "login required"],
        }

    def analyze_failure(self, error_output: str, exit_code: int) -> Dict[str, Any]:
        """Analyze failure and suggest recovery strategies"""
        failure_type = "unknown"
        confidence = 0.0
        recovery_strategies = []

        error_lower = error_output.lower()

        # Identify failure type
        for failure, patterns in self.failure_patterns.items():
            for pattern in patterns:
                if pattern in error_lower:
                    failure_type = failure
                    confidence += 0.3
                    break

        # Exit code analysis
        if exit_code == 1:
            confidence += 0.1
        elif exit_code == 124:  # timeout
            failure_type = "timeout"
            confidence += 0.5
        elif exit_code == 126:  # permission denied
            failure_type = "permission_denied"
            confidence += 0.5

        confidence = min(1.0, confidence)

        # Generate recovery strategies
        if failure_type == "timeout":
            recovery_strategies = [
                "Increase timeout values",
                "Reduce thread count",
                "Use alternative faster tool",
                "Split target into smaller chunks",
            ]
        elif failure_type == "permission_denied":
            recovery_strategies = [
                "Run with elevated privileges",
                "Check file permissions",
                "Use alternative tool with different approach",
            ]
        elif failure_type == "rate_limited":
            recovery_strategies = [
                "Implement delays between requests",
                "Reduce thread count",
                "Use stealth timing profile",
                "Rotate IP addresses if possible",
            ]
        elif failure_type == "network_error":
            recovery_strategies = [
                "Check network connectivity",
                "Try alternative network routes",
                "Use proxy or VPN",
                "Verify target is accessible",
            ]

        return {
            "failure_type": failure_type,
            "confidence": confidence,
            "recovery_strategies": recovery_strategies,
            "alternative_tools": self.tool_alternatives.get(self._extract_tool_name(error_output), []),
        }

    def _extract_tool_name(self, error_output: str) -> str:
        """Extract tool name from error output"""
        for tool in self.tool_alternatives.keys():
            if tool in error_output.lower():
                return tool
        return "unknown"


class PerformanceMonitor:
    """Advanced performance monitoring with automatic resource allocation"""

    def __init__(self):
        self.performance_metrics = {}
        self.resource_thresholds = {"cpu_high": 80.0, "memory_high": 85.0, "disk_high": 90.0, "network_high": 80.0}

        self.optimization_rules = {
            "high_cpu": {"reduce_threads": 0.5, "increase_delay": 2.0, "enable_nice": True},
            "high_memory": {"reduce_batch_size": 0.6, "enable_streaming": True, "clear_cache": True},
            "high_disk": {"reduce_output_verbosity": True, "enable_compression": True, "cleanup_temp_files": True},
            "high_network": {
                "reduce_concurrent_connections": 0.7,
                "increase_timeout": 1.5,
                "enable_connection_pooling": True,
            },
        }

    def monitor_system_resources(self) -> Dict[str, float]:
        """Monitor current system resource usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            network = psutil.net_io_counters()

            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": disk.percent,
                "network_bytes_sent": network.bytes_sent,
                "network_bytes_recv": network.bytes_recv,
                "timestamp": time.time(),
            }
        except Exception as e:
            logger.error(f"Error monitoring system resources: {str(e)}")
            return {}

    def optimize_based_on_resources(
        self, current_params: Dict[str, Any], resource_usage: Dict[str, float]
    ) -> Dict[str, Any]:
        """Optimize parameters based on current resource usage"""
        optimized_params = current_params.copy()
        optimizations_applied = []

        # CPU optimization
        if resource_usage.get("cpu_percent", 0) > self.resource_thresholds["cpu_high"]:
            if "threads" in optimized_params:
                original_threads = optimized_params["threads"]
                optimized_params["threads"] = max(
                    1, int(original_threads * self.optimization_rules["high_cpu"]["reduce_threads"])
                )
                optimizations_applied.append(
                    f"Reduced threads from {original_threads} to {optimized_params['threads']}"
                )

            if "delay" in optimized_params:
                original_delay = optimized_params.get("delay", 0)
                optimized_params["delay"] = original_delay * self.optimization_rules["high_cpu"]["increase_delay"]
                optimizations_applied.append(f"Increased delay to {optimized_params['delay']}")

        # Memory optimization
        if resource_usage.get("memory_percent", 0) > self.resource_thresholds["memory_high"]:
            if "batch_size" in optimized_params:
                original_batch = optimized_params["batch_size"]
                optimized_params["batch_size"] = max(
                    1, int(original_batch * self.optimization_rules["high_memory"]["reduce_batch_size"])
                )
                optimizations_applied.append(
                    f"Reduced batch size from {original_batch} to {optimized_params['batch_size']}"
                )

        # Network optimization
        if "network_bytes_sent" in resource_usage:
            # Simple heuristic for high network usage
            if resource_usage["network_bytes_sent"] > 1000000:  # 1MB/s
                if "concurrent_connections" in optimized_params:
                    original_conn = optimized_params["concurrent_connections"]
                    optimized_params["concurrent_connections"] = max(
                        1, int(original_conn * self.optimization_rules["high_network"]["reduce_concurrent_connections"])
                    )
                    optimizations_applied.append(
                        f"Reduced concurrent connections to {optimized_params['concurrent_connections']}"
                    )

        optimized_params["_optimizations_applied"] = optimizations_applied
        return optimized_params


class ParameterOptimizer:
    """Advanced parameter optimization system with intelligent context-aware selection"""

    def __init__(self):
        self.tech_detector = TechnologyDetector()
        self.rate_limiter = RateLimitDetector()
        self.failure_recovery = FailureRecoverySystem()
        self.performance_monitor = PerformanceMonitor()

        # Tool-specific optimization profiles
        self.optimization_profiles = {
            "nmap": {
                "stealth": {
                    "scan_type": "-sS",
                    "timing": "-T2",
                    "additional_args": "--max-retries 1 --host-timeout 300s",
                },
                "normal": {"scan_type": "-sS -sV", "timing": "-T4", "additional_args": "--max-retries 2"},
                "aggressive": {
                    "scan_type": "-sS -sV -sC -O",
                    "timing": "-T5",
                    "additional_args": "--max-retries 3 --min-rate 1000",
                },
            },
            "gobuster": {
                "stealth": {"threads": 5, "delay": "1s", "timeout": "30s"},
                "normal": {"threads": 20, "delay": "0s", "timeout": "10s"},
                "aggressive": {"threads": 50, "delay": "0s", "timeout": "5s"},
            },
            "sqlmap": {
                "stealth": {"level": 1, "risk": 1, "threads": 1, "delay": 1},
                "normal": {"level": 2, "risk": 2, "threads": 5, "delay": 0},
                "aggressive": {"level": 3, "risk": 3, "threads": 10, "delay": 0},
            },
        }

    def optimize_parameters_advanced(
        self, tool: str, target_profile: TargetProfile, context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Advanced parameter optimization with full intelligence"""
        if context is None:
            context = {}

        # Get base parameters
        base_params = self._get_base_parameters(tool, target_profile)

        # Detect technologies for context-aware optimization
        detected_tech = self.tech_detector.detect_technologies(
            target_profile.target,
            headers=context.get("headers", {}),
            content=context.get("content", ""),
            ports=target_profile.open_ports,
        )

        # Apply technology-specific optimizations
        tech_optimized_params = self._apply_technology_optimizations(tool, base_params, detected_tech)

        # Monitor system resources and optimize accordingly
        resource_usage = self.performance_monitor.monitor_system_resources()
        resource_optimized_params = self.performance_monitor.optimize_based_on_resources(
            tech_optimized_params, resource_usage
        )

        # Apply profile-based optimizations
        profile = context.get("optimization_profile", "normal")
        profile_optimized_params = self._apply_profile_optimizations(tool, resource_optimized_params, profile)

        # Add metadata
        profile_optimized_params["_optimization_metadata"] = {
            "detected_technologies": detected_tech,
            "resource_usage": resource_usage,
            "optimization_profile": profile,
            "optimizations_applied": resource_optimized_params.get("_optimizations_applied", []),
            "timestamp": datetime.now().isoformat(),
        }

        return profile_optimized_params

    def _get_base_parameters(self, tool: str, profile: TargetProfile) -> Dict[str, Any]:
        """Get base parameters for a tool"""
        base_params = {"target": profile.target}

        # Tool-specific base parameters
        if tool == "nmap":
            base_params.update({"scan_type": "-sS", "ports": "1-1000", "timing": "-T4"})
        elif tool == "gobuster":
            base_params.update(
                {
                    "mode": "dir",
                    "threads": 20,
                    "wordlist": "/usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt",
                }
            )
        elif tool == "sqlmap":
            base_params.update({"batch": True, "level": 1, "risk": 1})
        elif tool == "nuclei":
            base_params.update({"severity": "critical,high,medium", "threads": 25})

        return base_params

    def _apply_technology_optimizations(
        self, tool: str, params: Dict[str, Any], detected_tech: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """Apply technology-specific optimizations"""
        optimized_params = params.copy()

        # Web server optimizations
        if "apache" in detected_tech.get("web_servers", []):
            if tool == "gobuster":
                optimized_params["extensions"] = "php,html,txt,xml,conf"
            elif tool == "nuclei":
                optimized_params["tags"] = optimized_params.get("tags", "") + ",apache"

        elif "nginx" in detected_tech.get("web_servers", []):
            if tool == "gobuster":
                optimized_params["extensions"] = "php,html,txt,json,conf"
            elif tool == "nuclei":
                optimized_params["tags"] = optimized_params.get("tags", "") + ",nginx"

        # CMS optimizations
        if "wordpress" in detected_tech.get("cms", []):
            if tool == "gobuster":
                optimized_params["extensions"] = "php,html,txt,xml"
                optimized_params["additional_paths"] = "/wp-content/,/wp-admin/,/wp-includes/"
            elif tool == "nuclei":
                optimized_params["tags"] = optimized_params.get("tags", "") + ",wordpress"
            elif tool == "wpscan":
                optimized_params["enumerate"] = "ap,at,cb,dbe"

        # Language-specific optimizations
        if "php" in detected_tech.get("languages", []):
            if tool == "gobuster":
                optimized_params["extensions"] = "php,php3,php4,php5,phtml,html"
            elif tool == "sqlmap":
                optimized_params["dbms"] = "mysql"

        elif "dotnet" in detected_tech.get("languages", []):
            if tool == "gobuster":
                optimized_params["extensions"] = "aspx,asp,html,txt"
            elif tool == "sqlmap":
                optimized_params["dbms"] = "mssql"

        # Security feature adaptations
        if detected_tech.get("security", []):
            # WAF detected - use stealth mode
            if any(waf in detected_tech["security"] for waf in ["cloudflare", "incapsula", "sucuri"]):
                optimized_params["_stealth_mode"] = True
                if tool == "gobuster":
                    optimized_params["threads"] = min(optimized_params.get("threads", 20), 5)
                    optimized_params["delay"] = "2s"
                elif tool == "sqlmap":
                    optimized_params["delay"] = 2
                    optimized_params["randomize"] = True

        return optimized_params

    def _apply_profile_optimizations(self, tool: str, params: Dict[str, Any], profile: str) -> Dict[str, Any]:
        """Apply optimization profile settings"""
        if tool not in self.optimization_profiles:
            return params

        profile_settings = self.optimization_profiles[tool].get(profile, {})
        optimized_params = params.copy()

        # Apply profile-specific settings
        for key, value in profile_settings.items():
            optimized_params[key] = value

        # Handle stealth mode flag
        if params.get("_stealth_mode", False) and profile != "stealth":
            # Force stealth settings even if different profile requested
            stealth_settings = self.optimization_profiles[tool].get("stealth", {})
            for key, value in stealth_settings.items():
                optimized_params[key] = value

        return optimized_params

    def handle_tool_failure(
        self, tool: str, error_output: str, exit_code: int, current_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle tool failure and suggest recovery"""
        failure_analysis = self.failure_recovery.analyze_failure(error_output, exit_code)

        recovery_plan = {
            "original_tool": tool,
            "failure_analysis": failure_analysis,
            "recovery_actions": [],
            "alternative_tools": failure_analysis["alternative_tools"],
            "adjusted_parameters": current_params.copy(),
        }

        # Apply automatic parameter adjustments based on failure type
        if failure_analysis["failure_type"] == "timeout":
            if "timeout" in recovery_plan["adjusted_parameters"]:
                recovery_plan["adjusted_parameters"]["timeout"] *= 2
            if "threads" in recovery_plan["adjusted_parameters"]:
                recovery_plan["adjusted_parameters"]["threads"] = max(
                    1, recovery_plan["adjusted_parameters"]["threads"] // 2
                )
            recovery_plan["recovery_actions"].append("Increased timeout and reduced threads")

        elif failure_analysis["failure_type"] == "rate_limited":
            timing_profile = self.rate_limiter.adjust_timing(recovery_plan["adjusted_parameters"], "stealth")
            recovery_plan["adjusted_parameters"].update(timing_profile)
            recovery_plan["recovery_actions"].append("Applied stealth timing profile")

        return recovery_plan


# ============================================================================
# ADVANCED PROCESS MANAGEMENT AND MONITORING (v10.0 ENHANCEMENT)
# ============================================================================


class ProcessPool:
    """Intelligent process pool with auto-scaling capabilities"""

    def __init__(self, min_workers=2, max_workers=20, scale_threshold=0.8):
        self.min_workers = min_workers
        self.max_workers = max_workers
        self.scale_threshold = scale_threshold
        self.workers = []
        self.task_queue = queue.Queue()
        self.results = {}
        self.pool_lock = threading.Lock()
        self.active_tasks = {}
        self._workers_initialized = False
        self.performance_metrics = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "avg_task_time": 0.0,
            "cpu_usage": 0.0,
            "memory_usage": 0.0,
        }

        # Start monitoring thread (lightweight, no workers yet)
        self.monitor_thread = threading.Thread(target=self._monitor_performance, daemon=True)
        self.monitor_thread.start()

    def _ensure_workers(self):
        """Lazy-initialize worker threads on first task submission"""
        if not self._workers_initialized:
            self._workers_initialized = True
            self._scale_up(self.min_workers)

    def submit_task(self, task_id: str, func, *args, **kwargs) -> str:
        """Submit a task to the process pool"""
        self._ensure_workers()  # Lazy init on first use
        task = {
            "id": task_id,
            "func": func,
            "args": args,
            "kwargs": kwargs,
            "submitted_at": time.time(),
            "status": "queued",
        }

        with self.pool_lock:
            self.active_tasks[task_id] = task
            self.task_queue.put(task)

        logger.info(f"📋 Task submitted to pool: {task_id}")
        return task_id

    def get_task_result(self, task_id: str) -> Dict[str, Any]:
        """Get result of a submitted task"""
        with self.pool_lock:
            if task_id in self.results:
                return self.results[task_id]
            elif task_id in self.active_tasks:
                return {"status": self.active_tasks[task_id]["status"], "result": None}
            else:
                return {"status": "not_found", "result": None}

    def _worker_thread(self, worker_id: int):
        """Worker thread that processes tasks"""
        logger.info(f"🔧 Process pool worker {worker_id} started")

        while True:
            try:
                # Get task from queue with timeout
                task = self.task_queue.get(timeout=30)
                if task is None:  # Shutdown signal
                    break

                task_id = task["id"]
                start_time = time.time()

                # Update task status
                with self.pool_lock:
                    if task_id in self.active_tasks:
                        self.active_tasks[task_id]["status"] = "running"
                        self.active_tasks[task_id]["worker_id"] = worker_id
                        self.active_tasks[task_id]["started_at"] = start_time

                try:
                    # Execute task
                    result = task["func"](*task["args"], **task["kwargs"])

                    # Store result
                    execution_time = time.time() - start_time
                    with self.pool_lock:
                        self.results[task_id] = {
                            "status": "completed",
                            "result": result,
                            "execution_time": execution_time,
                            "worker_id": worker_id,
                            "completed_at": time.time(),
                        }

                        # Update performance metrics
                        self.performance_metrics["tasks_completed"] += 1
                        self.performance_metrics["avg_task_time"] = (
                            self.performance_metrics["avg_task_time"]
                            * (self.performance_metrics["tasks_completed"] - 1)
                            + execution_time
                        ) / self.performance_metrics["tasks_completed"]

                        # Remove from active tasks
                        if task_id in self.active_tasks:
                            del self.active_tasks[task_id]

                    logger.info(f"✅ Task completed: {task_id} in {execution_time:.2f}s")

                except Exception as e:
                    # Handle task failure
                    with self.pool_lock:
                        self.results[task_id] = {
                            "status": "failed",
                            "error": str(e),
                            "execution_time": time.time() - start_time,
                            "worker_id": worker_id,
                            "failed_at": time.time(),
                        }

                        self.performance_metrics["tasks_failed"] += 1

                        if task_id in self.active_tasks:
                            del self.active_tasks[task_id]

                    logger.error(f"❌ Task failed: {task_id} - {str(e)}")

                self.task_queue.task_done()

            except queue.Empty:
                # No tasks available, continue waiting
                continue
            except Exception as e:
                logger.error(f"💥 Worker {worker_id} error: {str(e)}")

    def _monitor_performance(self):
        """Monitor pool performance and auto-scale"""
        while True:
            try:
                time.sleep(10)  # Monitor every 10 seconds

                with self.pool_lock:
                    queue_size = self.task_queue.qsize()
                    active_workers = len([w for w in self.workers if w.is_alive()])
                    active_tasks_count = len(self.active_tasks)

                # Calculate load metrics
                load_ratio = (active_tasks_count + queue_size) / active_workers if active_workers > 0 else float("inf")

                # Auto-scaling logic
                if load_ratio > self.scale_threshold and active_workers < self.max_workers:
                    # Scale up
                    new_workers = min(2, self.max_workers - active_workers)
                    self._scale_up(new_workers)
                    logger.info(
                        f"📈 Scaled up process pool: +{new_workers} workers (total: {active_workers + new_workers})"
                    )

                elif load_ratio < 0.3 and active_workers > self.min_workers:
                    # Scale down
                    workers_to_remove = min(1, active_workers - self.min_workers)
                    self._scale_down(workers_to_remove)
                    logger.info(
                        f"📉 Scaled down process pool: -{workers_to_remove} workers (total: {active_workers - workers_to_remove})"
                    )

                # Update performance metrics
                try:
                    cpu_percent = psutil.cpu_percent()
                    memory_info = psutil.virtual_memory()

                    with self.pool_lock:
                        self.performance_metrics["cpu_usage"] = cpu_percent
                        self.performance_metrics["memory_usage"] = memory_info.percent

                except Exception:
                    pass  # Ignore psutil errors

            except Exception as e:
                logger.error(f"💥 Pool monitor error: {str(e)}")

    def _scale_up(self, count: int):
        """Add workers to the pool"""
        with self.pool_lock:
            for i in range(count):
                worker_id = len(self.workers)
                worker = threading.Thread(target=self._worker_thread, args=(worker_id,), daemon=True)
                worker.start()
                self.workers.append(worker)

    def _scale_down(self, count: int):
        """Remove workers from the pool"""
        with self.pool_lock:
            for _ in range(count):
                if len(self.workers) > self.min_workers:
                    # Signal worker to shutdown by putting None in queue
                    self.task_queue.put(None)
                    # Remove from workers list (worker will exit naturally)
                    if self.workers:
                        self.workers.pop()

    def get_pool_stats(self) -> Dict[str, Any]:
        """Get current pool statistics"""
        with self.pool_lock:
            active_workers = len([w for w in self.workers if w.is_alive()])
            return {
                "active_workers": active_workers,
                "queue_size": self.task_queue.qsize(),
                "active_tasks": len(self.active_tasks),
                "performance_metrics": self.performance_metrics.copy(),
                "min_workers": self.min_workers,
                "max_workers": self.max_workers,
            }


class AdvancedCache:
    """Advanced caching system with intelligent TTL and LRU eviction"""

    def __init__(self, max_size=1000, default_ttl=3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache = {}
        self.access_times = {}
        self.ttl_times = {}
        self.cache_lock = threading.RLock()
        self.hit_count = 0
        self.miss_count = 0

        # Start cleanup thread
        self.cleanup_thread = threading.Thread(target=self._cleanup_expired, daemon=True)
        self.cleanup_thread.start()

    def get(self, key: str) -> Any:
        """Get value from cache"""
        with self.cache_lock:
            current_time = time.time()

            # Check if key exists and is not expired
            if key in self.cache and (key not in self.ttl_times or self.ttl_times[key] > current_time):
                # Update access time for LRU
                self.access_times[key] = current_time
                self.hit_count += 1
                return self.cache[key]

            # Cache miss or expired
            if key in self.cache:
                # Remove expired entry
                self._remove_key(key)

            self.miss_count += 1
            return None

    def set(self, key: str, value: Any, ttl: int = None) -> None:
        """Set value in cache with optional TTL"""
        with self.cache_lock:
            current_time = time.time()

            # Use default TTL if not specified
            if ttl is None:
                ttl = self.default_ttl

            # Check if we need to evict entries
            if len(self.cache) >= self.max_size and key not in self.cache:
                self._evict_lru()

            # Set the value
            self.cache[key] = value
            self.access_times[key] = current_time
            self.ttl_times[key] = current_time + ttl

    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        with self.cache_lock:
            if key in self.cache:
                self._remove_key(key)
                return True
            return False

    def clear(self) -> None:
        """Clear all cache entries"""
        with self.cache_lock:
            self.cache.clear()
            self.access_times.clear()
            self.ttl_times.clear()

    def _remove_key(self, key: str) -> None:
        """Remove key and associated metadata"""
        self.cache.pop(key, None)
        self.access_times.pop(key, None)
        self.ttl_times.pop(key, None)

    def _evict_lru(self) -> None:
        """Evict least recently used entry"""
        if not self.access_times:
            return

        # Find least recently used key
        lru_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        self._remove_key(lru_key)
        logger.debug(f"🗑️ Evicted LRU cache entry: {lru_key}")

    def _cleanup_expired(self) -> None:
        """Cleanup expired entries periodically"""
        while True:
            try:
                time.sleep(60)  # Cleanup every minute
                current_time = time.time()
                expired_keys = []

                with self.cache_lock:
                    for key, expiry_time in self.ttl_times.items():
                        if expiry_time <= current_time:
                            expired_keys.append(key)

                    for key in expired_keys:
                        self._remove_key(key)

                if expired_keys:
                    logger.debug(f"🧹 Cleaned up {len(expired_keys)} expired cache entries")

            except Exception as e:
                logger.error(f"💥 Cache cleanup error: {str(e)}")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.cache_lock:
            total_requests = self.hit_count + self.miss_count
            hit_rate = (self.hit_count / total_requests * 100) if total_requests > 0 else 0

            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "hit_count": self.hit_count,
                "miss_count": self.miss_count,
                "hit_rate": hit_rate,
                "utilization": (len(self.cache) / self.max_size * 100),
            }


class EnhancedProcessManager:
    """Advanced process management with intelligent resource allocation"""

    def __init__(self):
        self.process_pool = ProcessPool(min_workers=4, max_workers=32)
        self.cache = AdvancedCache(max_size=2000, default_ttl=1800)  # 30 minutes default TTL
        self.resource_monitor = ResourceMonitor()
        self.process_registry = {}
        self.registry_lock = threading.RLock()
        self.performance_dashboard = PerformanceDashboard()

        # Process termination and recovery
        self.termination_handlers = {}
        self.recovery_strategies = {}

        # Auto-scaling configuration
        self.auto_scaling_enabled = True
        self.resource_thresholds = {"cpu_high": 85.0, "memory_high": 90.0, "disk_high": 95.0, "load_high": 0.8}

        # Start background monitoring
        self.monitor_thread = threading.Thread(target=self._monitor_system, daemon=True)
        self.monitor_thread.start()

    def execute_command_async(self, command: str, context: Dict[str, Any] = None) -> str:
        """Execute command asynchronously using process pool"""
        task_id = f"cmd_{int(time.time() * 1000)}_{hash(command) % 10000}"

        # Check cache first
        cache_key = f"cmd_result_{hash(command)}"
        cached_result = self.cache.get(cache_key)
        if cached_result and context and context.get("use_cache", True):
            logger.info(f"📋 Using cached result for command: {command[:50]}...")
            return cached_result

        # Submit to process pool
        self.process_pool.submit_task(task_id, self._execute_command_internal, command, context or {})

        return task_id

    def _execute_command_internal(self, command: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Internal command execution with enhanced monitoring"""
        start_time = time.time()

        try:
            # Resource-aware execution
            resource_usage = self.resource_monitor.get_current_usage()

            # Adjust command based on resource availability
            if resource_usage["cpu_percent"] > self.resource_thresholds["cpu_high"]:
                # Add nice priority for CPU-intensive commands
                if not command.startswith("nice"):
                    command = f"nice -n 10 {command}"

            # Execute command
            if os.name == "nt":
                # Windows specific command handling
                cmd_strip = command.strip()

                # Handle 'file' command replacement
                if cmd_strip.startswith("file "):
                    file_to_check = cmd_strip[5:].strip()
                    # Use python's mimetypes as a simple fallback for 'file' command
                    import mimetypes

                    mtype, _ = mimetypes.guess_type(file_to_check)
                    if mtype:
                        return {
                            "success": True,
                            "stdout": f"{file_to_check}: {mtype}",
                            "stderr": "",
                            "return_code": 0,
                            "execution_time": 0.1,
                            "pid": os.getpid(),
                            "resource_usage": {},
                        }

                # Handle 'strings' command replacement
                if cmd_strip.startswith("strings "):
                    file_to_check = cmd_strip[8:].strip()
                    if os.path.exists(file_to_check):
                        try:
                            with open(file_to_check, "rb") as f:
                                data = f.read()
                                # Simple strings implementation: find sequences of printable chars
                                import re

                                strings = re.findall(b"[ -~]{4,}", data)
                                stdout = "\n".join(s.decode("ascii", errors="ignore") for s in strings)
                                return {
                                    "success": True,
                                    "stdout": stdout,
                                    "stderr": "",
                                    "return_code": 0,
                                    "execution_time": 0.5,
                                    "pid": os.getpid(),
                                    "resource_usage": {},
                                }
                        except Exception as e:
                            logger.error(f"Error in Windows strings fallback: {e}")

            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                preexec_fn=os.setsid if os.name != "nt" else None,
            )

            # Register process
            with self.registry_lock:
                self.process_registry[process.pid] = {
                    "command": command,
                    "process": process,
                    "start_time": start_time,
                    "context": context,
                    "status": "running",
                }

            # Monitor process execution
            stdout, stderr = process.communicate()
            execution_time = time.time() - start_time

            result = {
                "success": process.returncode == 0,
                "stdout": stdout,
                "stderr": stderr,
                "return_code": process.returncode,
                "execution_time": execution_time,
                "pid": process.pid,
                "resource_usage": self.resource_monitor.get_process_usage(process.pid),
            }

            # Cache successful results
            if result["success"] and context.get("cache_result", True):
                cache_key = f"cmd_result_{hash(command)}"
                cache_ttl = context.get("cache_ttl", 1800)  # 30 minutes default
                self.cache.set(cache_key, result, cache_ttl)

            # Update performance metrics
            self.performance_dashboard.record_execution(command, result)

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            error_result = {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "return_code": -1,
                "execution_time": execution_time,
                "error": str(e),
            }

            self.performance_dashboard.record_execution(command, error_result)
            return error_result

        finally:
            # Cleanup process registry
            with self.registry_lock:
                if hasattr(process, "pid") and process.pid in self.process_registry:
                    del self.process_registry[process.pid]

    def get_task_result(self, task_id: str) -> Dict[str, Any]:
        """Get result of async task"""
        return self.process_pool.get_task_result(task_id)

    def terminate_process_gracefully(self, pid: int, timeout: int = 30) -> bool:
        """Terminate process with graceful degradation"""
        try:
            with self.registry_lock:
                if pid not in self.process_registry:
                    return False

                process_info = self.process_registry[pid]
                process = process_info["process"]

                # Try graceful termination first
                process.terminate()

                # Wait for graceful termination
                try:
                    process.wait(timeout=timeout)
                    process_info["status"] = "terminated_gracefully"
                    logger.info(f"✅ Process {pid} terminated gracefully")
                    return True
                except subprocess.TimeoutExpired:
                    # Force kill if graceful termination fails
                    process.kill()
                    process_info["status"] = "force_killed"
                    logger.warning(f"⚠️ Process {pid} force killed after timeout")
                    return True

        except Exception as e:
            logger.error(f"💥 Error terminating process {pid}: {str(e)}")
            return False

    def _monitor_system(self):
        """Monitor system resources and auto-scale"""
        while True:
            try:
                time.sleep(15)  # Monitor every 15 seconds

                # Get current resource usage
                resource_usage = self.resource_monitor.get_current_usage()

                # Auto-scaling based on resource usage
                if self.auto_scaling_enabled:
                    self._auto_scale_based_on_resources(resource_usage)

                # Update performance dashboard
                self.performance_dashboard.update_system_metrics(resource_usage)

            except Exception as e:
                logger.error(f"💥 System monitoring error: {str(e)}")

    def _auto_scale_based_on_resources(self, resource_usage: Dict[str, float]):
        """Auto-scale process pool based on resource usage"""
        pool_stats = self.process_pool.get_pool_stats()
        current_workers = pool_stats["active_workers"]

        # Scale down if resources are constrained
        if (
            resource_usage["cpu_percent"] > self.resource_thresholds["cpu_high"]
            or resource_usage["memory_percent"] > self.resource_thresholds["memory_high"]
        ):
            if current_workers > self.process_pool.min_workers:
                self.process_pool._scale_down(1)
                logger.info(
                    f"📉 Auto-scaled down due to high resource usage: CPU {resource_usage['cpu_percent']:.1f}%, Memory {resource_usage['memory_percent']:.1f}%"
                )

        # Scale up if resources are available and there's demand
        elif (
            resource_usage["cpu_percent"] < 60
            and resource_usage["memory_percent"] < 70
            and pool_stats["queue_size"] > 2
        ):
            if current_workers < self.process_pool.max_workers:
                self.process_pool._scale_up(1)
                logger.info(f"📈 Auto-scaled up due to available resources and demand")

    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive system and process statistics"""
        return {
            "process_pool": self.process_pool.get_pool_stats(),
            "cache": self.cache.get_stats(),
            "resource_usage": self.resource_monitor.get_current_usage(),
            "active_processes": len(self.process_registry),
            "performance_dashboard": self.performance_dashboard.get_summary(),
            "auto_scaling_enabled": self.auto_scaling_enabled,
            "resource_thresholds": self.resource_thresholds,
        }


class ResourceMonitor:
    """Advanced resource monitoring with historical tracking"""

    def __init__(self, history_size=100):
        self.history_size = history_size
        self.usage_history = []
        self.history_lock = threading.Lock()

    def get_current_usage(self) -> Dict[str, float]:
        """Get current system resource usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            network = psutil.net_io_counters()

            usage = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "disk_percent": disk.percent,
                "disk_free_gb": disk.free / (1024**3),
                "network_bytes_sent": network.bytes_sent,
                "network_bytes_recv": network.bytes_recv,
                "timestamp": time.time(),
            }

            # Add to history
            with self.history_lock:
                self.usage_history.append(usage)
                if len(self.usage_history) > self.history_size:
                    self.usage_history.pop(0)

            return usage

        except Exception as e:
            logger.error(f"💥 Error getting resource usage: {str(e)}")
            return {
                "cpu_percent": 0,
                "memory_percent": 0,
                "memory_available_gb": 0,
                "disk_percent": 0,
                "disk_free_gb": 0,
                "network_bytes_sent": 0,
                "network_bytes_recv": 0,
                "timestamp": time.time(),
            }

    def get_process_usage(self, pid: int) -> Dict[str, Any]:
        """Get resource usage for specific process"""
        try:
            process = psutil.Process(pid)
            return {
                "cpu_percent": process.cpu_percent(),
                "memory_percent": process.memory_percent(),
                "memory_rss_mb": process.memory_info().rss / (1024**2),
                "num_threads": process.num_threads(),
                "status": process.status(),
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return {}

    def get_usage_trends(self) -> Dict[str, Any]:
        """Get resource usage trends"""
        with self.history_lock:
            if len(self.usage_history) < 2:
                return {}

            recent = self.usage_history[-10:]  # Last 10 measurements

            cpu_trend = sum(u["cpu_percent"] for u in recent) / len(recent)
            memory_trend = sum(u["memory_percent"] for u in recent) / len(recent)

            return {
                "cpu_avg_10": cpu_trend,
                "memory_avg_10": memory_trend,
                "measurements": len(self.usage_history),
                "trend_period_minutes": len(recent) * 15 / 60,  # 15 second intervals
            }


class PerformanceDashboard:
    """Real-time performance monitoring dashboard"""

    def __init__(self):
        self.execution_history = []
        self.system_metrics = []
        self.dashboard_lock = threading.Lock()
        self.max_history = 1000

    def record_execution(self, command: str, result: Dict[str, Any]):
        """Record command execution for performance tracking"""
        with self.dashboard_lock:
            execution_record = {
                "command": command[:100],  # Truncate long commands
                "success": result.get("success", False),
                "execution_time": result.get("execution_time", 0),
                "return_code": result.get("return_code", -1),
                "timestamp": time.time(),
            }

            self.execution_history.append(execution_record)
            if len(self.execution_history) > self.max_history:
                self.execution_history.pop(0)

    def update_system_metrics(self, metrics: Dict[str, Any]):
        """Update system metrics for dashboard"""
        with self.dashboard_lock:
            self.system_metrics.append(metrics)
            if len(self.system_metrics) > self.max_history:
                self.system_metrics.pop(0)

    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        with self.dashboard_lock:
            if not self.execution_history:
                return {"executions": 0}

            recent_executions = self.execution_history[-100:]  # Last 100 executions

            total_executions = len(recent_executions)
            successful_executions = sum(1 for e in recent_executions if e["success"])
            avg_execution_time = sum(e["execution_time"] for e in recent_executions) / total_executions

            return {
                "total_executions": len(self.execution_history),
                "recent_executions": total_executions,
                "success_rate": (successful_executions / total_executions * 100) if total_executions > 0 else 0,
                "avg_execution_time": avg_execution_time,
                "system_metrics_count": len(self.system_metrics),
            }


# Global instances (lazy-init for faster module load — uses module-level __getattr__)
_tech_detector = None
_rate_limiter = None
_failure_recovery = None
_performance_monitor = None
_parameter_optimizer = None
_enhanced_process_manager = None


def get_enhanced_process_manager():
    global _enhanced_process_manager
    if _enhanced_process_manager is None:
        _enhanced_process_manager = EnhancedProcessManager()
    return _enhanced_process_manager


def __getattr__(name):
    _globals = {
        "tech_detector": lambda: (
            _globals["_tech_detector"]
            if _globals["_tech_detector"]
            else globals().__setitem__("_tech_detector", TechnologyDetector()) or globals()["_tech_detector"]
        ),
    }
    if name == "tech_detector":
        global _tech_detector
        if _tech_detector is None:
            _tech_detector = TechnologyDetector()
        return _tech_detector
    if name == "rate_limiter":
        global _rate_limiter
        if _rate_limiter is None:
            _rate_limiter = RateLimitDetector()
        return _rate_limiter
    if name == "failure_recovery":
        global _failure_recovery
        if _failure_recovery is None:
            _failure_recovery = FailureRecoverySystem()
        return _failure_recovery
    if name == "performance_monitor":
        global _performance_monitor
        if _performance_monitor is None:
            _performance_monitor = PerformanceMonitor()
        return _performance_monitor
    if name == "parameter_optimizer":
        global _parameter_optimizer
        if _parameter_optimizer is None:
            _parameter_optimizer = ParameterOptimizer()
        return _parameter_optimizer
    if name == "enhanced_process_manager":
        return get_enhanced_process_manager()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
