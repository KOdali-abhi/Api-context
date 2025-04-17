"""
setup.py for API Context Memory System
"""

from setuptools import setup, find_packages

setup(
    name="api-context-memory",
    version="0.2.0",
    description="A streamlined library for recording, analyzing, and maintaining context across API interactions",
    author="API Context Memory Team",
    author_email="info@apicontextmemory.com",
    url="https://github.com/apicontextmemory/api-context-memory",
    packages=find_packages(),
    install_requires=[
        "requests>=2.25.0",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.7",
)
