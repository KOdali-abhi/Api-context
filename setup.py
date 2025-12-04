"""
setup.py for API Context Memory System
"""

from setuptools import setup, find_packages

setup(
    name="api-context-memory",
    version="0.3.0",
    description="A streamlined library for recording, analyzing, and maintaining context across API interactions",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="API Context Memory Team",
    author_email="info@apicontextmemory.com",
    url="https://github.com/apicontextmemory/api-context-memory",
    packages=find_packages(),
    install_requires=[
        "requests>=2.25.0",
    ],
    extras_require={
        "redis": ["redis>=4.0.0"],
        "async": ["aiohttp>=3.8.0"],
        "all": [
            "redis>=4.0.0",
            "aiohttp>=3.8.0",
        ],
    },
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
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP",
    ],
    python_requires=">=3.7",
    keywords="api, context, memory, http, requests, middleware, authentication, rate-limiting",
)
