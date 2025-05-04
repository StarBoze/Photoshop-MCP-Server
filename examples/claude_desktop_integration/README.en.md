# Claude Desktop + Photoshop MCP Integration Guide

This guide explains how to operate Photoshop MCP Server from Claude Desktop. Learn how to automate Photoshop operations and streamline your image editing workflow using Claude Desktop's MCP (Model Context Protocol) feature.

## Overview

Using Claude Desktop's MCP feature, you can connect Claude to external systems and APIs. This repository demonstrates how to connect Claude Desktop to Photoshop MCP Server and automate Photoshop operations.

Key features:
- Open and save files in Photoshop from Claude Desktop
- Image analysis and automatic retouching
- Create and edit adjustment layers
- Apply filters
- Automate batch processing

## Prerequisites

The following software and tools are required:

1. **Claude Desktop**
   - Latest version of Claude Desktop installed
   - MCP server integration feature enabled

2. **Adobe Photoshop**
   - Adobe Photoshop 2022 or later
   - Version that supports UXP plugins

3. **Photoshop MCP Server**
   - Photoshop MCP Server from this repository installed
   - Required dependencies installed

4. **Python Environment**
   - Python 3.11 or higher
   - pip package manager

## Setup Instructions

### 1. Install Photoshop MCP Server

If you haven't installed it yet, install Photoshop MCP Server with the following commands:

```bash
git clone https://github.com/your-repo/photoshop_mcp_server.git
cd photoshop_mcp_server
pip install -e .
```

### 2. Install Required Libraries

Install the libraries needed for this sample:

```bash
pip install requests
```

### 3. Configure Photoshop MCP Server

1. Start Photoshop MCP Server:

```bash
python -m photoshop_mcp_server.server
```

2. Launch Photoshop and verify that the UXP plugin is loaded correctly.

### 4. Configure Claude Desktop MCP

1. Launch Claude Desktop.
2. Open "MCP Settings" from the settings menu.
3. Click "New MCP Connection".
4. Enter the following information:
   - Server name: `photoshop-mcp`
   - Endpoint: `http://localhost:5001`
   - Description: `Photoshop MCP Server`
5. Click "Test Connection" to test the connection.
6. Click "Save" to save the settings.

## Usage Examples

### Basic Operations

You can operate Photoshop from Claude Desktop using prompts like:

```
Create a new image in Photoshop, add a text layer, and display "Hello World".
```

Claude Desktop will connect to Photoshop MCP Server through MCP and execute the instructions.

### Running Sample Code

This repository includes sample code for operating Photoshop MCP Server from Claude Desktop. You can run it with the following command:

```bash
python claude_photoshop_mcp.py --operation open --file path/to/image.jpg
```

Available operations:
- `open`: Open an image file
- `save`: Save the current image
- `analyze`: Analyze an image
- `retouch`: Auto-retouch an image
- `apply_filter`: Apply a filter

For detailed options, use the `--help` option:

```bash
python claude_photoshop_mcp.py --help
```

### Customization

The sample code can be easily customized to suit your needs:

1. To add new operations, add new methods to the `PhotoshopMCPClient` class.
2. To create complex workflows, combine multiple operations to create new functions.
3. You can create your own prompt templates optimized for specific tasks.

## Troubleshooting

### Connection Issues

- Make sure Photoshop MCP Server is running.
- Verify that port 5001 is not being used by other applications.
- Ensure that your firewall allows connections to port 5001.

### Photoshop Issues

- Make sure Photoshop is running.
- Verify that the UXP plugin is loaded correctly.
- Try restarting Photoshop to reload the plugin.

### Claude Desktop Issues

- Verify that the Claude Desktop MCP settings are correct.
- Try restarting Claude Desktop.
- Check the MCP connection logs for error messages.

## Additional Information

- [Photoshop MCP Server Documentation](https://github.com/StarBoze/Photoshop-MCP-Server/blob/main/docs/)
- [Claude Desktop MCP Documentation](https://claude.ai/docs/mcp)
- [Adobe UXP Plugin Development Guide](https://developer.adobe.com/photoshop/uxp/2022/)