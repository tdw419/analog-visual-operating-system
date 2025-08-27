"""
Setup script for VisualPython

This makes VisualPython installable via pip:
    pip install visual-python

Or for local development:
    pip install -e .
"""

from setuptools import setup, find_packages
import os

# Read README for long description
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return ""

# Read version from __init__.py
def get_version():
    init_path = os.path.join('visual_python', '__init__.py')
    with open(init_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('__version__'):
                return line.split('=')[1].strip().strip('"\'')
    return "0.1.0"

setup(
    name="visual-python",
    version=get_version(),
    author="AVOS/UVIR Team",
    author_email="contact@visualpython.org",
    description="Revolutionary Python execution without compilation - code becomes visual operations instantly",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/avos-uvir/visual-python",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Education", 
        "Topic :: Software Development :: Interpreters",
        "Topic :: Software Development :: User Interfaces",
        "Topic :: Education",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Environment :: Console",
        "Environment :: Win32 (MS Windows)",
        "Environment :: X11 Applications :: Qt",
        "Environment :: MacOS X",
    ],
    python_requires=">=3.7",
    install_requires=[
        # Core dependencies - minimal for maximum compatibility
    ],
    extras_require={
        # Optional dependencies for enhanced features
        "gui": [
            "tkinter; platform_system != 'Linux'",  # Usually built-in
        ],
        "pygame": [
            "pygame>=2.0.0",
        ],
        "monitoring": [
            "watchdog>=2.1.0",
        ],
        "hardware": [
            "pyserial>=3.4",
        ],
        "all": [
            "pygame>=2.0.0",
            "watchdog>=2.1.0", 
            "pyserial>=3.4",
        ],
        "dev": [
            "pytest>=6.0",
            "pytest-cov",
            "black",
            "flake8",
            "mypy",
        ]
    },
    entry_points={
        "console_scripts": [
            "visual-python=visual_python.monitor:main",
            "vpy=visual_python.monitor:main",
            "visual-python-demo=visual_python:quick_demo",
        ],
    },
    keywords=[
        "python", "visual", "execution", "live", "coding", "no-compilation",
        "immediate", "feedback", "analog", "signals", "hardware", "education",
        "interactive", "programming", "development", "real-time"
    ],
    project_urls={
        "Bug Reports": "https://github.com/avos-uvir/visual-python/issues",
        "Source": "https://github.com/avos-uvir/visual-python",
        "Documentation": "https://visual-python.readthedocs.io/",
        "Funding": "https://github.com/sponsors/avos-uvir",
    },
    include_package_data=True,
    package_data={
        "visual_python": [
            "examples/*.py",
            "templates/*.py",
            "assets/*",
        ],
    },
    zip_safe=False,  # Allow file access for templates and assets
)