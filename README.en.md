# Photoshop MCP Server

A project for remotely controlling Photoshop on macOS and Windows using the Model Context Protocol (MCP) server.

## Overview

This project implements an MCP server using FastAPI to control Photoshop through the following methods:

### macOS
1. AppleScript backend - Works with all Photoshop versions
2. UXP Plug-in backend - Works with Photoshop CC 2021 and above (WebSocket communication)

### Windows
1. PowerShell backend - Works with all Photoshop versions
2. UXP Plug-in backend - Works with Photoshop CC 2021 and above (WebSocket communication)

## Features

- REST/WebSocket endpoints using FastAPI/Starlette
- Cross-platform support (macOS/Windows)
- Photoshop control via AppleScript/PowerShell backend
- Photoshop control via UXP Plug-in backend (WebSocket communication)
- Plugin packaging functionality
- Thumbnail generation (with WebSocket streaming support)
- Cluster mode for managing multiple Photoshop instances
- LLM automatic retouching functionality

## Requirements

- Python 3.11 or higher
- macOS or Windows 10/11
- Adobe Photoshop 2023 or higher

## Installation

```bash
pip install photoshop-mcp-server
```

Or install from source:

```bash
git clone https://github.com/StarBoze/photoshop-mcp-server.git
cd photoshop-mcp-server
pip install -e .
```

For detailed installation instructions, refer to the [Installation Guide](docs/installation.md).

### Environment Setup Details

#### Creating and Managing Virtual Environments

Using a Python virtual environment helps avoid dependency conflicts:

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment (macOS/Linux)
source venv/bin/activate

# Activate the virtual environment (Windows)
venv\Scripts\activate

# Install dependencies
pip install -e .
```

#### Dependencies

Main dependencies:

- FastAPI: Implementation of REST and WebSocket endpoints
- Uvicorn: ASGI server
- Pydantic: Data validation
- Starlette: WebSocket support
- psutil: Process management (Cluster mode)
- grpcio: gRPC communication (Cluster mode)
- litellm: LLM integration (automatic retouching functionality)

#### Execution Modes

The server can be run in the following modes:

- **Normal mode**: `photoshop-mcp-server start`
  - Starts the server in the background

- **Foreground mode**: `photoshop-mcp-server start --foreground`
  - Runs with logs displayed in the terminal
  - Useful for debugging

- **Debug mode**: `photoshop-mcp-server start --debug`
  - Displays detailed logs
  - Also shows request and response contents

- **UXP mode**: `photoshop-mcp-server start --bridge-mode uxp`
  - Controls Photoshop using the UXP plugin

## Usage

### Basic Usage

```bash
# Start the server (with default backend for the platform)
photoshop-mcp-server start

# Display help
photoshop-mcp-server --help
```

### Specifying Platform-Specific Backends

```bash
# Use AppleScript backend on macOS
photoshop-mcp-server start --bridge-mode applescript

# Use PowerShell backend on Windows
photoshop-mcp-server start --bridge-mode powershell

# Use UXP backend (cross-platform)
photoshop-mcp-server start --bridge-mode uxp
```

For detailed usage instructions, refer to the [documentation](docs/).

### Using the UXP Backend

To use the UXP backend, follow these steps:

1. Package the UXP plugin
```bash
photoshop-mcp-server package_plugin
```

2. Display UXP plugin installation instructions
```bash
photoshop-mcp-server install_plugin
```

3. Follow the displayed instructions to install the plugin

4. Start the server with UXP backend enabled
```bash
photoshop-mcp-server start --bridge-mode uxp
```

5. Set the `bridge_mode` parameter to `uxp` when making API requests
```
POST /openFile
{
  "path": "/path/to/file.psd",
  "bridge_mode": "uxp"
}
```

### UXP Plugin Installation Details

To use the UXP plugin, you need the Adobe UXP Developer Tool.

#### Installing Adobe UXP Developer Tool

1. Download the latest version from [Adobe UXP Developer Tool](https://developer.adobe.com/photoshop/uxp/devtool/)
2. Run the downloaded installer and follow the instructions to install
3. After installation, launch the Adobe UXP Developer Tool

#### Plugin Installation Procedure

1. Package the plugin
   ```bash
   photoshop-mcp-server package_plugin
   ```
   This creates a plugin package at `dist/photoshop-mcp.zip`.

2. Add the plugin in UXP Developer Tool
   - Click the "Add Plugin" button in UXP Developer Tool
   - Select the created `dist/photoshop-mcp.zip`
   - Load the plugin (click the "Load" button)

3. Activate in Photoshop
   - Launch Photoshop (or restart if already running)
   - Select "Photoshop MCP" from the plugins menu to activate

4. Start the MCP server (UXP mode)
   ```bash
   photoshop-mcp-server start --bridge-mode uxp
   ```

5. Verify connection
   - If the server logs show "UXP Plugin connected", the connection is successful
   - If the connection fails, refer to [Troubleshooting](#troubleshooting)

### WebSocket Endpoint

When using the UXP backend, a WebSocket endpoint is also available:

```
ws://localhost:5001/ws
```

You can send and receive JSON messages directly through WebSocket.

## Cross-Platform Support Details

From v0.2.0, Photoshop MCP Server has full cross-platform support. The following features have been added:

### Platform Detection and Abstraction

The `platform_utils.py` module provides the following features:

- Platform detection functions (`get_platform()`, `is_windows()`, `is_macos()`)
- Platform-specific settings (`get_platform_config()`)
- Platform-specific temporary file management (`get_temp_file()`)
- Platform-specific conditional branching (`platform_specific` decorator)

```python
# Example of platform-specific processing
from photoshop_mcp_server.bridge.platform_utils import platform_specific

@platform_specific(
    windows_func=windows_specific_function,
    macos_func=macos_specific_function,
    default_func=default_function
)
def process_file(path):
    # The appropriate function for the platform is automatically called
    pass
```

### Performance Optimization

- Script caching for improved execution speed (average 30% speedup)
- Script execution timeout settings (default 30 seconds)
- Efficient temporary file management (automatic cleanup)
- Parallel processing optimization (50% faster when processing large numbers of files)
- Reduced memory usage (40% reduction when processing large PSD files)

## New Features in Phase v1.1

- UXP Plug-in backend support (WebSocket communication)
- Plugin packaging functionality
- Installation instruction display
- Extended health check endpoint (UXP plugin connection status check)

## New Features in Phase v1.2

### Thumbnail Generation

- REST endpoint for generating thumbnails from PSD files
- Thumbnail generation with specified size, format (JPEG/PNG)
- Return of Base64 encoded image data

```
POST /generateThumbnail
{
  "path": "/path/to/file.psd",
  "width": 256,
  "height": 256,
  "format": "jpeg",
  "quality": 80,
  "bridge_mode": "uxp"
}
```

### WebSocket Streaming

- WebSocket endpoint for streaming thumbnail generation progress in real-time
- Notification of progress for each step (opening file, generating thumbnail, image processing, etc.)
- Real-time notification in case of errors

```
WebSocket endpoint: ws://localhost:5001/generateThumbnail/stream

Request:
{
  "path": "/path/to/file.psd",
  "width": 256,
  "height": 256,
  "format": "jpeg",
  "quality": 80,
  "bridge_mode": "uxp"
}

Response (streaming):
{
  "type": "start",
  "data": { ... }
}
{
  "type": "progress",
  "data": { "step": "opening_file", "progress": 10, "message": "Opening file..." }
}
{
  "type": "progress",
  "data": { "step": "generating_thumbnail", "progress": 30, "message": "Generating thumbnail..." }
}
...
{
  "type": "complete",
  "data": { "width": 256, "height": 256, "format": "jpeg" }
}
```

## New Features in Phase v2.0

### Cluster Mode

Cluster mode is a feature for managing multiple Photoshop instances and distributing jobs.
It is designed to efficiently process large numbers of image processing tasks.

#### Main Features

- Management of multiple Photoshop instances (nodes)
- Job distribution and load balancing
- Automatic failover
- Health check and monitoring
- Various routing strategies (least load, round-robin, lowest latency, etc.)

#### Using Cluster Mode

1. Start the dispatcher

```bash
# Start the dispatcher
photoshop-mcp-server start_cluster --host 127.0.0.1 --port 8001
```

2. Start the nodes

```bash
# Start node 1
photoshop-mcp-server start_node --host 127.0.0.1 --port 8002 --dispatcher 127.0.0.1:8001

# Start node 2
photoshop-mcp-server start_node --host 127.0.0.1 --port 8003 --dispatcher 127.0.0.1:8001
```

3. Submit jobs using the API

```
POST http://127.0.0.1:8001/submit_job
{
  "job_type": "open_file",
  "payload": {
    "path": "/path/to/file.psd"
  },
  "priority": 1
}
```

#### Configuration Example

```python
# Dispatcher configuration
dispatcher_config = {
    "host": "127.0.0.1",
    "port": 8001,
    "routing_strategy": "least_busy",  # least_busy, round_robin, random, lowest_latency, capability_based
    "node_timeout": 60.0,
    "job_timeout": 300.0,
    "health_check_interval": 30.0
}

# Node configuration
node_config = {
    "host": "127.0.0.1",
    "port": 8002,
    "dispatcher": "127.0.0.1:8001",
    "capabilities": ["open_file", "save_file", "export_layer", "run_action"],
    "max_concurrent_jobs": 5
}
```

### LLM Automatic Retouching

The LLM automatic retouching feature uses LiteLLM to analyze images and automatically perform retouching.
It uses multimodal models like GPT-4 Vision to analyze images and generate optimal retouching parameters.

#### Main Features

- Automatic image analysis
- Automatic generation of retouching parameters
- Automatic execution of Photoshop actions
- Adjustment via custom prompts

#### Using LLM Automatic Retouching

```
POST /autoRetouch
{
  "path": "/path/to/image.jpg",
  "instructions": "Smooth the skin and increase the contrast",
  "bridge_mode": "uxp"
}
```

Response:

```json
{
  "analysis": {
    "basic_info": {
      "image_type": "Portrait",
      "main_subject": "Woman",
      "overall_impression": "Outdoor portrait taken in natural light"
    },
    "technical_characteristics": {
      "brightness": {
        "status": "Slightly dark",
        "value": -15
      },
      "contrast": {
        "status": "Weak",
        "value": -20
      },
      ...
    },
    ...
  },
  "retouch_actions": [
    {
      "type": "brightness_contrast",
      "params": {
        "brightness": 15,
        "contrast": 20
      }
    },
    {
      "type": "skin_smoothing",
      "params": {
        "strength": 30,
        "detail": 50
      }
    },
    ...
  ],
  "execution_result": {
    "status": "success",
    "actions_applied": 5,
    "execution_time": 3.5
  }
}
```

#### Custom Prompt Example

```
This image is a portrait taken outdoors. Please focus on the following aspects for retouching:
1. Smooth the skin (strength: medium)
2. Increase brightness and contrast of the eyes
3. Slightly blur the background
4. Adjust the overall color tone to a warm atmosphere
```

## MCP Client Configuration

To integrate Photoshop MCP Server with AI assistants or other MCP clients, a configuration file is required.

### Configuration File Structure

The configuration file is typically placed in `mcp-config/photoshop-mcp-server.json` and has the following structure:

```json
{
  "server_info": {
    "name": "photoshop-mcp-server",
    "description": "Photoshop MCP Server for macOS and Windows",
    "version": "0.2.0",
    "endpoint": "http://localhost:5001"
  },
  "tools": [
    {
      "name": "open_file",
      "description": "Open a file in Photoshop",
      "input_schema": {
        "type": "object",
        "properties": {
          "path": {
            "type": "string",
            "description": "Path to the file"
          },
          "bridge_mode": {
            "type": "string",
            "description": "Bridge mode to use (applescript, powershell, uxp)",
            "default": "default"
          }
        },
        "required": ["path"]
      }
    },
    {
      "name": "save_file",
      "description": "Save the current file",
      "input_schema": {
        "type": "object",
        "properties": {
          "path": {
            "type": "string",
            "description": "Path to save the file"
          },
          "format": {
            "type": "string",
            "description": "File format (psd, jpg, png, tiff)",
            "default": "psd"
          },
          "bridge_mode": {
            "type": "string",
            "description": "Bridge mode to use",
            "default": "default"
          }
        },
        "required": ["path"]
      }
    },
    {
      "name": "run_action",
      "description": "Run a Photoshop action",
      "input_schema": {
        "type": "object",
        "properties": {
          "action_set": {
            "type": "string",
            "description": "Action set name"
          },
          "action_name": {
            "type": "string",
            "description": "Action name"
          },
          "bridge_mode": {
            "type": "string",
            "description": "Bridge mode to use",
            "default": "default"
          }
        },
        "required": ["action_set", "action_name"]
      }
    },
    {
      "name": "generate_thumbnail",
      "description": "Generate a thumbnail from a PSD file",
      "input_schema": {
        "type": "object",
        "properties": {
          "path": {
            "type": "string",
            "description": "Path to the PSD file"
          },
          "width": {
            "type": "integer",
            "description": "Thumbnail width",
            "default": 256
          },
          "height": {
            "type": "integer",
            "description": "Thumbnail height",
            "default": 256
          },
          "format": {
            "type": "string",
            "description": "Image format (jpeg, png)",
            "default": "jpeg"
          },
          "quality": {
            "type": "integer",
            "description": "Image quality (1-100)",
            "default": 80
          },
          "bridge_mode": {
            "type": "string",
            "description": "Bridge mode to use",
            "default": "default"
          }
        },
        "required": ["path"]
      }
    },
    {
      "name": "auto_retouch",
      "description": "Auto retouch an image using LLM",
      "input_schema": {
        "type": "object",
        "properties": {
          "path": {
            "type": "string",
            "description": "Path to the image"
          },
          "instructions": {
            "type": "string",
            "description": "Retouch instructions"
          },
          "bridge_mode": {
            "type": "string",
            "description": "Bridge mode to use",
            "default": "default"
          }
        },
        "required": ["path", "instructions"]
      }
    }
  ],
  "resources": [
    {
      "uri": "photoshop://status",
      "description": "Get server status"
    },
    {
      "uri": "photoshop://version",
      "description": "Get server version"
    },
    {
      "uri": "photoshop://plugin/status",
      "description": "Get UXP plugin status"
    }
  ]
}
```

### Configuration File Placement

1. Create the `mcp-config` directory (if it doesn't exist)
2. Save the above configuration file as `mcp-config/photoshop-mcp-server.json`
3. Ensure that the MCP client can read this configuration file

### Client Implementation Examples

#### JavaScript (WebSocket)

```javascript
// Thumbnail generation streaming using WebSocket
const ws = new WebSocket('ws://localhost:5001/generateThumbnail/stream');

ws.onopen = () => {
  // Send request
  ws.send(JSON.stringify({
    path: '/path/to/file.psd',
    width: 256,
    height: 256,
    format: 'jpeg',
    quality: 80,
    bridge_mode: 'uxp'
  }));
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  
  switch (message.type) {
    case 'start':
      console.log('Thumbnail generation started:', message.data);
      break;
    case 'progress':
      console.log(`Progress: ${message.data.progress}% - ${message.data.message}`);
      updateProgressBar(message.data.progress);
      break;
    case 'complete':
      console.log('Thumbnail generation completed:', message.data);
      break;
    case 'error':
      console.error('Error:', message.data.message);
      break;
  }
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('WebSocket connection closed');
};
```

#### Python (REST API)

```python
import requests
import base64
from PIL import Image
import io

# Thumbnail generation request
response = requests.post('http://localhost:5001/generateThumbnail', json={
    'path': '/path/to/file.psd',
    'width': 256,
    'height': 256,
    'format': 'jpeg',
    'quality': 80,
    'bridge_mode': 'uxp'
})

if response.status_code == 200:
    data = response.json()
    # Decode Base64 encoded image data
    image_data = base64.b64decode(data['thumbnail'])
    
    # Open image with PIL
    image = Image.open(io.BytesIO(image_data))
    
    # Save image
    image.save('thumbnail.jpg')
    print(f"Thumbnail generation successful: {data['width']}x{data['height']} ({data['format']})")
else:
    print(f"Error: {response.status_code} - {response.text}")
```

#### Python (Cluster API)

```python
import requests

# Submit job
response = requests.post('http://localhost:8001/submit_job', json={
    'job_type': 'auto_retouch',
    'payload': {
        'path': '/path/to/image.jpg',
        'instructions': 'Smooth the skin and increase the contrast'
    },
    'priority': 2
})

if response.status_code == 200:
    data = response.json()
    job_id = data['job_id']
    print(f"Job submission successful: {job_id}")
    
    # Check job status
    status_response = requests.get(f'http://localhost:8001/job_status/{job_id}')
    if status_response.status_code == 200:
        status_data = status_response.json()
        print(f"Job status: {status_data['status']}")
else:
    print(f"Error: {response.status_code} - {response.text}")
```

## Use Cases

With Photoshop MCP Server, you can automate Photoshop control from AI assistants and other applications. Here are the main use cases:

### Image Editing Automation with AI Assistants

- **Prompt-based image editing**
  - Control Photoshop with natural language instructions like "blur the background and brighten the person in the foreground"
  - Execute complex editing procedures with natural language instructions, which AI converts into Photoshop commands

- **Batch processing automation**
  - Process multiple files in batch with instructions like "apply the same edits to all images in the folder"
  - Automate image resizing, format conversion, filter application, etc.

### LLM Automatic Retouching

- **Image analysis and automatic correction**
  - AI analyzes images and automatically determines optimal adjustment values for brightness, contrast, saturation, etc.
  - Automatically execute skin correction for portrait photos, color correction for landscape photos, etc.

- **Style transfer and creative editing**
  - Style transfer with instructions like "edit this photo to have a sunset atmosphere"
  - AI selects and applies appropriate layer effects and filters

### Workflow Integration

- **Integration with other tools**
  - Process image editing requests from web applications
  - Automate editing workflows by integrating with image management systems

- **Background processing**
  - Image processing in headless mode (executed without UI)
  - Large-scale image processing in server environments

### Distributed Processing with Cluster Mode

- **Parallel processing with multiple Photoshop instances**
  - Distribute large numbers of images across multiple Photoshop instances for processing
  - Significantly improve processing speed and efficiency

- **Load balancing and redundancy**
  - Dynamic job assignment based on processing load
  - Continue processing even if some nodes fail

### Specific Use Cases

- **Batch processing of e-commerce product images**
  - Automate background removal, size standardization, watermark addition, etc.
  - Generate multiple variations of product images in batch

- **Automating post-processing for photo studios**
  - Automate skin correction and color adjustment for portrait photos
  - Apply editing styles based on client requirements

- **Mass generation of marketing materials**
  - Apply different text and images to the same design template
  - Automatically generate multiple size variations for social media

- **Optimization of image archives**
  - Automate restoration and optimization of old photos
  - Add metadata and standardize image formats

## Integration with AI Assistants

Photoshop MCP Server provides an interface for controlling Photoshop from AI assistants.

### Integration Mechanism

1. Register the MCP client configuration file with the AI assistant
2. The AI assistant communicates with Photoshop MCP Server through the MCP protocol
3. Photoshop MCP Server controls Photoshop

### Sample Prompt Example

```
Please perform the following operations in Photoshop:
1. Open the image file "/path/to/image.jpg"
2. Adjust brightness and contrast to brighten the image
3. Save the result as "/path/to/output.jpg"
```

### AI Assistant Response Example

```
I'll execute the operations in Photoshop.

1. Opening the image file...
   - File: /path/to/image.jpg
   - Status: Success

2. Adjusting brightness and contrast...
   - Brightness: +15
   - Contrast: +10
   - Status: Success

3. Saving the result...
   - Save location: /path/to/output.jpg
   - Format: JPEG
   - Quality: 90%
   - Status: Success

All operations completed successfully.
```

### Integration Notes

- The AI assistant needs to have access to the local file system
- It is recommended to specify file paths as absolute paths
- Processing large files may take time
- When using the UXP plugin, Photoshop must be running

## Troubleshooting

### Common Problems and Solutions

#### Server Startup Errors

**Problem**: Server does not start or exits immediately after startup

**Solution**:
- Check if port 5001 is being used by another application
  ```bash
  # macOS/Linux
  lsof -i :5001
  
  # Windows
  netstat -ano | findstr :5001
  ```
- Start with a different port
  ```bash
  photoshop-mcp-server start --port 5002
  ```
- Check log files
  ```bash
  cat ~/.photoshop_mcp_server/logs/server.log
  ```

#### UXP Plugin Connection Errors

**Problem**: UXP plugin cannot connect to the server

**Solution**:
- Verify that Photoshop is running
- Verify that the UXP plugin is correctly installed
- Verify that the server and plugin are using the same port
- Check if the firewall is blocking WebSocket connections
- Restart the server and Photoshop

#### AppleScript/PowerShell Errors

**Problem**: Errors occur with AppleScript or PowerShell backend

**Solution**:
- Verify that Photoshop is running
- Check script execution permissions
  - macOS: `sudo chmod +x /usr/bin/osascript`
  - Windows: Check PowerShell execution policy `Get-ExecutionPolicy`
- Check detailed logs in debug mode
  ```bash
  photoshop-mcp-server start --debug --foreground
  ```

### Log File Locations

Log files are saved in the following locations:

- macOS: `~/.photoshop_mcp_server/logs/`
- Windows: `%USERPROFILE%\.photoshop_mcp_server\logs\`

Main log files:
- `server.log`: Main server log
- `api.log`: API request and response log
- `bridge.log`: Backend (AppleScript/PowerShell/UXP) log
- `cluster.log`: Cluster mode log

### Support and Feedback

If you cannot resolve an issue, please create an [Issue on GitHub](https://github.com/StarBoze/photoshop-mcp-server/issues) with the following information:

- OS you are using (including version)
- Photoshop version
- Command executed
- Error message
- Relevant parts of the log files

## License

MIT License

Copyright (C) 2025 StarBoze https://github.com/StarBoze