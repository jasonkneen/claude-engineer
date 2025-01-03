from setuptools import setup, find_packages

setup(
    name="mcp-memory",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        line.strip()
        for line in open("requirements.txt").readlines()
    ],
    entry_points={
        "console_scripts": [
            "mcp-memory=mcp_memory.tool:main",
        ],
    },
)
