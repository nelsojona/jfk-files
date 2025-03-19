#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
import os

# Read the long description from README.md
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read requirements from requirements.txt
with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = f.read().splitlines()

setup(
    name="jfk-files-scraper",
    version="1.0.0",
    author="JFK Files Scraper Project Contributors",
    author_email="example@example.com",  # Replace with a real maintainer email
    description="A tool for scraping JFK files from the National Archives website",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/jfk-files-scraper",  # Replace with actual repo URL
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Internet :: WWW/HTTP :: Indexing/Search",
        "Topic :: Text Processing :: Markup :: Markdown",
        "Topic :: Utilities",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "jfk-scraper=jfk_scraper:main",
        ],
    },
    include_package_data=True,
)
