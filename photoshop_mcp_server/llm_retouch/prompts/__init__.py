"""
プロンプトモジュール

このモジュールは、LLM自動レタッチ機能で使用するプロンプトテンプレートを提供します。
"""

# バージョン情報
__version__ = "0.1.0"

# サブモジュールのインポート
from .analysis import get_image_analysis_prompt
from .retouch import get_retouch_command_prompt