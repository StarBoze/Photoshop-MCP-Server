"""
レタッチコマンド生成モジュール

このモジュールは、LiteLLMを使用して、画像分析結果に基づいてレタッチコマンドを生成します。
"""

import logging
from typing import Dict, Any, List, Optional
import json
import litellm

# プロンプトのインポート
from .prompts.retouch import get_retouch_command_prompt

# ロガーの設定
logger = logging.getLogger(__name__)

class RetouchCommandGenerator:
    """レタッチコマンド生成クラス"""
    
    def __init__(self, model: str = "gpt-4-turbo"):
        """
        初期化
        
        Args:
            model: 使用するLLMモデル
        """
        self.model = model
        logger.info(f"RetouchCommandGeneratorを初期化しました (model: {model})")
    
    async def generate(self, analysis_result: Dict[str, Any], instructions: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        レタッチコマンドを生成する
        
        Args:
            analysis_result: 画像分析結果
            instructions: レタッチの指示（オプション）
            
        Returns:
            レタッチコマンドのリスト
        """
        try:
            # レタッチコマンド生成用プロンプトを取得
            prompt = get_retouch_command_prompt()
            
            # 分析結果とユーザー指示をJSON文字列に変換
            analysis_json = json.dumps(analysis_result, ensure_ascii=False, indent=2)
            
            # ユーザー指示の処理
            user_instructions = "特に指示はありません。画像分析結果に基づいて最適なレタッチを行ってください。"
            if instructions:
                user_instructions = instructions
            
            # LiteLLMを使用してレタッチコマンドを生成
            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"""
画像分析結果:
```json
{analysis_json}
```

ユーザー指示:
{user_instructions}

上記の情報に基づいて、Photoshopで実行可能なレタッチコマンドを生成してください。
"""}
            ]
            
            logger.info("LLMによるレタッチコマンド生成を開始")
            response = await litellm.acompletion(
                model=self.model,
                messages=messages,
                max_tokens=2000,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            # レスポンスをパース
            commands_text = response.choices[0].message.content
            
            # JSONとして解析
            commands_data = json.loads(commands_text)
            
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
    
    async def generate_with_custom_prompt(self, analysis_result: Dict[str, Any], custom_prompt: str) -> List[Dict[str, Any]]:
        """
        カスタムプロンプトでレタッチコマンドを生成する
        
        Args:
            analysis_result: 画像分析結果
            custom_prompt: カスタムプロンプト
            
        Returns:
            レタッチコマンドのリスト
        """
        try:
            # 分析結果をJSON文字列に変換
            analysis_json = json.dumps(analysis_result, ensure_ascii=False, indent=2)
            
            # LiteLLMを使用してレタッチコマンドを生成
            messages = [
                {"role": "system", "content": "あなたはPhotoshopレタッチの専門家です。"},
                {"role": "user", "content": f"""
画像分析結果:
```json
{analysis_json}
```

{custom_prompt}
"""}
            ]
            
            logger.info("カスタムプロンプトによるレタッチコマンド生成を開始")
            response = await litellm.acompletion(
                model=self.model,
                messages=messages,
                max_tokens=2000,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            # レスポンスをパース
            commands_text = response.choices[0].message.content
            
            # JSONとして解析
            commands_data = json.loads(commands_text)
            
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