"""
Image Analysis Example

This script demonstrates how to use the LLM client for image analysis.
"""

import os
import json
import argparse
import logging
from pathlib import Path

from llm_client import LLMClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Analysis prompt templates
BASIC_ANALYSIS_PROMPT = """
Analyze this image in detail and provide information about:

1. Basic Information:
   - Image type (portrait, landscape, product, etc.)
   - Main subject
   - Overall impression

2. Technical Characteristics:
   - Brightness (too dark, too bright, balanced)
   - Contrast (too low, too high, balanced)
   - Color balance (color cast, white balance issues)
   - Sharpness (blurry, sharp, over-sharpened)
   - Noise level (clean, noisy)

3. Composition:
   - Rule of thirds adherence
   - Leading lines
   - Balance and symmetry
   - Framing issues

4. Subject Analysis:
   - For portraits: skin tone, facial features, expression
   - For landscapes: horizon, sky, foreground elements
   - For products: product presentation, background, lighting

5. Potential Improvements:
   - Specific areas that need adjustment
   - Suggested enhancements

Provide your analysis in a structured JSON format.
"""

ADVANCED_ANALYSIS_PROMPT = """
Perform a comprehensive analysis of this image, focusing on both technical aspects and artistic elements:

1. Basic Information:
   - Image type and genre
   - Main subject and secondary elements
   - Overall mood and impression
   - Estimated purpose of the image

2. Technical Assessment:
   - Exposure (provide EV value estimate if possible)
   - Dynamic range (highlight and shadow detail)
   - Color accuracy and saturation
   - White balance (color temperature in Kelvin if possible)
   - Sharpness and focus precision
   - Noise characteristics (luminance/color noise)
   - Lens characteristics (distortion, vignetting, chromatic aberration)
   - Resolution and detail retention

3. Composition Analysis:
   - Rule of thirds and golden ratio adherence
   - Leading lines and visual flow
   - Balance, symmetry, and weight distribution
   - Framing and cropping effectiveness
   - Depth and perspective
   - Negative space usage
   - Background/foreground relationship

4. Color Theory Assessment:
   - Color harmony and scheme (complementary, analogous, etc.)
   - Color psychology and emotional impact
   - Color contrast and separation
   - Color grading characteristics

5. Subject-Specific Analysis:
   - For portraits: skin tone accuracy, facial lighting, expression, pose
   - For landscapes: atmospheric conditions, time of day, seasonal elements
   - For products: product presentation, lighting setup, background choice
   - For architecture: perspective, structural elements, spatial representation

6. Detailed Improvement Recommendations:
   - Exposure and tonal adjustments
   - Color correction and grading
   - Retouching requirements
   - Composition refinements
   - Special effects or creative enhancements

Provide your analysis in a detailed, structured JSON format with numerical values where applicable.
"""

def analyze_image(
    image_path: str,
    provider: str = "openai",
    model: str = None,
    advanced: bool = False,
    output_path: str = None,
):
    """
    Analyze an image using the LLM client.
    
    Args:
        image_path: Path to the image file
        provider: LLM provider to use
        model: Specific model to use (if None, default model for provider will be used)
        advanced: Whether to use advanced analysis prompt
        output_path: Path to save analysis results (if None, print to console)
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
    
    # Select prompt based on analysis type
    prompt = ADVANCED_ANALYSIS_PROMPT if advanced else BASIC_ANALYSIS_PROMPT
    
    logger.info(f"Analyzing image: {image_path}")
    logger.info(f"Using provider: {provider}")
    
    # Perform image analysis
    response = client.image_analysis(
        image_path=image_path,
        prompt=prompt,
        json_response=True,
    )
    
    # Parse JSON response
    try:
        analysis = json.loads(response["content"])
    except json.JSONDecodeError:
        logger.warning("Failed to parse JSON response, returning raw content")
        analysis = {"raw_content": response["content"]}
    
    # Save or print results
    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(analysis, f, indent=2)
        logger.info(f"Analysis saved to: {output_path}")
    else:
        print(json.dumps(analysis, indent=2))
    
    return analysis

def main():
    """Main function to run the script from command line."""
    parser = argparse.ArgumentParser(description="Analyze an image using LLM")
    parser.add_argument("image_path", help="Path to the image file")
    parser.add_argument(
        "--provider",
        choices=["openai", "anthropic", "google"],
        default="openai",
        help="LLM provider to use",
    )
    parser.add_argument("--model", help="Specific model to use")
    parser.add_argument(
        "--advanced",
        action="store_true",
        help="Use advanced analysis prompt",
    )
    parser.add_argument(
        "--output",
        help="Path to save analysis results (if not provided, print to console)",
    )
    
    args = parser.parse_args()
    
    analyze_image(
        image_path=args.image_path,
        provider=args.provider,
        model=args.model,
        advanced=args.advanced,
        output_path=args.output,
    )

if __name__ == "__main__":
    main()