from setuptools import setup, find_packages

setup(
    name="git-sensei",
    version="0.10.0",
    packages=find_packages(),
    py_modules=["main", "config", "providers", "git_utils", "secrets", "local_bridge"],
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
)
