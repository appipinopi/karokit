import re

from setuptools import find_namespace_packages, setup

with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

with open("./karokit/__init__.py", encoding="utf-8") as f:
    version = re.findall(r'__version__ = "(.+)"', f.read())[0]

setup(
    name="karokit",
    version=version,
    install_requires=[
        "httpx[socks]",
        "beautifulsoup4",
        "lxml",
        "python-socketio[asyncio_client]",
    ],
    python_requires=">=3.10",
    description="Karotter scraper/API wrapper for python with no official API key required.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="MIT",
    url="https://karotter.com/",
    packages=find_namespace_packages(include=["karokit*"]),
)
