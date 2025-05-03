"""
Retouch Generation Example

This script demonstrates how to use the LLM client for generating Photoshop retouch instructions.
"""

import os
import json
import argparse
import logging
from pathlib import Path

from llm_client import LLMClient
from image_analysis import analyze_image

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Retouch prompt templates
RETOUCH_PROMPT_TEMPLATE = """
Based on the following image analysis:
{analysis}

And the user instructions:
{instructions}

Generate detailed Photoshop retouch steps in JSON format with the following structure:
{{
  "retouch_steps": [
    {{
      "step": 1,
      "action": "action name",
      "parameters": {{
        "param1": "value1",
        "param2": "value2"
      }},
      "description": "detailed description of the step"
    }},
    ...
  ],
  "summary": "summary of the retouch approach"
}}

Include specific parameter values for each adjustment.
"""

# Retouch style templates
RETOUCH_STYLES = {
    "natural": "Create a natural-looking retouch that enhances the image while maintaining its authentic appearance. Focus on subtle adjustments to exposure, contrast, and color balance. For portraits, maintain natural skin texture and tones.",
    "dramatic": "Create a dramatic, high-contrast look with rich colors and deep shadows. Emphasize lighting contrast and color saturation to create a cinematic feel.",
    "vintage": "Create a vintage film look with muted colors, slight color shifts, and film grain. Add subtle vignetting and reduce contrast slightly for a nostalgic feel.",
    "black_and_white": "Convert the image to a compelling black and white version with appropriate contrast and tonal range. Focus on creating a timeless monochrome image with rich blacks and detailed highlights.",
    "high_key": "Create a bright, high-key look with lifted shadows and bright highlights. Maintain detail in highlights while creating an airy, light atmosphere.",
    "low_key": "Create a moody, low-key look with rich shadows and controlled highlights. Focus on creating dramatic lighting with deep blacks and selective highlight emphasis.",
}

def generate_retouch(
    image_path: str,
    instructions: str,
    provider: str = "openai",
    model: str = None,
    style: str = None,
    analysis_path: str = None,
    output_path: str = None,
):
    """
    Generate Photoshop retouch instructions using the LLM client.
    
    Args:
        image_path: Path to the image file
        instructions: User instructions for retouching
        provider: LLM provider to use
        model: Specific model to use (if None, default model for provider will be used)
        style: Retouch style to apply (if provided, will be added to instructions)
        analysis_path: Path to existing analysis JSON (if None, will analyze the image)
        output_path: Path to save retouch instructions (if None, print to console)
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
    
    # Get image analysis
    if analysis_path and os.path.exists(analysis_path):
        logger.info(f"Loading existing analysis from: {analysis_path}")
        with open(analysis_path, "r") as f:
            analysis = json.load(f)
    else:
        logger.info(f"Analyzing image: {image_path}")
        analysis = analyze_image(
            image_path=image_path,
            provider=provider,
            model=model,
            advanced=True,
            output_path=None,  # Don't save analysis to file
        )
    
    # Prepare instructions with style if provided
    final_instructions = instructions
    if style and style in RETOUCH_STYLES:
        final_instructions = f"{instructions}\n\nStyle: {RETOUCH_STYLES[style]}"
    
    # Prepare prompt
    prompt = RETOUCH_PROMPT_TEMPLATE.format(
        analysis=json.dumps(analysis, indent=2),
        instructions=final_instructions,
    )
    
    logger.info(f"Generating retouch instructions for: {image_path}")
    logger.info(f"Using provider: {provider}")
    
    # Generate retouch instructions
    response = client.image_analysis(
        image_path=image_path,
        prompt=prompt,
        json_response=True,
    )
    
    # Parse JSON response
    try:
        retouch_instructions = json.loads(response["content"])
    except json.JSONDecodeError:
        logger.warning("Failed to parse JSON response, returning raw content")
        retouch_instructions = {"raw_content": response["content"]}
    
    # Save or print results
    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(retouch_instructions, f, indent=2)
        logger.info(f"Retouch instructions saved to: {output_path}")
    else:
        print(json.dumps(retouch_instructions, indent=2))
    
    return retouch_instructions

def main():
    """Main function to run the script from command line."""
    parser = argparse.ArgumentParser(description="Generate Photoshop retouch instructions using LLM")
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
        "--style",
        choices=list(RETOUCH_STYLES.keys()),
        help="Retouch style to apply",
    )
    parser.add_argument(
        "--analysis",
        help="Path to existing analysis JSON (if not provided, will analyze the image)",
    )
    parser.add_argument(
        "--output",
        help="Path to save retouch instructions (if not provided, print to console)",
    )
    
    args = parser.parse_args()
    
    generate_retouch(
        image_path=args.image_path,
        instructions=args.instructions,
        provider=args.provider,
        model=args.model,
        style=args.style,
        analysis_path=args.analysis,
        output_path=args.output,
    )

if __name__ == "__main__":
    main()