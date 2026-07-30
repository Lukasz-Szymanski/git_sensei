from setuptools import setup, find_packages

setup(
    name="git-sensei-ai",
    version="0.15.0",
    description="AI-powered git commit helper with smart truncation, monorepo detection, and secret redaction.",
    long_description=open("README.md", "r", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="Lukasz Szymanski",
    url="https://github.com/Lukasz-Szymanski/git_sensei",
    license="MIT",
    packages=find_packages(),
    py_modules=["main", "config", "providers", "git_utils", "secrets_shield", "local_bridge"],
    install_requires=[
        "typer>=0.9.0",
        "tomli>=2.0.1; python_version < '3.11'",
        "rich>=13.0.0",
    ],
    entry_points={
        "console_scripts": [
            "sensei=main:app",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
)
