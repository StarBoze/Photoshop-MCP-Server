"""
LLM Retouch Analyzer

This module provides image analysis functionality using LLM vision models.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List, Union
import base64
import asyncio

from .models import get_model, ModelType, BaseVisionModel

# プロンプトのインポート
from .prompts.analysis import get_image_analysis_prompt

# ロガーの設定
logger = logging.getLogger(__name__)

# 分析プロンプトテンプレート
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

class ImageAnalyzer:
    """画像分析クラス"""
    
    def __init__(self, model_type: Union[ModelType, str] = ModelType.GPT4_VISION, api_key: Optional[str] = None):
        """
        画像分析クラスの初期化
        
        Args:
            model_type: 使用するモデルタイプ
            api_key: APIキー（Noneの場合は環境変数から取得）
        """
        self.model = get_model(model_type, api_key)
        logger.info(f"ImageAnalyzerを初期化しました (model_type: {model_type})")
    
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
    
    async def analyze(self, image_path: str, advanced: bool = False, custom_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        画像を分析する
        
        Args:
            image_path: 分析する画像のパス
            advanced: 詳細分析を行うかどうか
            custom_prompt: カスタム分析プロンプト
            
        Returns:
            分析結果
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"画像ファイルが見つかりません: {image_path}")
        
        # プロンプトの選択
        if custom_prompt:
            prompt = custom_prompt
        elif advanced:
            prompt = ADVANCED_ANALYSIS_PROMPT
        else:
            prompt = BASIC_ANALYSIS_PROMPT
        
        logger.info(f"画像分析を開始: {image_path}")
        
        try:
            # モデルを使用して画像を分析
            analysis = self.model.analyze_image(image_path, prompt)
            
            # 分析結果をログに記録
            logger.debug(f"分析結果: {json.dumps(analysis, indent=2, ensure_ascii=False)}")
            
            return analysis
            
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
        return await self.analyze(image_path, custom_prompt=custom_prompt)
    
    async def analyze_composition(self, image_path: str) -> Dict[str, Any]:
        """
        画像の構図を分析
        
        Args:
            image_path: 画像ファイルのパス
            
        Returns:
            構図分析結果
        """
        composition_prompt = """
        Analyze the composition of this image in detail:
        
        1. Rule of thirds adherence
        2. Leading lines and visual flow
        3. Balance and symmetry
        4. Framing and cropping
        5. Depth and perspective
        6. Negative space usage
        7. Background/foreground relationship
        8. Visual weight distribution
        9. Points of interest and focal points
        10. Overall composition effectiveness
        
        Provide a score from 1-10 for each aspect and specific recommendations for improvement.
        Return your analysis in JSON format.
        """
        
        logger.info(f"構図分析を開始: {image_path}")
        return self.model.analyze_image(image_path, composition_prompt)
    
    async def analyze_color(self, image_path: str) -> Dict[str, Any]:
        """
        画像の色調を分析
        
        Args:
            image_path: 画像ファイルのパス
            
        Returns:
            色調分析結果
        """
        color_prompt = """
        Perform a detailed color analysis of this image:
        
        1. Overall color scheme (warm, cool, neutral)
        2. Color harmony type (complementary, analogous, triadic, etc.)
        3. Color balance and white balance
        4. Color saturation and vibrance
        5. Color contrast and separation
        6. Dominant colors (provide approximate RGB values)
        7. Color grading characteristics
        8. Color psychology and emotional impact
        9. Color issues or problems
        10. Color enhancement recommendations
        
        Provide specific color values where possible and detailed recommendations.
        Return your analysis in JSON format.
        """
        
        logger.info(f"色調分析を開始: {image_path}")
        return self.model.analyze_image(image_path, color_prompt)
    
    async def analyze_subject(self, image_path: str, subject_type: str = "auto") -> Dict[str, Any]:
        """
        画像の被写体を分析
        
        Args:
            image_path: 画像ファイルのパス
            subject_type: 被写体タイプ（"portrait", "landscape", "product", "auto"）
            
        Returns:
            被写体分析結果
        """
        if subject_type == "auto":
            # 自動検出の場合は基本分析を行い、被写体タイプを判断
            basic_analysis = await self.analyze(image_path, advanced=False)
            image_type = basic_analysis.get("basic_info", {}).get("image_type", "").lower()
            
            if "portrait" in image_type or "person" in image_type:
                subject_type = "portrait"
            elif "landscape" in image_type or "nature" in image_type:
                subject_type = "landscape"
            elif "product" in image_type:
                subject_type = "product"
            else:
                subject_type = "general"
        
        # 被写体タイプに応じたプロンプト
        if subject_type == "portrait":
            prompt = """
            Perform a detailed portrait subject analysis:
            
            1. Facial features and proportions
            2. Skin tone and texture
            3. Expression and emotion
            4. Pose and body language
            5. Lighting on the subject (direction, quality, ratio)
            6. Eyes (sharpness, catchlights, expression)
            7. Hair detail and styling
            8. Clothing and accessories
            9. Subject-background relationship
            10. Portrait style and mood
            
            Provide specific retouching recommendations for portrait enhancement.
            Return your analysis in JSON format.
            """
        elif subject_type == "landscape":
            prompt = """
            Perform a detailed landscape subject analysis:
            
            1. Horizon placement and straightness
            2. Sky elements and characteristics
            3. Foreground elements and interest
            4. Middle ground elements
            5. Natural features (mountains, water, trees, etc.)
            6. Weather and atmospheric conditions
            7. Time of day and lighting conditions
            8. Seasonal indicators
            9. Scale and sense of grandeur
            10. Overall landscape mood and feeling
            
            Provide specific enhancement recommendations for landscape optimization.
            Return your analysis in JSON format.
            """
        elif subject_type == "product":
            prompt = """
            Perform a detailed product subject analysis:
            
            1. Product identification and category
            2. Product presentation and positioning
            3. Product details and features visibility
            4. Lighting setup and highlights
            5. Background choice and relevance
            6. Product color accuracy
            7. Texture and material representation
            8. Scale and size perception
            9. Product context and usage scenario
            10. Commercial appeal and marketability
            
            Provide specific recommendations for product photography enhancement.
            Return your analysis in JSON format.
            """
        else:  # general
            prompt = """
            Perform a detailed subject analysis:
            
            1. Main subject identification
            2. Subject placement and framing
            3. Subject details and clarity
            4. Subject lighting and shadows
            5. Subject color and contrast
            6. Subject-background relationship
            7. Supporting elements and context
            8. Subject emphasis techniques
            9. Subject storytelling aspects
            10. Overall subject presentation effectiveness
            
            Provide specific recommendations for subject enhancement.
            Return your analysis in JSON format.
            """
        
        logger.info(f"被写体分析を開始: {image_path} (タイプ: {subject_type})")
        return self.model.analyze_image(image_path, prompt)