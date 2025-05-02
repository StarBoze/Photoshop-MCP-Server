"""
LLM自動レタッチモジュール

このモジュールは、LiteLLMを使用してLLMと統合し、画像分析と自動レタッチを行います。
"""

from typing import Dict, Any, List, Optional
import logging

# ロガーの設定
logger = logging.getLogger(__name__)

# バージョン情報
__version__ = "0.1.0"

# サブモジュールのインポート
from .analyzer import ImageAnalyzer
from .generator import RetouchCommandGenerator
from .executor import RetouchCommandExecutor

class LLMRetouchManager:
    """LLM自動レタッチ機能の管理クラス"""
    
    def __init__(self, bridge_mode: str = "applescript"):
        """
        初期化
        
        Args:
            bridge_mode: 使用するブリッジモード
        """
        self.bridge_mode = bridge_mode
        self.analyzer = ImageAnalyzer()
        self.generator = RetouchCommandGenerator()
        self.executor = RetouchCommandExecutor(bridge_mode=bridge_mode)
        logger.info("LLMRetouchManagerを初期化しました")
    
    async def analyze_image(self, image_path: str) -> Dict[str, Any]:
        """
        画像を分析する
        
        Args:
            image_path: 分析する画像のパス
            
        Returns:
            分析結果
        """
        logger.info(f"画像分析開始: {image_path}")
        analysis_result = await self.analyzer.analyze(image_path)
        logger.info(f"画像分析完了: {len(analysis_result)} 項目の特徴を検出")
        return analysis_result
    
    async def generate_retouch_commands(self, analysis_result: Dict[str, Any], instructions: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        レタッチコマンドを生成する
        
        Args:
            analysis_result: 画像分析結果
            instructions: レタッチの指示（オプション）
            
        Returns:
            レタッチコマンドのリスト
        """
        logger.info("レタッチコマンド生成開始")
        commands = await self.generator.generate(analysis_result, instructions)
        logger.info(f"レタッチコマンド生成完了: {len(commands)} コマンド")
        return commands
    
    async def execute_retouch_commands(self, commands: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        レタッチコマンドを実行する
        
        Args:
            commands: レタッチコマンドのリスト
            
        Returns:
            実行結果のリスト
        """
        logger.info(f"レタッチコマンド実行開始: {len(commands)} コマンド")
        results = await self.executor.execute(commands)
        logger.info("レタッチコマンド実行完了")
        return results
    
    async def auto_retouch(self, image_path: str, instructions: Optional[str] = None) -> Dict[str, Any]:
        """
        画像を自動レタッチする
        
        Args:
            image_path: レタッチする画像のパス
            instructions: レタッチの指示（オプション）
            
        Returns:
            レタッチ結果
        """
        logger.info(f"自動レタッチ開始: {image_path}")
        
        # 画像分析
        analysis_result = await self.analyze_image(image_path)
        
        # レタッチコマンド生成
        commands = await self.generate_retouch_commands(analysis_result, instructions)
        
        # レタッチコマンド実行
        execution_results = await self.execute_retouch_commands(commands)
        
        # 結果を返す
        result = {
            "status": "success",
            "analysis": analysis_result,
            "retouch_actions": execution_results,
            "output_path": None  # 保存された場合はここにパスが入る
        }
        
        logger.info("自動レタッチ完了")
        return result