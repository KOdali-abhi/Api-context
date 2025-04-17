# API Context Memory System - Installation Guide

This guide will help you install and get started with the API Context Memory System.

## Installation

### Option 1: Install from the package

1. Extract the zip file to a location of your choice
2. Navigate to the extracted directory
3. Install the package:

```bash
pip install -e .
```

### Option 2: Install dependencies manually

If you prefer not to install the package, you can simply use the files directly:

1. Extract the zip file to a location of your choice
2. Install the required dependency:

```bash
pip install requests
```

3. Make sure the `api_context_memory` directory is in your Python path

## Quick Verification

To verify that the installation was successful, run the included test script:

```bash
python test_api_memory.py
```

You should see all tests pass successfully.

## Running the Example

To see the API Context Memory System in action, run the example script:

```bash
python example.py
```

This will demonstrate all the key features of the system with real API calls.

## Next Steps

1. Read the README.md file for comprehensive documentation
2. Explore the example.py file to understand how to use the system
3. Integrate the API Context Memory System into your own projects

## Troubleshooting

If you encounter any issues during installation:

1. Make sure you have Python 3.7 or higher installed
2. Verify that pip is up to date: `pip install --upgrade pip`
3. Check that you have the required permissions to install packages
4. If using a virtual environment, ensure it's activated

For any other issues, refer to the troubleshooting section in the README.md file.
