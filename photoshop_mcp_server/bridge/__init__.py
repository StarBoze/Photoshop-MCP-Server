import platform
import logging
from typing import Dict, Type, Any, List

# プラットフォーム検出
PLATFORM = platform.system()

# ロガーの設定
logger = logging.getLogger('photoshop_mcp_server.bridge')
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# 抽象基底クラス
class PhotoshopBridge:
    """Photoshopとの通信を行うブリッジの基底クラス"""
    
    async def open_file(self, path: str) -> bool:
        """ファイルを開く"""
        raise NotImplementedError()
    
    async def close_file(self, save_changes: bool = False) -> bool:
        """ファイルを閉じる
        
        Args:
            save_changes: 変更を保存するかどうか
            
        Returns:
            成功したかどうか
        """
        raise NotImplementedError()
    
    async def save_file(self, path: str = None) -> bool:
        """ファイルを保存する
        
        Args:
            path: 保存先のパス。Noneの場合は現在のパスに保存
            
        Returns:
            成功したかどうか
        """
        raise NotImplementedError()
    
    async def export_layer(self, layer_name: str, export_path: str, format: str = "PNG") -> bool:
        """レイヤーをエクスポートする
        
        Args:
            layer_name: エクスポートするレイヤー名
            export_path: エクスポート先のパス
            format: エクスポート形式（PNG, JPEG, PSD等）
            
        Returns:
            成功したかどうか
        """
        raise NotImplementedError()
    
    async def run_action(self, action_set: str, action_name: str) -> bool:
        """アクションを実行する
        
        Args:
            action_set: アクションセット名
            action_name: アクション名
            
        Returns:
            成功したかどうか
        """
        raise NotImplementedError()
    
    async def execute_script(self, script: str) -> Any:
        """JavaScriptを実行する"""
        raise NotImplementedError()
    
    async def get_document_info(self) -> Dict[str, Any]:
        """現在のドキュメント情報を取得する"""
        raise NotImplementedError()
    
    async def generate_thumbnail(self, path: str, width: int = 256, height: int = 256, format: str = "jpeg", quality: int = 80) -> dict:
        """サムネイルを生成する
        
        Args:
            path: サムネイルを生成するファイルのパス
            width: サムネイルの幅
            height: サムネイルの高さ
            format: 出力形式（jpeg, png）
            quality: 画質（0-100）
            
        Returns:
            サムネイル情報（status, thumbnail, width, height, format）
        """
        raise NotImplementedError()
        
    async def generate_thumbnail_stream(self, path: str, width: int = 256, height: int = 256, format: str = "jpeg", quality: int = 80, callback=None) -> dict:
        """サムネイルを生成し、進捗状況をコールバックで通知する
        
        Args:
            path: サムネイルを生成するファイルのパス
            width: サムネイルの幅
            height: サムネイルの高さ
            format: 出力形式（jpeg, png）
            quality: 画質（0-100）
            callback: 進捗状況を通知するコールバック関数
            
        Returns:
            サムネイル情報（status, thumbnail, width, height, format）
        """
        raise NotImplementedError()

# UXPバックエンドは常にインポート（プラットフォーム非依存）
from .uxp_backend import UXPBridge

# プラットフォームに応じた実装クラスのインポート
_BRIDGES = {
    "uxp": UXPBridge
}

# macOS固有のバックエンド
if PLATFORM == "Darwin":
    from .applescript_backend import AppleScriptBridge
    _BRIDGES["applescript"] = AppleScriptBridge
    _BRIDGES["default"] = AppleScriptBridge
# Windows固有のバックエンド
elif PLATFORM == "Windows":
    from .powershell_backend import PowerShellBridge
    _BRIDGES["powershell"] = PowerShellBridge
    _BRIDGES["default"] = PowerShellBridge
else:
    # その他のプラットフォームではUXPバックエンドをデフォルトとして使用
    _BRIDGES["default"] = UXPBridge

def get_bridge(bridge_mode: str = "default") -> PhotoshopBridge:
    """指定されたモードのブリッジインスタンスを取得する（改善版）
    
    Args:
        bridge_mode: ブリッジモード（"default", "uxp", "applescript"など）
            "default": プラットフォームに応じたデフォルトのバックエンド
            "uxp": UXPプラグインを使用するバックエンド（クロスプラットフォーム）
            "applescript": AppleScriptを使用するバックエンド（macOSのみ）
            "powershell": PowerShellを使用するバックエンド（Windowsのみ）
            
    Returns:
        PhotoshopBridgeインスタンス
        
    Raises:
        RuntimeError: ブリッジの初期化に失敗した場合
    """
    try:
        if bridge_mode not in _BRIDGES:
            available_modes = list(_BRIDGES.keys())
            logger.warning(f"Unknown bridge mode: {bridge_mode}. Available modes: {available_modes}")
            logger.info(f"Falling back to default bridge mode")
            bridge_mode = "default"
            
        bridge_class = _BRIDGES[bridge_mode]
        logger.debug(f"Initializing bridge: {bridge_class.__name__}")
        
        # ブリッジインスタンスの作成
        bridge = bridge_class()
        
        # プラットフォーム互換性チェック
        if (bridge_mode == "applescript" and PLATFORM != "Darwin") or \
           (bridge_mode == "powershell" and PLATFORM != "Windows"):
            logger.warning(f"Bridge mode '{bridge_mode}' is not compatible with platform '{PLATFORM}'")
            
        return bridge
    except Exception as e:
        logger.error(f"Failed to initialize bridge: {e}")
        raise RuntimeError(f"Failed to initialize bridge: {e}")

def get_available_bridge_modes() -> List[str]:
    """利用可能なブリッジモードのリストを取得する
    
    Returns:
        利用可能なブリッジモードのリスト
    """
    return list(_BRIDGES.keys())