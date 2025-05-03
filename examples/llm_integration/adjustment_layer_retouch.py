"""
Adjustment Layer Retouch Example

This script demonstrates how to use the LLM client for generating non-destructive
retouch instructions using Photoshop adjustment layers.
"""

import os
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from llm_client import LLMClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Adjustment layer types and their parameters
ADJUSTMENT_LAYER_TYPES = {
    "levels": {
        "description": "Adjusts tonal range and color balance",
        "parameters": ["input_black", "input_white", "gamma", "output_black", "output_white"]
    },
    "curves": {
        "description": "Adjusts tonal range with precise curve control",
        "parameters": ["curve_points", "channel"]
    },
    "brightness_contrast": {
        "description": "Adjusts brightness and contrast",
        "parameters": ["brightness", "contrast"]
    },
    "exposure": {
        "description": "Adjusts exposure, offset, and gamma correction",
        "parameters": ["exposure", "offset", "gamma"]
    },
    "hue_saturation": {
        "description": "Adjusts hue, saturation, and lightness",
        "parameters": ["hue", "saturation", "lightness", "colorize"]
    },
    "color_balance": {
        "description": "Adjusts color balance in shadows, midtones, and highlights",
        "parameters": ["shadows", "midtones", "highlights", "preserve_luminosity"]
    },
    "black_white": {
        "description": "Converts to black and white with control over color channels",
        "parameters": ["reds", "yellows", "greens", "cyans", "blues", "magentas"]
    },
    "photo_filter": {
        "description": "Applies a color filter to the image",
        "parameters": ["filter_color", "density", "preserve_luminosity"]
    },
    "channel_mixer": {
        "description": "Modifies color channels",
        "parameters": ["red_channel", "green_channel", "blue_channel", "constant"]
    },
    "color_lookup": {
        "description": "Applies a color lookup table",
        "parameters": ["lookup_table"]
    },
    "vibrance": {
        "description": "Adjusts vibrance and saturation",
        "parameters": ["vibrance", "saturation"]
    },
    "selective_color": {
        "description": "Adjusts the amount of process colors in color components",
        "parameters": ["colors", "method"]
    },
    "gradient_map": {
        "description": "Maps grayscale range to a gradient fill",
        "parameters": ["gradient", "dither", "reverse"]
    }
}

# Blend modes
BLEND_MODES = [
    "normal", "dissolve", "darken", "multiply", "color_burn", "linear_burn", "darker_color",
    "lighten", "screen", "color_dodge", "linear_dodge", "lighter_color", "overlay", "soft_light",
    "hard_light", "vivid_light", "linear_light", "pin_light", "hard_mix", "difference", 
    "exclusion", "subtract", "divide", "hue", "saturation", "color", "luminosity"
]

def analyze_layers(
    image_path: str,
    provider: str = "openai",
    model: str = None,
    output_path: str = None,
) -> Dict[str, Any]:
    """
    Analyze the layer structure of a PSD file.
    
    Args:
        image_path: Path to the PSD file
        provider: LLM provider to use
        model: Specific model to use (if None, default model for provider will be used)
        output_path: Path to save analysis results (if None, print to console)
        
    Returns:
        The layer analysis result
    """
    # Verify image exists
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    # Initialize LLM client
    client = LLMClient(
        provider=provider,
        model=model,
        temperature=0.3,  # Lower temperature for more consistent analysis
    )
    
    logger.info(f"Analyzing layers of: {image_path}")
    
    # Perform layer analysis
    response = client.analyze_layers(image_path)
    
    # Get the content
    layer_analysis = response["content"]
    
    # Save or print results
    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(layer_analysis, f, indent=2)
        logger.info(f"Layer analysis saved to: {output_path}")
    else:
        print(json.dumps(layer_analysis, indent=2))
    
    return layer_analysis

def generate_adjustment_layer_retouch(
    image_path: str,
    instructions: str,
    provider: str = "openai",
    model: str = None,
    layer_analysis_path: str = None,
    output_path: str = None,
) -> Dict[str, Any]:
    """
    Generate non-destructive retouch instructions using adjustment layers.
    
    Args:
        image_path: Path to the image file
        instructions: User instructions for retouching
        provider: LLM provider to use
        model: Specific model to use (if None, default model for provider will be used)
        layer_analysis_path: Path to existing layer analysis JSON (if None and PSD file, will analyze layers)
        output_path: Path to save retouch instructions (if None, print to console)
        
    Returns:
        The adjustment layer retouch instructions
    """
    # Verify image exists
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    # Initialize LLM client
    client = LLMClient(
        provider=provider,
        model=model,
        temperature=0.7,  # Higher temperature for more creative retouch suggestions
    )
    
    # Get layer analysis if path provided
    layer_analysis = None
    if layer_analysis_path and os.path.exists(layer_analysis_path):
        logger.info(f"Loading layer analysis from: {layer_analysis_path}")
        with open(layer_analysis_path, "r") as f:
            layer_analysis = json.load(f)
    
    logger.info(f"Generating adjustment layer retouch instructions for: {image_path}")
    logger.info(f"Using provider: {provider}")
    
    # Generate adjustment layer retouch instructions
    response = client.generate_adjustment_layer_retouch(
        image_path=image_path,
        instructions=instructions,
        layer_analysis=layer_analysis,
    )
    
    # Get the content
    retouch_instructions = response["content"]
    
    # Save or print results
    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(retouch_instructions, f, indent=2)
        logger.info(f"Retouch instructions saved to: {output_path}")
    else:
        print(json.dumps(retouch_instructions, indent=2))
    
    return retouch_instructions

def apply_adjustment_layers(
    retouch_instructions: Dict[str, Any],
    mcp_server_url: str = "http://localhost:5001",
) -> None:
    """
    Apply adjustment layer retouch instructions using Photoshop MCP Server.
    
    Args:
        retouch_instructions: The retouch instructions
        mcp_server_url: The URL of the Photoshop MCP Server
    """
    import requests
    
    # Check if retouch_steps exists
    if "retouch_steps" not in retouch_instructions:
        logger.error("Invalid retouch instructions: 'retouch_steps' not found")
        return
    
    # Apply each step
    for step in retouch_instructions["retouch_steps"]:
        logger.info(f"Applying step {step['step']}: {step.get('description', '')}")
        
        # Check if step is for creating adjustment layer
        if step["action"] != "create_adjustment_layer":
            logger.warning(f"Unsupported action: {step['action']}")
            continue
        
        # Prepare command for MCP Server
        command = {
            "action": "create_adjustment_layer",
            "parameters": step["parameters"]
        }
        
        # Send command to MCP Server
        try:
            response = requests.post(
                f"{mcp_server_url}/api/execute",
                json=command,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                logger.info(f"Step {step['step']} applied successfully")
            else:
                logger.error(f"Failed to apply step {step['step']}: {response.status_code} - {response.text}")
        
        except Exception as e:
            logger.error(f"Error applying step {step['step']}: {e}")
    
    logger.info("Finished applying adjustment layers")

def main():
    """Main function to run the script from command line."""
    parser = argparse.ArgumentParser(description="Generate and apply non-destructive retouch using adjustment layers")
    parser.add_argument("image_path", help="Path to the image file")
    parser.add_argument(
        "--instructions",
        required=True,
        help="User instructions for retouching",
    )
    parser.add_argument(
        "--provider",
        choices=["openai", "anthropic", "google"],
        default="openai",
        help="LLM provider to use",
    )
    parser.add_argument("--model", help="Specific model to use")
    parser.add_argument(
        "--analyze-only",
        action="store_true",
        help="Only analyze layers without generating retouch instructions",
    )
    parser.add_argument(
        "--layer-analysis",
        help="Path to existing layer analysis JSON (if not provided and PSD file, will analyze layers)",
    )
    parser.add_argument(
        "--output",
        help="Path to save retouch instructions (if not provided, print to console)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the generated retouch instructions using Photoshop MCP Server",
    )
    parser.add_argument(
        "--server-url",
        default="http://localhost:5001",
        help="URL of the Photoshop MCP Server (default: http://localhost:5001)",
    )
    
    args = parser.parse_args()
    
    # Analyze layers only if requested
    if args.analyze_only:
        analyze_layers(
            image_path=args.image_path,
            provider=args.provider,
            model=args.model,
            output_path=args.output,
        )
        return
    
    # Generate adjustment layer retouch instructions
    retouch_instructions = generate_adjustment_layer_retouch(
        image_path=args.image_path,
        instructions=args.instructions,
        provider=args.provider,
        model=args.model,
        layer_analysis_path=args.layer_analysis,
        output_path=args.output,
    )
    
    # Apply retouch instructions if requested
    if args.apply:
        apply_adjustment_layers(
            retouch_instructions=retouch_instructions,
            mcp_server_url=args.server_url,
        )

if __name__ == "__main__":
    main()