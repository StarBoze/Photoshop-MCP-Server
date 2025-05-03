"""
LLM Client

This module provides a unified interface for interacting with various LLM providers
using litellm for abstraction.
"""

import os
import json
import base64
from typing import Dict, Any, Optional, List, Union, Literal
import logging
from pathlib import Path

import litellm
from litellm import completion

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMClient:
    """
    A unified client for interacting with various LLM providers using litellm.
    
    This class provides methods for text completion and image analysis across
    different LLM providers (OpenAI, Anthropic, Google, etc.) using litellm
    for abstraction.
    """
    
    def __init__(
        self,
        provider: Literal["openai", "anthropic", "google", "azure"] = "openai",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ):
        """
        Initialize the LLM client.
        
        Args:
            provider: The LLM provider to use
            model: The specific model to use (if None, a default model for the provider will be used)
            api_key: The API key for the provider (if None, will look for environment variables)
            api_base: The API base URL (for Azure or custom endpoints)
            max_tokens: Maximum number of tokens to generate
            temperature: Temperature for generation (0.0 to 1.0)
        """
        self.provider = provider
        self.max_tokens = max_tokens
        self.temperature = temperature
        
        # Set API key from arguments or environment variables
        if api_key:
            self.api_key = api_key
        else:
            self.api_key = self._get_api_key_from_env()
        
        # Set API base if provided
        self.api_base = api_base
        
        # Set model based on provider if not specified
        if model:
            self.model = model
        else:
            self.model = self._get_default_model()
        
        # Configure litellm
        self._configure_litellm()
        
        logger.info(f"Initialized LLM client with provider: {provider}, model: {self.model}")
    
    def _get_api_key_from_env(self) -> str:
        """Get API key from environment variables based on provider."""
        env_var_map = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GOOGLE_API_KEY",
            "azure": "AZURE_OPENAI_API_KEY",
        }
        
        env_var = env_var_map.get(self.provider)
        if not env_var:
            raise ValueError(f"Unsupported provider: {self.provider}")
        
        api_key = os.environ.get(env_var)
        if not api_key:
            raise ValueError(f"{env_var} environment variable is not set")
        
        return api_key
    
    def _get_default_model(self) -> str:
        """Get default model based on provider."""
        default_models = {
            "openai": "gpt-4-turbo",
            "anthropic": "claude-3-sonnet-20240229",
            "google": "gemini-pro",
            "azure": "gpt-4",
        }
        
        model = default_models.get(self.provider)
        if not model:
            raise ValueError(f"Unsupported provider: {self.provider}")
        
        return model
    
    def _configure_litellm(self):
        """Configure litellm based on provider and settings."""
        # Set API key
        os.environ[f"LITELLM_{self.provider.upper()}_API_KEY"] = self.api_key
        
        # Set API base if provided
        if self.api_base and self.provider == "azure":
            os.environ["AZURE_API_BASE"] = self.api_base
        
        # Additional provider-specific configurations can be added here
    
    def text_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_response: bool = False,
    ) -> Dict[str, Any]:
        """
        Generate text completion using the configured LLM.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            json_response: Whether to request JSON response format
            
        Returns:
            The completion response
        """
        messages = []
        
        # Add system prompt if provided
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Add user prompt
        messages.append({"role": "user", "content": prompt})
        
        # Prepare completion parameters
        params = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }
        
        # Add response format for JSON if requested
        if json_response:
            params["response_format"] = {"type": "json_object"}
        
        try:
            # Call litellm completion
            response = completion(**params)
            
            # Extract and return the response content
            return {
                "content": response.choices[0].message.content,
                "model": response.model,
                "usage": response.usage,
            }
        
        except Exception as e:
            logger.error(f"Error in text completion: {e}")
            raise
    
    def image_analysis(
        self,
        image_path: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_response: bool = False,
    ) -> Dict[str, Any]:
        """
        Analyze an image using the configured LLM.
        
        Args:
            image_path: Path to the image file
            prompt: The analysis prompt
            system_prompt: Optional system prompt
            json_response: Whether to request JSON response format
            
        Returns:
            The analysis response
        """
        # Verify image exists
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        # Encode image to base64
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode("utf-8")
        
        messages = []
        
        # Add system prompt if provided
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Prepare content based on provider
        if self.provider == "openai":
            content = [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}",
                        "detail": "high"
                    }
                }
            ]
            messages.append({"role": "user", "content": content})
        
        elif self.provider == "anthropic":
            content = [
                {
                    "type": "text",
                    "text": prompt
                },
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": base64_image
                    }
                }
            ]
            messages.append({"role": "user", "content": content})
        
        elif self.provider == "google":
            # For Google, we need to use a different approach with litellm
            content = [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"
                    }
                }
            ]
            messages.append({"role": "user", "content": content})
        
        else:
            raise ValueError(f"Image analysis not supported for provider: {self.provider}")
        
        # Prepare completion parameters
        params = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }
        
        # Add response format for JSON if requested
        if json_response:
            params["response_format"] = {"type": "json_object"}
        
        try:
            # Call litellm completion
            response = completion(**params)
            
            # Extract and return the response content
            return {
                "content": response.choices[0].message.content,
                "model": response.model,
                "usage": response.usage,
            }
        
        except Exception as e:
            logger.error(f"Error in image analysis: {e}")
            raise
            
    def analyze_layers(
        self,
        image_path: str,
        prompt: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze the layer structure of a PSD file using the configured LLM.
        
        Args:
            image_path: Path to the PSD file
            prompt: Custom analysis prompt (if None, a default prompt will be used)
            system_prompt: Optional system prompt
            
        Returns:
            The layer analysis response
        """
        # Verify image exists and is a PSD file
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        if not image_path.lower().endswith('.psd'):
            logger.warning(f"File {image_path} is not a PSD file, layer analysis may not be accurate")
        
        # Encode image to base64
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode("utf-8")
        
        # Default prompt for layer analysis
        if prompt is None:
            prompt = """
            Analyze this PSD file and identify its layer structure.
            Provide information about:
            
            1. The number of layers
            2. Layer names and types (regular, adjustment, smart object, text, etc.)
            3. Layer hierarchy and grouping
            4. Visibility and blend modes of layers
            5. Any adjustment layers and their settings
            
            Format your response as a structured JSON with the following schema:
            {
              "layer_count": number,
              "layers": [
                {
                  "id": number,
                  "name": "layer name",
                  "type": "layer type",
                  "visible": boolean,
                  "blend_mode": "blend mode",
                  "opacity": number,
                  "is_group": boolean,
                  "parent_group": "parent group name or null",
                  "children": [child layer ids] or null,
                  "adjustment_settings": {
                    "type": "adjustment type",
                    "settings": {
                      "param1": "value1",
                      "param2": "value2"
                    }
                  } or null
                },
                ...
              ]
            }
            """
        
        messages = []
        
        # Add system prompt if provided
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Prepare content based on provider
        if self.provider == "openai":
            content = [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}",
                        "detail": "high"
                    }
                }
            ]
            messages.append({"role": "user", "content": content})
        
        elif self.provider == "anthropic":
            content = [
                {
                    "type": "text",
                    "text": prompt
                },
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": base64_image
                    }
                }
            ]
            messages.append({"role": "user", "content": content})
        
        elif self.provider == "google":
            content = [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"
                    }
                }
            ]
            messages.append({"role": "user", "content": content})
        
        else:
            raise ValueError(f"Layer analysis not supported for provider: {self.provider}")
        
        # Prepare completion parameters
        params = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": 0.3,  # Lower temperature for more consistent analysis
            "response_format": {"type": "json_object"}
        }
        
        try:
            # Call litellm completion
            response = completion(**params)
            
            # Extract and parse the response content
            content = response.choices[0].message.content
            try:
                layer_analysis = json.loads(content)
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON response, returning raw content")
                layer_analysis = {"raw_content": content}
            
            return {
                "content": layer_analysis,
                "model": response.model,
                "usage": response.usage,
            }
        
        except Exception as e:
            logger.error(f"Error in layer analysis: {e}")
            raise

    def generate_adjustment_layer_retouch(
        self,
        image_path: str,
        instructions: str,
        layer_analysis: Optional[Dict[str, Any]] = None,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate non-destructive retouch instructions using adjustment layers.
        
        Args:
            image_path: Path to the image file
            instructions: User instructions for retouching
            layer_analysis: Optional layer analysis result (if None, will analyze the image)
            system_prompt: Optional system prompt
            
        Returns:
            The adjustment layer retouch instructions
        """
        # Verify image exists
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        # Encode image to base64
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode("utf-8")
        
        # Get layer analysis if not provided
        if layer_analysis is None and image_path.lower().endswith('.psd'):
            logger.info(f"Analyzing layers of: {image_path}")
            layer_analysis_response = self.analyze_layers(image_path)
            layer_analysis = layer_analysis_response["content"]
        
        # Prepare prompt for adjustment layer retouch
        prompt = f"""
        Based on the following user instructions:
        {instructions}
        
        Generate non-destructive retouch instructions using Photoshop adjustment layers.
        
        For each adjustment needed, specify:
        1. The type of adjustment layer (Levels, Curves, Hue/Saturation, etc.)
        2. The specific settings for the adjustment
        3. The blend mode (if different from Normal)
        4. The opacity (if different from 100%)
        5. Any layer mask needed
        
        Format your response as a structured JSON with the following schema:
        {{
          "retouch_steps": [
            {{
              "step": 1,
              "action": "create_adjustment_layer",
              "parameters": {{
                "type": "adjustment layer type",
                "name": "descriptive name",
                "settings": {{
                  "param1": "value1",
                  "param2": "value2"
                }},
                "blend_mode": "blend mode",
                "opacity": number,
                "mask": {{
                  "type": "mask type",
                  "settings": {{
                    "param1": "value1"
                  }}
                }} or null
              }},
              "description": "detailed description of the step"
            }},
            ...
          ],
          "summary": "summary of the retouch approach"
        }}
        """
        
        # Add layer analysis information if available
        if layer_analysis:
            prompt += f"\n\nExisting layer structure:\n{json.dumps(layer_analysis, indent=2)}"
        
        messages = []
        
        # Add system prompt if provided
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Prepare content based on provider
        if self.provider == "openai":
            content = [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}",
                        "detail": "high"
                    }
                }
            ]
            messages.append({"role": "user", "content": content})
        
        elif self.provider == "anthropic":
            content = [
                {
                    "type": "text",
                    "text": prompt
                },
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": base64_image
                    }
                }
            ]
            messages.append({"role": "user", "content": content})
        
        elif self.provider == "google":
            content = [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"
                    }
                }
            ]
            messages.append({"role": "user", "content": content})
        
        else:
            raise ValueError(f"Adjustment layer retouch not supported for provider: {self.provider}")
        
        # Prepare completion parameters
        params = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": 0.7,  # Higher temperature for more creative retouch suggestions
            "response_format": {"type": "json_object"}
        }
        
        try:
            # Call litellm completion
            response = completion(**params)
            
            # Extract and parse the response content
            content = response.choices[0].message.content
            try:
                retouch_instructions = json.loads(content)
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON response, returning raw content")
                retouch_instructions = {"raw_content": content}
            
            return {
                "content": retouch_instructions,
                "model": response.model,
                "usage": response.usage,
            }
        
        except Exception as e:
            logger.error(f"Error in adjustment layer retouch generation: {e}")
            raise