# LLM Integration Examples

This directory contains examples of how to use LLMs (Large Language Models) with Photoshop MCP Server using the `litellm` library for abstraction.

## Overview

These examples demonstrate how to:

1. Create a unified interface for interacting with various LLM providers (OpenAI, Anthropic, Google, etc.)
2. Analyze images using vision-capable LLMs
3. Generate Photoshop retouch instructions based on image analysis and user instructions
4. Analyze layer structure of PSD files
5. Generate non-destructive retouch instructions using adjustment layers

## Requirements

- Python 3.11+
- litellm
- Photoshop MCP Server

## Installation

```bash
pip install litellm
```

## Configuration

Set the appropriate API keys as environment variables:

```bash
# For OpenAI
export OPENAI_API_KEY=your_openai_api_key

# For Anthropic
export ANTHROPIC_API_KEY=your_anthropic_api_key

# For Google
export GOOGLE_API_KEY=your_google_api_key

# For Azure OpenAI
export AZURE_OPENAI_API_KEY=your_azure_api_key
export AZURE_API_BASE=your_azure_endpoint
```

## Examples

### Image Analysis

Analyze an image using a vision-capable LLM:

```bash
python image_analysis.py path/to/image.jpg --provider openai --advanced --output analysis.json
```

Options:
- `--provider`: LLM provider to use (openai, anthropic, google)
- `--model`: Specific model to use (optional)
- `--advanced`: Use advanced analysis prompt
- `--output`: Path to save analysis results (if not provided, print to console)

### Retouch Generation

Generate Photoshop retouch instructions based on image analysis and user instructions:

```bash
python retouch_generation.py path/to/image.jpg --instructions "Make the image brighter and enhance the colors" --style natural --output retouch.json
```

Options:
- `--instructions`: User instructions for retouching
- `--provider`: LLM provider to use (openai, anthropic, google)
- `--model`: Specific model to use (optional)
- `--style`: Retouch style to apply (natural, dramatic, vintage, black_and_white, high_key, low_key)
- `--analysis`: Path to existing analysis JSON (if not provided, will analyze the image)
- `--output`: Path to save retouch instructions (if not provided, print to console)

### Layer Analysis

Analyze the layer structure of a PSD file:

```bash
python adjustment_layer_retouch.py path/to/file.psd --analyze-only --output layer_analysis.json
```

Options:
- `--analyze-only`: Only analyze layers without generating retouch instructions
- `--provider`: LLM provider to use (openai, anthropic, google)
- `--model`: Specific model to use (optional)
- `--output`: Path to save layer analysis results (if not provided, print to console)

### Adjustment Layer Retouch

Generate and apply non-destructive retouch instructions using adjustment layers:

```bash
python adjustment_layer_retouch.py path/to/image.psd --instructions "Enhance contrast and make colors more vibrant" --output retouch.json --apply
```

Options:
- `--instructions`: User instructions for retouching
- `--provider`: LLM provider to use (openai, anthropic, google)
- `--model`: Specific model to use (optional)
- `--layer-analysis`: Path to existing layer analysis JSON (if not provided and PSD file, will analyze layers)
- `--output`: Path to save retouch instructions (if not provided, print to console)
- `--apply`: Apply the generated retouch instructions using Photoshop MCP Server
- `--server-url`: URL of the Photoshop MCP Server (default: http://localhost:5001)

## Integration with Photoshop MCP Server

These examples can be integrated with Photoshop MCP Server to automate the retouching process:

### Basic Retouch Workflow

```python
import json
import requests

# 1. Analyze image
analysis_result = analyze_image("path/to/image.jpg", provider="openai", advanced=True)

# 2. Generate retouch instructions
retouch_instructions = generate_retouch(
    "path/to/image.jpg",
    instructions="Enhance the colors and make it more vibrant",
    provider="openai",
    style="natural",
)

# 3. Apply retouch instructions using Photoshop MCP Server
for step in retouch_instructions["retouch_steps"]:
    # Convert step to MCP Server command
    command = {
        "action": step["action"],
        "parameters": step["parameters"]
    }
    
    # Send command to MCP Server
    response = requests.post(
        "http://localhost:5001/api/execute",
        json=command,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Step {step['step']}: {response.status_code}")

# 4. Save the result
save_command = {
    "action": "save_file",
    "parameters": {
        "path": "path/to/output.jpg",
        "format": "jpg",
        "quality": 90
    }
}

response = requests.post(
    "http://localhost:5001/api/execute",
    json=save_command,
    headers={"Content-Type": "application/json"}
)

print(f"Save result: {response.status_code}")
```

### Non-destructive Adjustment Layer Workflow

```python
import json
import requests

# 1. Analyze PSD layers
layer_analysis = analyze_layers("path/to/image.psd", provider="openai")

# 2. Generate adjustment layer retouch instructions
retouch_instructions = generate_adjustment_layer_retouch(
    "path/to/image.psd",
    instructions="Enhance contrast and make colors more vibrant",
    provider="openai",
    layer_analysis=layer_analysis,
)

# 3. Apply adjustment layers using Photoshop MCP Server
for step in retouch_instructions["retouch_steps"]:
    # Check if step is for creating adjustment layer
    if step["action"] != "create_adjustment_layer":
        continue
    
    # Prepare command for MCP Server
    command = {
        "action": "create_adjustment_layer",
        "parameters": step["parameters"]
    }
    
    # Send command to MCP Server
    response = requests.post(
        "http://localhost:5001/api/execute",
        json=command,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Step {step['step']}: {response.status_code}")

# 4. Save the result as PSD to preserve layers
save_command = {
    "action": "save_file",
    "parameters": {
        "path": "path/to/output.psd",
        "format": "psd"
    }
}

response = requests.post(
    "http://localhost:5001/api/execute",
    json=save_command,
    headers={"Content-Type": "application/json"}
)

print(f"Save result: {response.status_code}")
```

## Advanced Usage

### Custom Prompts

You can customize the analysis and retouch prompts by modifying the templates in each script.

### Multiple LLM Providers

The `LLMClient` class supports multiple LLM providers and can be easily switched:

```python
# Using OpenAI
openai_client = LLMClient(provider="openai", model="gpt-4-vision-preview")

# Using Anthropic
anthropic_client = LLMClient(provider="anthropic", model="claude-3-sonnet-20240229")

# Using Google
google_client = LLMClient(provider="google", model="gemini-pro-vision")
```

### Error Handling

The examples include basic error handling, but it's recommended to add more robust error handling for production use.