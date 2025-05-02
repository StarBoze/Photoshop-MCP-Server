"""
画像分析モジュール

このモジュールは、LiteLLMを使用して画像を分析し、特徴を抽出します。
"""

import os
import base64
import logging
from typing import Dict, Any, List, Optional
import asyncio
import litellm
from litellm import completion

# プロンプトのインポート
from .prompts.analysis import get_image_analysis_prompt

# ロガーの設定
logger = logging.getLogger(__name__)

class ImageAnalyzer:
    """画像分析クラス"""
    
    def __init__(self, model: str = "gpt-4-vision-preview"):
        """
        初期化
        
        Args:
            model: 使用するLLMモデル
        """
        self.model = model
        logger.info(f"ImageAnalyzerを初期化しました (model: {model})")
    
    async def _encode_image(self, image_path: str) -> str:
        """
        画像をBase64エンコードする
        
        Args:
            image_path: 画像のパス
            
        Returns:
            Base64エンコードされた画像データ
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"画像ファイルが見つかりません: {image_path}")
        
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    async def _get_image_mime_type(self, image_path: str) -> str:
        """
        画像のMIMEタイプを取得する
        
        Args:
            image_path: 画像のパス
            
        Returns:
            MIMEタイプ
        """
        extension = os.path.splitext(image_path)[1].lower()
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.tiff': 'image/tiff',
            '.psd': 'image/vnd.adobe.photoshop'
        }
        return mime_types.get(extension, 'application/octet-stream')
    
    async def analyze(self, image_path: str) -> Dict[str, Any]:
        """
        画像を分析する
        
        Args:
            image_path: 分析する画像のパス
            
        Returns:
            分析結果
        """
        try:
            # 画像をBase64エンコード
            image_data = await self._encode_image(image_path)
            mime_type = await self._get_image_mime_type(image_path)
            
            # 分析用プロンプトを取得
            prompt = get_image_analysis_prompt()
            
            # LiteLLMを使用して画像を分析
            messages = [
                {"role": "system", "content": prompt},
                {
                    "role": "user", 
                    "content": [
                        {"type": "text", "text": "この画像を分析して、レタッチに必要な特徴を抽出してください。"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_data}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ]
            
            logger.info(f"LLMによる画像分析を開始: {image_path}")
            response = await litellm.acompletion(
                model=self.model,
                messages=messages,
                max_tokens=2000,
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            
            # レスポンスをパース
            analysis_text = response.choices[0].message.content
            
            # JSONとして解析
            import json
            analysis_result = json.loads(analysis_text)
            
            logger.info(f"画像分析完了: {len(analysis_result)} 項目の特徴を検出")
            return analysis_result
            
        except Exception as e:
            logger.error(f"画像分析エラー: {e}")
            # エラーが発生した場合は最小限の分析結果を返す
            return {
                "error": str(e),
                "basic_info": {
                    "file_path": image_path,
                    "file_name": os.path.basename(image_path)
                }
            }
    
    async def analyze_with_custom_prompt(self, image_path: str, custom_prompt: str) -> Dict[str, Any]:
        """
        カスタムプロンプトで画像を分析する
        
        Args:
            image_path: 分析する画像のパス
            custom_prompt: カスタムプロンプト
            
        Returns:
            分析結果
        """
        try:
            # 画像をBase64エンコード
            image_data = await self._encode_image(image_path)
            mime_type = await self._get_image_mime_type(image_path)
            
            # LiteLLMを使用して画像を分析
            messages = [
                {"role": "system", "content": "あなたは画像分析の専門家です。"},
                {
                    "role": "user", 
                    "content": [
                        {"type": "text", "text": custom_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_data}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ]
            
            logger.info(f"カスタムプロンプトによる画像分析を開始: {image_path}")
            response = await litellm.acompletion(
                model=self.model,
                messages=messages,
                max_tokens=2000,
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            
            # レスポンスをパース
            analysis_text = response.choices[0].message.content
            
            # JSONとして解析
            import json
            analysis_result = json.loads(analysis_text)
            
            logger.info("カスタムプロンプトによる画像分析完了")
            return analysis_result
            
        except Exception as e:
            logger.error(f"カスタムプロンプトによる画像分析エラー: {e}")
            # エラーが発生した場合は最小限の分析結果を返す
            return {
                "error": str(e),
                "basic_info": {
                    "file_path": image_path,
                    "file_name": os.path.basename(image_path)
                }
            }