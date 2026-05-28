"""数据脱敏模块 — PentAGI 移植

安全测试中需要存储指南、答案、代码到记忆系统时，
必须对敏感数据进行脱敏处理。
"""

import re

# 脱敏模式（从 PentAGI anonymizer/patterns 移植）
ANONYMIZER_PATTERNS = [
    # IPv4 地址
    (
        re.compile(r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"),
        "{target_ip}",
    ),
    # IPv6
    (re.compile(r"(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}"), "{target_ipv6}"),
    # 域名
    (re.compile(r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b"), "{target_domain}"),
    # URL（包含域名）
    (re.compile(r'https?://[^\s<>"{}|\^`\[\]]+'), "{target_url}"),
    # API Key（通用模式）
    (re.compile(r"\b[A-Za-z0-9+/]{20,}={0,2}\b"), "{api_key_token}"),
    # 用户名:密码
    (re.compile(r"\b[a-zA-Z][a-zA-Z0-9_]{2,20}:[^\s]{3,100}\b"), "{username}:{password}"),
    # Password 看起来像哈希
    (re.compile(r"(?:password|pwd|pass)\s*[:=]\s*[^\s,;]+", re.IGNORECASE), "password: {password}"),
    # Token / JWT
    (re.compile(r"eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}"), "{jwt_token}"),
    # API key 在配置中
    (re.compile(r"(?:api[_-]?key|apikey|secret[_-]?key)\s*[:=]+\s*[^\s,;]+", re.IGNORECASE), "{api_key}=MASKED"),
    # Session token
    (re.compile(r"(?:session|cookie|token)\s*[:=]+\s*[a-zA-Z0-9+/]{16,}", re.IGNORECASE), "{token}=MASKED"),
    # MAC 地址
    (re.compile(r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b"), "{mac_address}"),
    # Email
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "{email}"),
    # 路径中有敏感信息
    (re.compile(r"(?:/home/|/Users/|C:\\Users\\)[^\s]+"), "{user_path}"),
    # SSH 私钥片段
    (
        re.compile(
            r"-----BEGIN\s+(?:RSA|DSA|EC|OPENSSH)\s+PRIVATE\s+KEY-----.*?-----END\s+(?:RSA|DSA|EC|OPENSSH)\s+PRIVATE\s+KEY-----",
            re.DOTALL,
        ),
        "{private_key}",
    ),
    # 标准端口保留不变 (80, 443, 22, 8080, 8443)，其他替换
    (
        re.compile(r"\bport\s*(?:=|:)?\s*([0-9]+)\b"),
        lambda m: f"port: {m.group(1)}"
        if int(m.group(1)) in {80, 443, 22, 8080, 8443, 21, 25, 53, 3306, 5432, 6379, 27017}
        else "port: {custom_port}",
    ),
    # UUID
    (re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"), "{uuid}"),
    # SSN
    (re.compile(r"\b[0-9]{3}-[0-9]{2}-[0-9]{4}\b"), "{ssn}"),
    # Credit Card
    (re.compile(r"\b[0-9]{4}[\s-]?[0-9]{4}[\s-]?[0-9]{4}[\s-]?[0-9]{4}\b"), "{credit_card}"),
]


def anonymize(text: str, preserve_standard_ports: bool = True) -> str:
    """脱敏文本中的敏感数据

    将所有可识别的敏感信息替换为描述性占位符。

    Args:
        text: 原始文本
        preserve_standard_ports: 是否保留标准端口号 (80,443,22 等)

    Returns:
        脱敏后的文本
    """
    result = text

    for pattern, replacement in ANONYMIZER_PATTERNS:
        if callable(replacement):
            continue  # 跳过 lambda（复杂模式）
        result = pattern.sub(replacement, result)

    return result


def anonymize_for_storage(text: str) -> str:
    """为存储到记忆系统进行脱敏

    确保存储的技术指南在多个目标中可复用。
    示例:
        'nmap -sV 192.168.1.100' → 'nmap -sV {target_ip}'
        'admin:password123 在 example.com' → '{username}:{password} 在 {target_domain}'
    """
    return anonymize(text)
