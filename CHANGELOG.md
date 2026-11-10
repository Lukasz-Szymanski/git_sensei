# Changelog

All notable changes to this project will be documented in this file.

# [v0.16.0] - 2026-11-10

## 🚀 Features

- **AI-Powered Merge Conflict Resolution**: Added dedicated AI command to automatically analyze and resolve git merge conflicts intelligently (`6e0e8df`).
- **Pre-commit Code Review**: Introduced an AI-assisted pre-commit code review command alongside a new `--review` flag to inspect staged changes before committing (`c3cab9f`).
- **Changelog Generator & Lazygit Integration**: Added an automated changelog generator and comprehensive integration instructions for Lazygit users (`712ca9d`).

## 🛠️ Maintenance & Refactoring

- **Code Quality & Deduplication**: Deduplicated default prompt templates and fixed outstanding Ruff linting issues (`752a6d8`).
- **CI & Runtime Environment**: Bumped the minimum supported Python version to 3.10 and updated the CI test matrix accordingly (`5d3e14d`).
- **Documentation Updates**: Streamlined `README.md`, untracked internal notes (`89c0a22`), and corrected previous changelog entries for v0.15.1 (`5da8b56`).
