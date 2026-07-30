"""
Secrets Shield - detects potential secrets in git diffs before sending to AI.
"""
import re
import math
from typing import List, Tuple
from dataclasses import dataclass


@dataclass
class SecretMatch:
    """Represents a detected secret."""
    line_num: int
    line: str
    pattern_name: str
    match: str


# Known secret patterns (regex)
SECRET_PATTERNS = {
    "AWS Access Key": r"AKIA[0-9A-Z]{16}",
    "AWS Secret Key": r"(?i)aws_secret_access_key\s*[=:]\s*['\"]?([A-Za-z0-9/+=]{40})['\"]?",
    "GitHub Token": r"ghp_[A-Za-z0-9]{36}",
    "GitHub OAuth": r"gho_[A-Za-z0-9]{36}",
    "GitHub PAT": r"github_pat_[A-Za-z0-9]{22}_[A-Za-z0-9]{59}",
    "GitLab Token": r"glpat-[A-Za-z0-9\-]{20}",
    "Slack Token": r"xox[baprs]-[0-9A-Za-z\-]{10,250}",
    "Slack Webhook": r"https://hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[A-Za-z0-9]+",
    "Discord Webhook": r"https://discord(?:app)?\.com/api/webhooks/[0-9]+/[A-Za-z0-9_-]+",
    "Google API Key": r"AIza[0-9A-Za-z\-_]{35}",
    "Heroku API Key": r"(?i)heroku[_-]?api[_-]?key\s*[=:]\s*['\"]?([A-Fa-f0-9-]{36})['\"]?",
    "JWT Token": r"eyJ[A-Za-z0-9-_]+\.eyJ[A-Za-z0-9-_]+\.[A-Za-z0-9-_.+/]*",
    "Private Key": r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",
    "Generic API Key": r"(?i)(?:api[_-]?key|apikey|secret[_-]?key|access[_-]?token)\s*[=:]\s*['\"]?([A-Za-z0-9_\-]{20,})['\"]?",
    "Generic Password": r"(?i)(?:password|passwd|pwd)\s*[=:]\s*['\"]([^'\"]{8,})['\"]",
    "Bearer Token": r"(?i)bearer\s+[A-Za-z0-9_\-\.]+",
    "Basic Auth": r"(?i)basic\s+[A-Za-z0-9+/=]{20,}",
    "NPM Token": r"npm_[A-Za-z0-9]{36}",
    "PyPI Token": r"pypi-[A-Za-z0-9]{60,}",
    "Anthropic API Key": r"sk-ant-[A-Za-z0-9\-_]{90,}",
    "OpenAI API Key": r"sk-[A-Za-z0-9]{48}",
}


def calculate_entropy(s: str) -> float:
    """Calculate Shannon entropy of a string."""
    if not s:
        return 0.0

    prob = [float(s.count(c)) / len(s) for c in set(s)]
    return -sum(p * math.log2(p) for p in prob if p > 0)


def check_high_entropy(line: str, threshold: float = 4.5) -> List[Tuple[str, float]]:
    """
    Find high-entropy strings that might be secrets.
    Returns list of (suspicious_string, entropy) tuples.
    """
    suspicious = []

    # Look for quoted strings or assignment values
    patterns = [
        r'["\']([A-Za-z0-9+/=_\-]{20,})["\']',  # Quoted strings
        r'=\s*([A-Za-z0-9+/=_\-]{20,})\s*$',     # Assignment values
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, line):
            value = match.group(1)
            entropy = calculate_entropy(value)
            if entropy >= threshold:
                suspicious.append((value, entropy))

    return suspicious


def scan_diff(diff: str, custom_patterns: dict = None) -> List[SecretMatch]:
    """
    Scan a git diff for potential secrets.
    Only scans added lines (starting with +).
    Returns list of SecretMatch objects.
    """
    matches = []
    current_file = ""

    patterns_to_check = SECRET_PATTERNS.copy()
    if custom_patterns:
        patterns_to_check.update(custom_patterns)

    # Files to skip (contain regex patterns that look like secrets)
    skip_files = {"secrets_shield.py", "test_secrets.py"}

    lines = diff.split('\n')
    line_num = 0

    for line in lines:
        # Track current file
        if line.startswith('+++ b/'):
            current_file = line[6:].split('/')[-1]
            continue

        # Skip files that contain detection patterns
        if current_file in skip_files:
            continue
        # Track line numbers from diff headers
        if line.startswith('@@'):
            # Parse @@ -x,y +a,b @@ format
            m = re.search(r'\+(\d+)', line)
            if m:
                line_num = int(m.group(1)) - 1
            continue

        # Only check added lines
        if not line.startswith('+'):
            if not line.startswith('-'):
                line_num += 1
            continue

        line_num += 1
        content = line[1:]  # Remove + prefix

        # Skip diff metadata
        if line.startswith('+++'):
            continue

        # Check known patterns
        for pattern_name, pattern in patterns_to_check.items():
            if re.search(pattern, content):
                match_obj = re.search(pattern, content)
                matches.append(SecretMatch(
                    line_num=line_num,
                    line=content.strip(),
                    pattern_name=pattern_name,
                    match=match_obj.group(0)[:50] + "..." if len(match_obj.group(0)) > 50 else match_obj.group(0)
                ))

        # Check entropy (only if no pattern match found for this line)
        if not any(m.line_num == line_num for m in matches):
            high_entropy = check_high_entropy(content)
            for value, entropy in high_entropy:
                matches.append(SecretMatch(
                    line_num=line_num,
                    line=content.strip(),
                    pattern_name=f"High entropy ({entropy:.1f})",
                    match=value[:50] + "..." if len(value) > 50 else value
                ))

    return matches


def format_warning(matches: List[SecretMatch]) -> str:
    """Format secret matches as a warning message."""
    if not matches:
        return ""

    lines = ["", "WARNING: Potential secrets detected!", "-" * 40]

    for m in matches:
        lines.append(f"  Line {m.line_num}: {m.pattern_name}")
        lines.append(f"    {m.line[:60]}{'...' if len(m.line) > 60 else ''}")

    lines.append("-" * 40)
    lines.append("")

    return "\n".join(lines)


def redact_secrets(diff: str, custom_patterns: dict = None) -> str:
    """
    Scan a git diff and replace all detected secrets/credentials with [REDACTED].
    """
    patterns_to_check = SECRET_PATTERNS.copy()
    if custom_patterns:
        patterns_to_check.update(custom_patterns)

    redacted_lines = []
    current_file = ""
    skip_files = {"secrets_shield.py", "test_secrets.py"}

    for line in diff.split('\n'):
        # Track current file
        if line.startswith('+++ b/'):
            current_file = line[6:].split('/')[-1]
            redacted_lines.append(line)
            continue

        # Skip files that contain detection patterns
        if current_file in skip_files:
            redacted_lines.append(line)
            continue

        # Only redact added lines
        if not line.startswith('+') or line.startswith('+++'):
            redacted_lines.append(line)
            continue

        content = line[1:]  # Remove + prefix
        redacted_content = content

        # 1. Redact known patterns
        for pattern_name, pattern in patterns_to_check.items():
            try:
                # Find match in content
                match_obj = re.search(pattern, redacted_content)
                if match_obj:
                    # If pattern has a capture group, redact only the first group
                    if match_obj.groups():
                        secret_val = match_obj.group(1)
                        if secret_val and secret_val != "[REDACTED]":
                            redacted_content = redacted_content.replace(secret_val, "[REDACTED]")
                    else:
                        whole_match = match_obj.group(0)
                        if whole_match and whole_match != "[REDACTED]":
                            redacted_content = redacted_content.replace(whole_match, "[REDACTED]")
            except Exception as e:
                print(f"Warning: Failed to process secret regex pattern '{pattern_name}': {e}")

        # 2. Redact high-entropy values
        high_entropy = check_high_entropy(redacted_content)
        for value, entropy in high_entropy:
            if value != "[REDACTED]":
                redacted_content = redacted_content.replace(value, "[REDACTED]")

        redacted_lines.append("+" + redacted_content)

    return '\n'.join(redacted_lines)

