# MCP スキーマ定義
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional

class MCPServerInfo(BaseModel):
    """MCPサーバー情報"""
    name: str = "photoshop-mcp-server"
    version: str = "0.1.0"
    description: str = "Photoshop MCP Server for macOS"

class MCPToolSchema(BaseModel):
    """MCPツールスキーマ"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]

class MCPResourceSchema(BaseModel):
    """MCPリソーススキーマ"""
    uri_pattern: str
    description: str

class MCPServerSchema(BaseModel):
    """MCPサーバースキーマ"""
    server_info: MCPServerInfo
    tools: List[MCPToolSchema]
    resources: List[MCPResourceSchema]

# 共通のレスポンスモデル
class StatusResponse(BaseModel):
    """ステータスレスポンス"""
    status: str = "ok"

# Photoshop操作関連のスキーマ
class OpenFileRequest(BaseModel):
    """ファイルを開くリクエスト"""
    path: str = Field(..., description="開くファイルのパス")
    bridge_mode: Optional[str] = Field("applescript", description="使用するブリッジモード")

class CloseFileRequest(BaseModel):
    """ファイルを閉じるリクエスト"""
    save_changes: bool = Field(False, description="変更を保存するかどうか")
    bridge_mode: Optional[str] = Field("applescript", description="使用するブリッジモード")

class SaveFileRequest(BaseModel):
    """ファイルを保存するリクエスト"""
    path: Optional[str] = Field(None, description="保存先のパス。指定しない場合は現在のパスに保存")
    bridge_mode: Optional[str] = Field("applescript", description="使用するブリッジモード")

class ExportLayerRequest(BaseModel):
    """レイヤーをエクスポートするリクエスト"""
    layer: str = Field(..., description="エクスポートするレイヤー名")
    format: str = Field("png", description="エクスポート形式（png, jpeg, psd等）")
    dest: str = Field(..., description="エクスポート先のパス")
    bridge_mode: Optional[str] = Field("applescript", description="使用するブリッジモード")

class RunActionRequest(BaseModel):
    """アクションを実行するリクエスト"""
    set: str = Field(..., description="アクションセット名")
    action: str = Field(..., description="アクション名")
    bridge_mode: Optional[str] = Field("applescript", description="使用するブリッジモード")

class ExecuteScriptRequest(BaseModel):
    """スクリプトを実行するリクエスト"""
    script: str = Field(..., description="実行するJavaScriptコード")
    bridge_mode: Optional[str] = Field("applescript", description="使用するブリッジモード")

class GetDocumentInfoRequest(BaseModel):
    """ドキュメント情報を取得するリクエスト"""
    bridge_mode: Optional[str] = Field("applescript", description="使用するブリッジモード")

class DocumentInfo(BaseModel):
    """ドキュメント情報"""
    name: str
    width: float
    height: float
    resolution: float

class HealthResponse(BaseModel):
    """ヘルスチェックレスポンス"""
    status: str = "ok"
    photoshop_running: bool
    active_document: Optional[str] = None
    uxp_connected: Optional[bool] = None

# サムネイル生成関連のスキーマ
class GenerateThumbnailRequest(BaseModel):
    """サムネイルを生成するリクエスト"""
    path: str = Field(..., description="サムネイルを生成するファイルのパス")
    width: int = Field(256, description="サムネイルの幅")
    height: int = Field(256, description="サムネイルの高さ")
    format: str = Field("jpeg", description="出力形式（jpeg, png）")
    quality: int = Field(80, description="画質（0-100）")
    bridge_mode: str = Field("applescript", description="使用するブリッジモード")

# LLM自動レタッチ関連のスキーマ
class AutoRetouchRequest(BaseModel):
    """画像を自動レタッチするリクエスト"""
    path: str = Field(..., description="レタッチする画像のパス")
    instructions: Optional[str] = None
    bridge_mode: str = Field("applescript", description="使用するブリッジモード")

class AutoRetouchResponse(BaseModel):
    """自動レタッチレスポンス"""
    status: str
    retouch_actions: List[Dict[str, Any]]
    output_path: Optional[str] = None

class ThumbnailResponse(BaseModel):
    """サムネイルレスポンス"""
    status: str
    thumbnail: str = Field(..., description="Base64エンコードされた画像データ")
    width: int
    height: int
    format: str

# ストリーミング関連のスキーマ
class StreamMessage(BaseModel):
    """ストリーミングメッセージ"""
    type: str = Field(..., description="メッセージタイプ（start, progress, complete, error）")
    data: Dict[str, Any] = Field({}, description="メッセージデータ")

class ThumbnailStreamRequest(BaseModel):
    """サムネイル生成ストリーミングリクエスト"""
    path: str = Field(..., description="サムネイルを生成するファイルのパス")
    width: int = Field(256, description="サムネイルの幅")
    height: int = Field(256, description="サムネイルの高さ")
    format: str = Field("jpeg", description="出力形式（jpeg, png）")
    quality: int = Field(80, description="画質（0-100）")
    bridge_mode: str = Field("applescript", description="使用するブリッジモード")