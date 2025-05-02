# Installation Guide

This guide explains how to install Photoshop MCP Server.

## Common Steps

### 1. Installing Python

Python 3.11 or higher is required.

- Download and install from the [Python official website](https://www.python.org/downloads/)
- Make sure to enable the "Add Python to PATH" option during installation

### 2. Installing Photoshop MCP Server

```bash
pip install photoshop-mcp-server
```

Or, install from source:

```bash
git clone https://github.com/StarBoze/photoshop-mcp-server.git
cd photoshop-mcp-server
pip install -e .
```

## macOS Specific Setup

### 1. AppleScript Permissions

1. System Preferences > Security & Privacy > Privacy > Automation
2. Allow Terminal or VS Code to access "Photoshop"

### 2. Installing py-applescript

```bash
pip install py-applescript
```

## Windows Specific Setup

### 1. PowerShell Execution Policy

Open PowerShell with administrator privileges and run the following command:

```powershell
Set-ExecutionPolicy RemoteSigned
```

### 2. Installing pywin32

```bash
pip install pywin32
```

For detailed Windows environment setup, please refer to the [Windows Setup Guide](windows_setup.en.md).

## UXP Plugin Installation

If you're using the UXP backend, you need to install the plugin:

1. Package the plugin
```bash
photoshop-mcp-server package_plugin
```

2. Display installation instructions
```bash
photoshop-mcp-server install_plugin
```

3. Follow the displayed instructions to install the plugin

## Verification

After installation is complete, start the server and verify operation with the following commands:

```bash
# For macOS (AppleScript backend)
photoshop-mcp-server start --bridge-mode applescript

# For Windows (PowerShell backend)
photoshop-mcp-server start --bridge-mode powershell

# Using UXP backend (cross-platform)
photoshop-mcp-server start --bridge-mode uxp
```

When the server starts successfully, you'll see a message like this:

```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:5001 (Press CTRL+C to quit)
```

## Troubleshooting

### Common Issues

- **Dependency Errors**: If required packages are not installed, run the following command:
  ```bash
  pip install -r requirements.txt
  ```

- **Port Conflicts**: If the default port (5001) is already in use, specify a different port:
  ```bash
  photoshop-mcp-server start --port 5002
  ```

### macOS Specific Issues

- **AppleScript Permission Errors**: If controlling Photoshop fails, check AppleScript permissions in System Preferences.

- **Photoshop Not Responding**: Restart Photoshop and ensure you're using the latest version.

### Windows Specific Issues

- **PowerShell Execution Policy Errors**: If script execution is not allowed, change the PowerShell execution policy.

- **COM Object Creation Errors**: Make sure Photoshop is running and run PowerShell with administrator privileges.

For detailed troubleshooting, please refer to the [Windows Setup Guide](windows_setup.en.md).

## Next Steps

- Check the [Basic Usage](../README.en.md#usage) guide
- Refer to the [API Reference](api_reference.md) (coming soon)
- Try the [Tutorials](tutorials.md) (coming soon)