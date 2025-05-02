"""
LLM Retouch Generator

This module generates Photoshop retouch instructions based on image analysis.
"""

import os
import logging
from typing import Dict, Any, List, Optional, Union
import json
import asyncio

from .models import get_model, ModelType, BaseVisionModel

# プロンプトのインポート
from .prompts.retouch import get_retouch_command_prompt

# ロガーの設定
logger = logging.getLogger(__name__)

# レタッチプロンプトテンプレート
BASIC_RETOUCH_PROMPT = """
Based on the provided image analysis, generate Photoshop retouch commands to improve the image.
Focus on the most important adjustments that will have the biggest impact.

Your response should be a JSON object with a "commands" array containing retouch steps.
Each command should have:
1. "type": The type of adjustment (e.g., "exposure", "contrast", "curves", etc.)
2. "params": Parameters for the adjustment
3. "purpose": Brief explanation of why this adjustment is needed
4. "order": The sequence number for this adjustment

Example format:
{
  "commands": [
    {
      "type": "exposure",
      "params": {
        "value": 0.5
      },
      "purpose": "Brighten the underexposed image",
      "order": 1
    },
    {
      "type": "curves",
      "params": {
        "channel": "rgb",
        "points": [[0, 0], [64, 60], [192, 200], [255, 255]]
      },
      "purpose": "Increase contrast and enhance midtones",
      "order": 2
    }
  ]
}
"""

ADVANCED_RETOUCH_PROMPT = """
Based on the provided image analysis, generate comprehensive Photoshop retouch commands to transform the image.
Create a professional-grade editing workflow that addresses all technical and aesthetic aspects.

Your response should be a JSON object with a "commands" array containing detailed retouch steps.
Each command should have:
1. "type": The specific adjustment type
2. "params": Detailed parameters with exact values
3. "purpose": Detailed explanation of the adjustment's purpose
4. "order": The sequence number
5. "layer_name": Suggested name for the adjustment layer
6. "blend_mode": Blend mode if applicable (e.g., "normal", "overlay", "soft light")
7. "opacity": Layer opacity percentage if not 100%
8. "mask": Boolean indicating if a mask should be used
9. "mask_instructions": Instructions for mask creation if applicable

Group the commands into logical sections:
1. Base corrections (exposure, white balance)
2. Tonal adjustments (contrast, curves, levels)
3. Color adjustments (saturation, color balance, selective color)
4. Local adjustments (dodge/burn, local contrast)
5. Creative effects (color grading, special effects)
6. Finishing touches (sharpening, noise reduction)

Example format:
{
  "commands": [
    {
      "type": "exposure",
      "params": {
        "value": 0.5,
        "offset": -0.1,
        "gamma": 1.05
      },
      "purpose": "Correct the 1-stop underexposure while preserving highlight detail",
      "order": 1,
      "layer_name": "Exposure Correction",
      "blend_mode": "normal",
      "opacity": 100,
      "mask": false
    },
    {
      "type": "curves",
      "params": {
        "channel": "rgb",
        "points": [[0, 0], [64, 60], [192, 200], [255, 255]],
        "output_black": 5,
        "output_white": 250
      },
      "purpose": "Enhance contrast while protecting shadow and highlight detail",
      "order": 3,
      "layer_name": "Contrast Enhancement",
      "blend_mode": "luminosity",
      "opacity": 85,
      "mask": true,
      "mask_instructions": "Mask out the already well-contrasted sky region"
    }
  ]
}
"""

# レタッチスタイルテンプレート
RETOUCH_STYLE_TEMPLATES = {
    "natural": """
    Create a natural-looking retouch that enhances the image while maintaining its authentic feel.
    Focus on subtle adjustments that correct technical issues without making the image look artificially processed.
    Preserve natural skin tones, realistic colors, and authentic textures.
    Aim for a result that looks like the best possible version of the original scene.
    """,
    
    "dramatic": """
    Create a dramatic, high-impact retouch that transforms the image with bold adjustments.
    Emphasize contrast, clarity, and color impact to create a striking visual impression.
    Consider techniques like:
    - High contrast with deep shadows and bright highlights
    - Clarity and texture enhancement
    - Vibrant or stylized color grading
    - Vignetting to focus attention
    - Dramatic sky enhancement for landscapes
    - Bold contouring for portraits
    """,
    
    "vintage": """
    Create a vintage-style retouch that gives the image a classic, timeless quality.
    Emulate the characteristics of film photography and traditional darkroom techniques.
    Consider techniques like:
    - Subtle color fading or muting
    - Split toning with warm highlights and cool shadows
    - Grain addition
    - Vignette effects
    - Slightly reduced contrast in shadows
    - Color palette shifting toward sepia, cyan-red, or other classic film looks
    """,
    
    "black_and_white": """
    Create a compelling black and white conversion that emphasizes form, texture, and tonal relationships.
    Focus on creating a rich tonal range with detailed shadows and highlights.
    Consider techniques like:
    - Channel mixer adjustments for optimal tonal separation
    - Dodging and burning to enhance dimensional qualities
    - Contrast adjustments that suit the subject matter
    - Clarity and texture enhancement where appropriate
    - Subtle toning (selenium, sepia, etc.) if it enhances the image
    """,
    
    "high_key": """
    Create a high-key retouch with bright, airy qualities and minimal shadows.
    Focus on creating a light, ethereal mood with delicate tonal transitions.
    Consider techniques like:
    - Exposure and brightness increases
    - Shadow lifting
    - Contrast reduction
    - Subtle color desaturation or pastel color palette
    - Highlight enhancement
    - Soft glow effects
    """,
    
    "low_key": """
    Create a low-key retouch with dramatic shadows and selective highlighting.
    Focus on creating a moody, atmospheric image with rich blacks and carefully placed highlights.
    Consider techniques like:
    - Shadow deepening
    - Controlled highlight placement
    - Increased contrast
    - Subdued color palette or selective color emphasis
    - Vignetting to enhance the dark mood
    """,
    
    "commercial": """
    Create a commercial-grade retouch suitable for advertising or marketing purposes.
    Focus on creating a polished, perfect look with immaculate details and vibrant presentation.
    Consider techniques like:
    - Perfect exposure and color balance
    - Skin retouching for portraits (while maintaining texture)
    - Product enhancement for commercial products
    - Color vibrancy and separation
    - Crisp details and clarity
    - Clean backgrounds with proper separation from subjects
    """,
    
    "cinematic": """
    Create a cinematic retouch inspired by movie color grading techniques.
    Focus on creating a filmic look with controlled color relationships and atmospheric qualities.
    Consider techniques like:
    - Letterbox crop (2.35:1 or similar aspect ratio)
    - Complementary color grading (orange-teal, etc.)
    - Contrast adjustments with lifted blacks
    - Subtle halation or bloom on highlights
    - Controlled color palette with emphasis on production design colors
    - Atmospheric effects (haze, volumetric lighting)
    """
}

class RetouchCommandGenerator:
    """レタッチコマンド生成クラス"""
    
    def __init__(self, model_type: Union[ModelType, str] = ModelType.GPT4_VISION, api_key: Optional[str] = None):
        """
        初期化
        
        Args:
            model_type: 使用するモデルタイプ
            api_key: APIキー（Noneの場合は環境変数から取得）
        """
        self.model = get_model(model_type, api_key)
        logger.info(f"RetouchCommandGeneratorを初期化しました (model_type: {model_type})")
    
    async def generate(self, 
                      image_path: str,
                      analysis_result: Dict[str, Any], 
                      instructions: Optional[str] = None,
                      advanced: bool = False,
                      style: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        レタッチコマンドを生成する
        
        Args:
            image_path: 画像ファイルのパス
            analysis_result: 画像分析結果
            instructions: レタッチの指示（オプション）
            advanced: 詳細なレタッチコマンドを生成するかどうか
            style: レタッチスタイル（"natural", "dramatic", "vintage", etc.）
            
        Returns:
            レタッチコマンドのリスト
        """
        try:
            # レタッチコマンド生成用プロンプトを取得
            base_prompt = ADVANCED_RETOUCH_PROMPT if advanced else BASIC_RETOUCH_PROMPT
            
            # スタイルテンプレートの適用
            style_prompt = ""
            if style and style in RETOUCH_STYLE_TEMPLATES:
                style_prompt = f"\nStyle Instructions: {RETOUCH_STYLE_TEMPLATES[style]}"
            
            # 分析結果をJSON文字列に変換
            analysis_json = json.dumps(analysis_result, ensure_ascii=False, indent=2)
            
            # ユーザー指示の処理
            user_instructions = "特に指示はありません。画像分析結果に基づいて最適なレタッチを行ってください。"
            if instructions:
                user_instructions = instructions
            
            # 最終プロンプトの構築
            prompt = f"""
            {base_prompt}
            
            {style_prompt}
            
            画像分析結果:
            ```json
            {analysis_json}
            ```
            
            ユーザー指示:
            {user_instructions}
            
            上記の情報に基づいて、Photoshopで実行可能なレタッチコマンドを生成してください。
            """
            
            logger.info("レタッチコマンド生成を開始")
            
            # モデルを使用してレタッチコマンドを生成
            commands_data = self.model.generate_retouch(image_path, analysis_result, prompt)
            
            # コマンドリストを取得
            if "commands" in commands_data:
                commands = commands_data["commands"]
            else:
                commands = commands_data.get("retouch_commands", [])
                if not commands:
                    # フォールバック: トップレベルのリストを使用
                    commands = list(commands_data.values()) if isinstance(commands_data, dict) else []
            
            # コマンドの検証
            validated_commands = []
            for cmd in commands:
                if isinstance(cmd, dict) and "type" in cmd and "params" in cmd:
                    validated_commands.append(cmd)
                else:
                    logger.warning(f"無効なコマンド形式をスキップ: {cmd}")
            
            logger.info(f"レタッチコマンド生成完了: {len(validated_commands)} コマンド")
            return validated_commands
            
        except Exception as e:
            logger.error(f"レタッチコマンド生成エラー: {e}")
            # エラーが発生した場合は空のリストを返す
            return []
    
    async def generate_with_custom_prompt(self, 
                                         image_path: str,
                                         analysis_result: Dict[str, Any], 
                                         custom_prompt: str) -> List[Dict[str, Any]]:
        """
        カスタムプロンプトでレタッチコマンドを生成する
        
        Args:
            image_path: 画像ファイルのパス
            analysis_result: 画像分析結果
            custom_prompt: カスタムプロンプト
            
        Returns:
            レタッチコマンドのリスト
        """
        try:
            # 分析結果をJSON文字列に変換
            analysis_json = json.dumps(analysis_result, ensure_ascii=False, indent=2)
            
            # 最終プロンプトの構築
            prompt = f"""
            画像分析結果:
            ```json
            {analysis_json}
            ```
            
            {custom_prompt}
            
            上記の情報に基づいて、Photoshopで実行可能なレタッチコマンドをJSON形式で生成してください。
            """
            
            logger.info("カスタムプロンプトによるレタッチコマンド生成を開始")
            
            # モデルを使用してレタッチコマンドを生成
            commands_data = self.model.generate_retouch(image_path, analysis_result, prompt)
            
            # コマンドリストを取得
            if "commands" in commands_data:
                commands = commands_data["commands"]
            else:
                commands = commands_data.get("retouch_commands", [])
                if not commands:
                    # フォールバック: トップレベルのリストを使用
                    commands = list(commands_data.values()) if isinstance(commands_data, dict) else []
            
            # コマンドの検証
            validated_commands = []
            for cmd in commands:
                if isinstance(cmd, dict) and "type" in cmd and "params" in cmd:
                    validated_commands.append(cmd)
                else:
                    logger.warning(f"無効なコマンド形式をスキップ: {cmd}")
            
            logger.info(f"カスタムプロンプトによるレタッチコマンド生成完了: {len(validated_commands)} コマンド")
            return validated_commands
            
        except Exception as e:
            logger.error(f"カスタムプロンプトによるレタッチコマンド生成エラー: {e}")
            # エラーが発生した場合は空のリストを返す
            return []
    
    async def generate_style_based(self,
                                  image_path: str,
                                  analysis_result: Dict[str, Any],
                                  style: str,
                                  instructions: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        特定のスタイルに基づいてレタッチコマンドを生成する
        
        Args:
            image_path: 画像ファイルのパス
            analysis_result: 画像分析結果
            style: レタッチスタイル（"natural", "dramatic", "vintage", etc.）
            instructions: 追加のレタッチ指示（オプション）
            
        Returns:
            レタッチコマンドのリスト
        """
        return await self.generate(
            image_path=image_path,
            analysis_result=analysis_result,
            instructions=instructions,
            advanced=True,
            style=style
        )
    
    async def generate_portrait_retouch(self,
                                       image_path: str,
                                       analysis_result: Dict[str, Any],
                                       beauty_level: int = 3,
                                       preserve_identity: bool = True) -> List[Dict[str, Any]]:
        """
        ポートレート用のレタッチコマンドを生成する
        
        Args:
            image_path: 画像ファイルのパス
            analysis_result: 画像分析結果
            beauty_level: 美肌レタッチのレベル（1-5、1=最小限、5=最大限）
            preserve_identity: 人物の特徴を保持するかどうか
            
        Returns:
            レタッチコマンドのリスト
        """
        # ポートレートレタッチ用のカスタムプロンプト
        portrait_prompt = f"""
        この画像のポートレートレタッチを行ってください。
        
        美肌レタッチレベル: {beauty_level}/5（1=最小限、5=最大限）
        個性の保持: {"必須" if preserve_identity else "任意"}
        
        以下の要素に注目してレタッチしてください：
        1. 肌の質感改善（しわ、毛穴、にきびなどの軽減）
        2. 肌のトーン均一化
        3. 目の明るさと鮮明さの強調
        4. 髪の毛の質感と色の改善
        5. 顔の輪郭の微調整（必要な場合）
        6. 全体的な照明とコントラストの最適化
        7. 背景の改善または調整
        
        各調整について、具体的なPhotoshopコマンドとパラメータを提供してください。
        美肌レタッチは自然な仕上がりを心がけ、過度な処理は避けてください。
        """
        
        return await self.generate_with_custom_prompt(
            image_path=image_path,
            analysis_result=analysis_result,
            custom_prompt=portrait_prompt
        )
    
    async def generate_landscape_retouch(self,
                                        image_path: str,
                                        analysis_result: Dict[str, Any],
                                        enhance_sky: bool = True,
                                        enhance_foreground: bool = True,
                                        style: str = "natural") -> List[Dict[str, Any]]:
        """
        風景写真用のレタッチコマンドを生成する
        
        Args:
            image_path: 画像ファイルのパス
            analysis_result: 画像分析結果
            enhance_sky: 空の強調を行うかどうか
            enhance_foreground: 前景の強調を行うかどうか
            style: レタッチスタイル
            
        Returns:
            レタッチコマンドのリスト
        """
        # 風景レタッチ用のカスタムプロンプト
        landscape_prompt = f"""
        この風景写真のレタッチを行ってください。
        
        スタイル: {style}
        空の強調: {"あり" if enhance_sky else "なし"}
        前景の強調: {"あり" if enhance_foreground else "なし"}
        
        以下の要素に注目してレタッチしてください：
        1. 全体的な露出とコントラストの最適化
        2. 色彩の強調と調整
        3. 空の処理（色、コントラスト、雲の詳細）
        4. 前景の処理（ディテール、コントラスト、色彩）
        5. 中間領域の処理
        6. 霞や大気遠近法の調整
        7. 全体的な色調の統一
        
        各調整について、具体的なPhotoshopコマンドとパラメータを提供してください。
        """
        
        return await self.generate_with_custom_prompt(
            image_path=image_path,
            analysis_result=analysis_result,
            custom_prompt=landscape_prompt
        )
    
    async def generate_product_retouch(self,
                                      image_path: str,
                                      analysis_result: Dict[str, Any],
                                      clean_background: bool = True,
                                      enhance_details: bool = True) -> List[Dict[str, Any]]:
        """
        商品写真用のレタッチコマンドを生成する
        
        Args:
            image_path: 画像ファイルのパス
            analysis_result: 画像分析結果
            clean_background: 背景のクリーンアップを行うかどうか
            enhance_details: 商品詳細の強調を行うかどうか
            
        Returns:
            レタッチコマンドのリスト
        """
        # 商品レタッチ用のカスタムプロンプト
        product_prompt = f"""
        この商品写真のレタッチを行ってください。
        
        背景のクリーンアップ: {"あり" if clean_background else "なし"}
        商品詳細の強調: {"あり" if enhance_details else "なし"}
        
        以下の要素に注目してレタッチしてください：
        1. 商品の色彩と質感の正確な表現
        2. 商品のディテールと鮮明さの強調
        3. 適切な露出とコントラストの調整
        4. 背景の処理（クリーンアップ、単色化、または適切な調整）
        5. 商品のハイライトと影の最適化
        6. 商品の輪郭の明確化
        7. 全体的な商品の魅力向上
        
        各調整について、具体的なPhotoshopコマンドとパラメータを提供してください。
        商品の実際の色や質感を正確に表現することを優先してください。
        """
        
        return await self.generate_with_custom_prompt(
            image_path=image_path,
            analysis_result=analysis_result,
            custom_prompt=product_prompt
        )