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