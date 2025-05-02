"""
LLM Retouch Models

This module provides support for multiple LLM models for image analysis and retouch generation.
"""

import os
import json
from enum import Enum
from typing import Dict, Any, Optional, List, Union
import base64
import requests
from abc import ABC, abstractmethod
import logging

# ロガーの設定
logger = logging.getLogger(__name__)

class ModelType(Enum):
    """サポートされているLLMモデルタイプ"""
    GPT4_VISION = "gpt-4-vision"
    CLAUDE3_SONNET_VISION = "claude-3-sonnet"
    GEMINI_PRO_VISION = "gemini-pro-vision"
    CUSTOM = "custom"

class BaseVisionModel(ABC):
    """ビジョンモデルの基底クラス"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        ビジョンモデルの初期化
        
        Args:
            api_key: APIキー（Noneの場合は環境変数から取得）
        """
        self.api_key = api_key or self._get_api_key_from_env()
    
    @abstractmethod
    def _get_api_key_from_env(self) -> str:
        """環境変数からAPIキーを取得"""
        pass
    
    @abstractmethod
    def analyze_image(self, image_path: str, prompt: str) -> Dict[str, Any]:
        """
        画像を分析
        
        Args:
            image_path: 画像ファイルのパス
            prompt: 分析プロンプト
            
        Returns:
            分析結果
        """
        pass
    
    @abstractmethod
    def generate_retouch(self, image_path: str, analysis: Dict[str, Any], instructions: str) -> Dict[str, Any]:
        """
        レタッチ手順を生成
        
        Args:
            image_path: 画像ファイルのパス
            analysis: 画像分析結果
            instructions: レタッチ指示
            
        Returns:
            レタッチ手順
        """
        pass
    
    def _encode_image_base64(self, image_path: str) -> str:
        """
        画像をBase64エンコード
        
        Args:
            image_path: 画像ファイルのパス
            
        Returns:
            Base64エンコードされた画像データ
        """
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

class GPT4VisionModel(BaseVisionModel):
    """GPT-4 Visionモデル"""
    
    def _get_api_key_from_env(self) -> str:
        """環境変数からOpenAI APIキーを取得"""
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        return api_key
    
    def analyze_image(self, image_path: str, prompt: str) -> Dict[str, Any]:
        """
        GPT-4 Visionを使用して画像を分析
        
        Args:
            image_path: 画像ファイルのパス
            prompt: 分析プロンプト
            
        Returns:
            分析結果
        """
        # 画像をBase64エンコード
        base64_image = self._encode_image_base64(image_path)
        
        # APIリクエストの準備
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": "gpt-4-vision-preview",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 1000,
            "response_format": {"type": "json_object"}
        }
        
        # APIリクエストの送信
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload
        )
        
        # レスポンスの処理
        if response.status_code != 200:
            logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
            raise Exception(f"OpenAI API error: {response.status_code} - {response.text}")
        
        result = response.json()
        analysis = json.loads(result["choices"][0]["message"]["content"])
        
        return analysis
    
    def generate_retouch(self, image_path: str, analysis: Dict[str, Any], instructions: str) -> Dict[str, Any]:
        """
        GPT-4 Visionを使用してレタッチ手順を生成
        
        Args:
            image_path: 画像ファイルのパス
            analysis: 画像分析結果
            instructions: レタッチ指示
            
        Returns:
            レタッチ手順
        """
        # 画像をBase64エンコード
        base64_image = self._encode_image_base64(image_path)
        
        # APIリクエストの準備
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # 分析結果とレタッチ指示を組み合わせたプロンプト
        prompt = f"""
        Based on the following image analysis:
        {json.dumps(analysis, indent=2)}
        
        And the user instructions:
        {instructions}
        
        Generate detailed Photoshop retouch steps in JSON format.
        Include specific parameter values for each adjustment.
        """
        
        payload = {
            "model": "gpt-4-vision-preview",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 1500,
            "response_format": {"type": "json_object"}
        }
        
        # APIリクエストの送信
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload
        )
        
        # レスポンスの処理
        if response.status_code != 200:
            logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
            raise Exception(f"OpenAI API error: {response.status_code} - {response.text}")
        
        result = response.json()
        retouch_steps = json.loads(result["choices"][0]["message"]["content"])
        
        return retouch_steps

class Claude3VisionModel(BaseVisionModel):
    """Claude 3 Sonnet Visionモデル"""
    
    def _get_api_key_from_env(self) -> str:
        """環境変数からAnthropicのAPIキーを取得"""
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
        return api_key
    
    def analyze_image(self, image_path: str, prompt: str) -> Dict[str, Any]:
        """
        Claude 3 Sonnetを使用して画像を分析
        
        Args:
            image_path: 画像ファイルのパス
            prompt: 分析プロンプト
            
        Returns:
            分析結果
        """
        # 画像をBase64エンコード
        base64_image = self._encode_image_base64(image_path)
        
        # APIリクエストの準備
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
        
        payload = {
            "model": "claude-3-sonnet-20240229",
            "max_tokens": 1000,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt + "\n\nRespond in JSON format."
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
                }
            ],
            "response_format": {"type": "json_object"}
        }
        
        # APIリクエストの送信
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload
        )
        
        # レスポンスの処理
        if response.status_code != 200:
            logger.error(f"Anthropic API error: {response.status_code} - {response.text}")
            raise Exception(f"Anthropic API error: {response.status_code} - {response.text}")
        
        result = response.json()
        analysis = json.loads(result["content"][0]["text"])
        
        return analysis
    
    def generate_retouch(self, image_path: str, analysis: Dict[str, Any], instructions: str) -> Dict[str, Any]:
        """
        Claude 3 Sonnetを使用してレタッチ手順を生成
        
        Args:
            image_path: 画像ファイルのパス
            analysis: 画像分析結果
            instructions: レタッチ指示
            
        Returns:
            レタッチ手順
        """
        # 画像をBase64エンコード
        base64_image = self._encode_image_base64(image_path)
        
        # APIリクエストの準備
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
        
        # 分析結果とレタッチ指示を組み合わせたプロンプト
        prompt = f"""
        Based on the following image analysis:
        {json.dumps(analysis, indent=2)}
        
        And the user instructions:
        {instructions}
        
        Generate detailed Photoshop retouch steps in JSON format.
        Include specific parameter values for each adjustment.
        """
        
        payload = {
            "model": "claude-3-sonnet-20240229",
            "max_tokens": 1500,
            "messages": [
                {
                    "role": "user",
                    "content": [
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
                }
            ],
            "response_format": {"type": "json_object"}
        }
        
        # APIリクエストの送信
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload
        )
        
        # レスポンスの処理
        if response.status_code != 200:
            logger.error(f"Anthropic API error: {response.status_code} - {response.text}")
            raise Exception(f"Anthropic API error: {response.status_code} - {response.text}")
        
        result = response.json()
        retouch_steps = json.loads(result["content"][0]["text"])
        
        return retouch_steps

class GeminiVisionModel(BaseVisionModel):
    """Gemini Pro Visionモデル"""
    
    def _get_api_key_from_env(self) -> str:
        """環境変数からGoogle APIキーを取得"""
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is not set")
        return api_key
    
    def analyze_image(self, image_path: str, prompt: str) -> Dict[str, Any]:
        """
        Gemini Pro Visionを使用して画像を分析
        
        Args:
            image_path: 画像ファイルのパス
            prompt: 分析プロンプト
            
        Returns:
            分析結果
        """
        # 画像をBase64エンコード
        base64_image = self._encode_image_base64(image_path)
        
        # APIリクエストの準備
        headers = {
            "Content-Type": "application/json"
        }
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt + "\n\nRespond in JSON format."},
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": base64_image
                            }
                        }
                    ]
                }
            ],
            "generation_config": {
                "temperature": 0.4,
                "top_p": 1,
                "top_k": 32,
                "max_output_tokens": 1000,
                "response_mime_type": "application/json"
            }
        }
        
        # APIリクエストの送信
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro-vision:generateContent?key={self.api_key}",
            headers=headers,
            json=payload
        )
        
        # レスポンスの処理
        if response.status_code != 200:
            logger.error(f"Google API error: {response.status_code} - {response.text}")
            raise Exception(f"Google API error: {response.status_code} - {response.text}")
        
        result = response.json()
        analysis = json.loads(result["candidates"][0]["content"]["parts"][0]["text"])
        
        return analysis
    
    def generate_retouch(self, image_path: str, analysis: Dict[str, Any], instructions: str) -> Dict[str, Any]:
        """
        Gemini Pro Visionを使用してレタッチ手順を生成
        
        Args:
            image_path: 画像ファイルのパス
            analysis: 画像分析結果
            instructions: レタッチ指示
            
        Returns:
            レタッチ手順
        """
        # 画像をBase64エンコード
        base64_image = self._encode_image_base64(image_path)
        
        # APIリクエストの準備
        headers = {
            "Content-Type": "application/json"
        }
        
        # 分析結果とレタッチ指示を組み合わせたプロンプト
        prompt = f"""
        Based on the following image analysis:
        {json.dumps(analysis, indent=2)}
        
        And the user instructions:
        {instructions}
        
        Generate detailed Photoshop retouch steps in JSON format.
        Include specific parameter values for each adjustment.
        """
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": base64_image
                            }
                        }
                    ]
                }
            ],
            "generation_config": {
                "temperature": 0.4,
                "top_p": 1,
                "top_k": 32,
                "max_output_tokens": 1500,
                "response_mime_type": "application/json"
            }
        }
        
        # APIリクエストの送信
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro-vision:generateContent?key={self.api_key}",
            headers=headers,
            json=payload
        )
        
        # レスポンスの処理
        if response.status_code != 200:
            logger.error(f"Google API error: {response.status_code} - {response.text}")
            raise Exception(f"Google API error: {response.status_code} - {response.text}")
        
        result = response.json()
        retouch_steps = json.loads(result["candidates"][0]["content"]["parts"][0]["text"])
        
        return retouch_steps

def get_model(model_type: Union[ModelType, str], api_key: Optional[str] = None) -> BaseVisionModel:
    """
    指定されたタイプのモデルインスタンスを取得
    
    Args:
        model_type: モデルタイプ（ModelTypeまたは文字列）
        api_key: APIキー（Noneの場合は環境変数から取得）
        
    Returns:
        モデルインスタンス
    """
    if isinstance(model_type, str):
        try:
            model_type = ModelType(model_type)
        except ValueError:
            model_type = ModelType.GPT4_VISION  # デフォルト
    
    if model_type == ModelType.GPT4_VISION:
        return GPT4VisionModel(api_key)
    elif model_type == ModelType.CLAUDE3_SONNET_VISION:
        return Claude3VisionModel(api_key)
    elif model_type == ModelType.GEMINI_PRO_VISION:
        return GeminiVisionModel(api_key)
    else:
        raise ValueError(f"Unsupported model type: {model_type}")