"""
クロスプラットフォームのパス処理ユーティリティ

このモジュールは、異なるプラットフォーム（macOS、Windows）間でのパス処理を
統一するためのユーティリティ関数を提供します。
"""

import os
import platform
from pathlib import Path
from typing import Union

# プラットフォーム検出
PLATFORM = platform.system()

def normalize_path(path: Union[str, Path]) -> str:
    """パスを正規化する
    
    異なるプラットフォーム間でのパス表記を統一するために、
    パスを正規化します。具体的には：
    - Windowsのバックスラッシュをスラッシュに変換
    - 相対パスを絶対パスに変換
    - ユーザーホームディレクトリの展開（~の展開）
    
    Args:
        path: 正規化するパス（文字列またはPathオブジェクト）
        
    Returns:
        正規化されたパス（文字列）
    """
    # Pathオブジェクトを文字列に変換
    if isinstance(path, Path):
        path = str(path)
    
    # ユーザーホームディレクトリの展開
    if path.startswith("~"):
        path = os.path.expanduser(path)
    
    # 相対パスを絶対パスに変換
    if not os.path.isabs(path):
        path = os.path.abspath(path)
    
    # Windowsのバックスラッシュをスラッシュに変換
    if PLATFORM == "Windows":
        path = path.replace("\\", "/")
    
    return path

def format_path_for_script(path: Union[str, Path]) -> str:
    """スクリプト用にパスをフォーマットする
    
    各プラットフォームのスクリプト（AppleScript、PowerShell）で
    使用するためにパスをフォーマットします。
    
    Args:
        path: フォーマットするパス（文字列またはPathオブジェクト）
        
    Returns:
        スクリプト用にフォーマットされたパス（文字列）
    """
    # まずパスを正規化
    path = normalize_path(path)
    
    # プラットフォームに応じたフォーマット
    if PLATFORM == "Darwin":
        # AppleScript用にPOSIXパスをクォート
        return f'POSIX file "{path}"'
    elif PLATFORM == "Windows":
        # PowerShell用にパスをエスケープ
        # PowerShell用にパスをエスケープ（バックスラッシュをエスケープ）
        escaped_path = path.replace('"', '\\"')
        return f'"{escaped_path}"`'
    else:
        # その他のプラットフォームではシンプルにクォート
        return f'"{path}"'

def convert_to_platform_path(path: Union[str, Path]) -> str:
    """プラットフォーム固有のパス形式に変換する
    
    クロスプラットフォームで統一されたパス形式から、
    現在のプラットフォーム固有のパス形式に変換します。
    
    Args:
        path: 変換するパス（文字列またはPathオブジェクト）
        
    Returns:
        プラットフォーム固有のパス形式（文字列）
    """
    # まずパスを正規化
    path = normalize_path(path)
    
    # Windowsの場合はスラッシュをバックスラッシュに変換
    if PLATFORM == "Windows":
        path = path.replace("/", "\\")
    
    return path

def get_temp_dir() -> str:
    """一時ディレクトリのパスを取得する
    
    プラットフォームに応じた一時ディレクトリのパスを取得します。
    
    Returns:
        一時ディレクトリのパス（文字列）
    """
    return normalize_path(os.path.join(os.path.dirname(os.path.dirname(__file__)), "temp"))

def ensure_dir_exists(path: Union[str, Path]) -> str:
    """ディレクトリが存在することを確認し、必要に応じて作成する
    
    Args:
        path: 確認するディレクトリのパス
        
    Returns:
        正規化されたディレクトリパス
    """
    path = normalize_path(path)
    os.makedirs(path, exist_ok=True)
    return path