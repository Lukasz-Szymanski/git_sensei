"""Pre-commit AI Code Reviewer module for Git-Sensei."""
from typing import Optional, Dict, Any
import re
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

REVIEW_SYSTEM_PROMPT = """You are a senior code reviewer and security auditor.
Analyze the provided git diff and provide an objective, actionable, and concise review.

Focus specifically on:
1. Critical bugs, logic errors, unhandled edge cases
2. Security vulnerabilities (injection, hardcoded secrets, insecure deserialization, unsafe subprocess)
3. Performance anti-patterns and memory leaks
4. Code clarity and maintainability
5. Missing or skipped tests for the changed code

Output format guidelines:
- If the changes are completely clean and good, state that clearly.
- Otherwise, list issues in this exact structured format:
[LEVEL] (filename:line or general): Issue description -> Recommended fix

Allowed LEVEL values:
- CRITICAL: Blocking bugs, security flaws, data loss risks
- WARNING: Edge cases, performance bottlenecks, unhandled errors
- SUGGESTION: Style, readability, minor cleanups

Finally, end with:
SUMMARY: A 1-2 sentence overall verdict.
"""

def parse_review_findings(raw_output: str) -> Dict[str, Any]:
    """Parse raw AI output into structured findings."""
    findings = []
    summary = ""
    lines = raw_output.strip().splitlines()

    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue
        if line_clean.startswith("SUMMARY:"):
            summary = line_clean.replace("SUMMARY:", "").strip()
            continue

        match = re.match(r"^\[?(CRITICAL|WARNING|SUGGESTION)\]?:?\s*(?:\(([^)]+)\))?:?\s*(.*)$", line_clean, re.IGNORECASE)
        if match:
            level = match.group(1).upper()
            location = match.group(2) or "General"
            details = match.group(3).strip()
            findings.append({
                "level": level,
                "location": location,
                "details": details
            })

    if not summary and lines:
        summary = lines[-1]

    return {
        "raw": raw_output,
        "findings": findings,
        "summary": summary,
        "has_critical": any(f["level"] == "CRITICAL" for f in findings),
        "has_warning": any(f["level"] == "WARNING" for f in findings),
    }

def display_review_report(parsed_review: Dict[str, Any], console: Optional[Console] = None) -> None:
    """Render a beautiful terminal report of the code review using Rich."""
    if console is None:
        console = Console()

    findings = parsed_review.get("findings", [])
    summary = parsed_review.get("summary", "Review complete.")
    has_critical = parsed_review.get("has_critical", False)
    has_warning = parsed_review.get("has_warning", False)

    if not findings:
        console.print(Panel(
            Text(f"✅ LGTM! {summary}\nNo major issues found in staged changes.", style="bold green"),
            title="🥋 [bold cyan]Git-Sensei Code Review[/bold cyan]",
            border_style="green"
        ))
        return

    table = Table(title="🔍 Review Findings", show_header=True, header_style="bold magenta")
    table.add_column("Level", style="bold", width=12)
    table.add_column("Target / Location", style="cyan", width=24)
    table.add_column("Finding & Suggestion", style="white")

    for f in findings:
        lvl = f["level"]
        if lvl == "CRITICAL":
            lvl_text = Text("🚨 CRITICAL", style="bold red")
        elif lvl == "WARNING":
            lvl_text = Text("⚠️  WARNING", style="bold yellow")
        else:
            lvl_text = Text("💡 SUGGESTION", style="bold blue")

        table.add_row(lvl_text, f["location"], f["details"])

    console.print()
    console.print(table)
    console.print()

    verdict_style = "bold red" if has_critical else ("bold yellow" if has_warning else "bold green")
    verdict_border = "red" if has_critical else ("yellow" if has_warning else "green")

    console.print(Panel(
        Text(f"Verdict: {summary}", style=verdict_style),
        title="🥋 [bold cyan]Summary[/bold cyan]",
        border_style=verdict_border
    ))
