"""Unit tests for Git-Sensei Code Reviewer."""
from git_sensei.core.reviewer import parse_review_findings, display_review_report
from rich.console import Console
import io

def test_parse_review_findings_clean():
    sample = "Everything looks good!\nSUMMARY: Code is clean and safe to commit."
    parsed = parse_review_findings(sample)
    assert not parsed["has_critical"]
    assert not parsed["has_warning"]
    assert len(parsed["findings"]) == 0
    assert "clean and safe" in parsed["summary"]

def test_parse_review_findings_structured():
    sample = """
[CRITICAL] (auth.py:45): Potential SQL injection in query building -> Use parameterized queries.
[WARNING] (utils.py:12): Unhandled ValueError on empty input -> Add try-except block.
[SUGGESTION] (main.py): Function name could be more descriptive -> Rename to validate_user_payload.
SUMMARY: Found 1 critical security issue and 1 warning.
"""
    parsed = parse_review_findings(sample)
    assert parsed["has_critical"] is True
    assert parsed["has_warning"] is True
    assert len(parsed["findings"]) == 3

    crit = parsed["findings"][0]
    assert crit["level"] == "CRITICAL"
    assert "auth.py:45" in crit["location"]
    assert "SQL injection" in crit["details"]

    warn = parsed["findings"][1]
    assert warn["level"] == "WARNING"
    assert "utils.py:12" in warn["location"]

    sugg = parsed["findings"][2]
    assert sugg["level"] == "SUGGESTION"

def test_display_review_report_clean():
    parsed = {
        "raw": "",
        "findings": [],
        "summary": "Looks great!",
        "has_critical": False,
        "has_warning": False,
    }
    buf = io.StringIO()
    console = Console(file=buf, force_terminal=True, color_system="truecolor")
    display_review_report(parsed, console=console)
    output = buf.getvalue()
    assert "LGTM" in output

def test_display_review_report_with_findings():
    parsed = {
        "raw": "",
        "findings": [
            {"level": "CRITICAL", "location": "app.py:10", "details": "Hardcoded secret"},
            {"level": "WARNING", "location": "db.py", "details": "Missing index"},
            {"level": "SUGGESTION", "location": "General", "details": "Add docstrings"},
        ],
        "summary": "Please fix critical issues before commit.",
        "has_critical": True,
        "has_warning": True,
    }
    buf = io.StringIO()
    console = Console(file=buf, force_terminal=True, color_system="truecolor")
    display_review_report(parsed, console=console)
    output = buf.getvalue()
    assert "CRITICAL" in output
    assert "Hardcoded secret" in output
    assert "Missing index" in output
