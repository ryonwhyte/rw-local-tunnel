#!/usr/bin/env python3
"""Setup script for rw-local-tunnel."""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="rw-local-tunnel",
    version="1.0.0",
    author="Ryon Whyte",
    description="Specialized Tailscale tunnel manager for servers running NPM (Nginx Proxy Manager) alongside Headscale/Tailscale",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/rw-local-tunnel",
    packages=find_packages(),
    py_modules=["rw_local_tunnel"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Topic :: System :: Networking",
        "Topic :: Security",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: POSIX :: Linux",
        "Environment :: Console",
    ],
    python_requires=">=3.8",
    install_requires=[
        "rich>=13.0.0",
        "psutil>=5.9.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "black>=22.0.0",
            "pyinstaller>=5.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "rw-local-tunnel=rw_local_tunnel:main",
            "rwlt=rw_local_tunnel:main",  # Short alias
        ],
    },
    keywords="tailscale headscale tunnel vpn networking firewall monitoring npm nginx-proxy-manager",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/rw-local-tunnel/issues",
        "Source": "https://github.com/yourusername/rw-local-tunnel",
    },
)