import asyncio
import json
import logging
import websockets
from typing import Dict, Any, Optional, List, Set
from . import PhotoshopBridge

# ロガーの設定
logger = logging.getLogger(__name__)

class UXPBridge(PhotoshopBridge):
    """UXPプラグインを使用してPhotoshopと通信するブリッジ"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 8765):
        """
        UXPBridgeのコンストラクタ
        
        Args:
            host: WebSocketサーバーのホスト
            port: WebSocketサーバーのポート
        """
        self.host = host
        self.port = port
        self.server = None
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.message_id = 0
        self.pending_requests: Dict[int, asyncio.Future] = {}
        
        # サーバー起動
        asyncio.create_task(self._start_server())
    
    async def _start_server(self):
        """WebSocketサーバーを起動"""
        try:
            self.server = await websockets.serve(
                self._handle_client,
                self.host,
                self.port
            )
            logger.info(f"UXP WebSocketサーバーを起動しました: ws://{self.host}:{self.port}")
        except Exception as e:
            logger.error(f"WebSocketサーバー起動エラー: {e}")
            raise
    
    async def _handle_client(self, websocket: websockets.WebSocketServerProtocol, path: str):
        """
        クライアント接続を処理
        
        Args:
            websocket: WebSocketクライアント接続
            path: リクエストパス
        """
        try:
            # クライアントを登録
            self.clients.add(websocket)
            logger.info(f"クライアント接続: {websocket.remote_address}")
            
            # 接続確認メッセージを送信
            await websocket.send(json.dumps({
                "command": "connected",
                "message": "UXP WebSocketサーバーに接続しました"
            }))
            
            # メッセージ処理ループ
            async for message in websocket:
                await self._process_message(websocket, message)
                
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"クライアント切断: {websocket.remote_address}")
        except Exception as e:
            logger.error(f"クライアント処理エラー: {e}")
        finally:
            # クライアントを削除
            self.clients.remove(websocket)
    
    async def _process_message(self, websocket: websockets.WebSocketServerProtocol, message: str):
        """
        受信メッセージを処理
        
        Args:
            websocket: WebSocketクライアント接続
            message: 受信メッセージ
        """
        try:
            data = json.loads(message)
            command = data.get("command")
            message_id = data.get("id")
            
            logger.debug(f"メッセージ受信: {command}")
            
            # コマンド応答を処理
            if command == "pong":
                logger.debug("Pong受信")
                return
                
            elif command == "action_result" or command == "document_info" or command == "error":
                # 保留中のリクエストを解決
                if message_id in self.pending_requests:
                    future = self.pending_requests.pop(message_id)
                    if command == "error":
                        future.set_exception(Exception(data.get("error", "Unknown error")))
                    else:
                        future.set_result(data)
                return
            
            # エラー応答
            await websocket.send(json.dumps({
                "command": "error",
                "id": message_id,
                "error": f"未知のコマンド: {command}"
            }))
            
        except json.JSONDecodeError:
            logger.error(f"JSONパースエラー: {message}")
            await websocket.send(json.dumps({
                "command": "error",
                "error": "無効なJSONフォーマット"
            }))
        except Exception as e:
            logger.error(f"メッセージ処理エラー: {e}")
            await websocket.send(json.dumps({
                "command": "error",
                "error": f"メッセージ処理エラー: {str(e)}"
            }))
    
    async def _send_command(self, command: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        コマンドを送信し、応答を待機
        
        Args:
            command: コマンド名
            params: コマンドパラメータ
            
        Returns:
            応答データ
        """
        if not self.clients:
            raise RuntimeError("接続中のUXPプラグインがありません")
        
        # メッセージIDをインクリメント
        self.message_id += 1
        message_id = self.message_id
        
        # 応答を待機するためのFutureを作成
        future = asyncio.Future()
        self.pending_requests[message_id] = future
        
        # コマンドを送信
        message = {
            "command": command,
            "id": message_id
        }
        if params:
            message["params"] = params
            
        # 最初の接続クライアントにメッセージを送信
        client = next(iter(self.clients))
        await client.send(json.dumps(message))
        
        # タイムアウト付きで応答を待機
        try:
            return await asyncio.wait_for(future, timeout=30.0)
        except asyncio.TimeoutError:
            self.pending_requests.pop(message_id, None)
            raise TimeoutError(f"コマンド {command} がタイムアウトしました")
    
    async def open_file(self, path: str) -> bool:
        """
        ファイルを開く
        
        Args:
            path: 開くファイルのパス
            
        Returns:
            成功したかどうか
        """
        try:
            result = await self._send_command("execute_action", {
                "actionType": "batchPlay",
                "commands": [{
                    "_obj": "open",
                    "_target": [{ "_ref": "application" }],
                    "file": { "_path": path }
                }]
            })
            return result.get("result", {}).get("success", False)
        except Exception as e:
            logger.error(f"ファイルを開く操作でエラー: {e}")
            return False
    
    async def close_file(self, save_changes: bool = False) -> bool:
        """
        ファイルを閉じる
        
        Args:
            save_changes: 変更を保存するかどうか
            
        Returns:
            成功したかどうか
        """
        try:
            save_option = "saveChanges" if save_changes else "no"
            result = await self._send_command("execute_action", {
                "actionType": "batchPlay",
                "commands": [{
                    "_obj": "close",
                    "_target": [{ "_ref": "document", "_enum": "ordinal", "_value": "first" }],
                    "saving": { "_enum": "yesNo", "_value": save_option }
                }]
            })
            return result.get("result", {}).get("success", False)
        except Exception as e:
            logger.error(f"ファイルを閉じる操作でエラー: {e}")
            return False
    
    async def save_file(self, path: str = None) -> bool:
        """
        ファイルを保存する
        
        Args:
            path: 保存先のパス。Noneの場合は現在のパスに保存
            
        Returns:
            成功したかどうか
        """
        try:
            if path:
                # 指定されたパスに保存
                result = await self._send_command("execute_action", {
                    "actionType": "batchPlay",
                    "commands": [{
                        "_obj": "save",
                        "_target": [{ "_ref": "document", "_enum": "ordinal", "_value": "first" }],
                        "as": { "_path": path }
                    }]
                })
            else:
                # 現在のパスに保存
                result = await self._send_command("execute_action", {
                    "actionType": "batchPlay",
                    "commands": [{
                        "_obj": "save",
                        "_target": [{ "_ref": "document", "_enum": "ordinal", "_value": "first" }]
                    }]
                })
            return result.get("result", {}).get("success", False)
        except Exception as e:
            logger.error(f"ファイルを保存する操作でエラー: {e}")
            return False
    
    async def export_layer(self, layer_name: str, export_path: str, format: str = "PNG") -> bool:
        """
        レイヤーをエクスポートする
        
        Args:
            layer_name: エクスポートするレイヤー名
            export_path: エクスポート先のパス
            format: エクスポート形式（PNG, JPEG, PSD等）
            
        Returns:
            成功したかどうか
        """
        try:
            # JavaScriptを使用してレイヤーをエクスポート
            js_script = f'''
            function exportLayer() {{
                var doc = app.activeDocument;
                var layerFound = false;
                
                // レイヤーを検索
                for (var i = 0; i < doc.layers.length; i++) {{
                    if (doc.layers[i].name === "{layer_name}") {{
                        layerFound = true;
                        
                        // 他のレイヤーを非表示にする
                        var visibilityState = [];
                        for (var j = 0; j < doc.layers.length; j++) {{
                            visibilityState.push(doc.layers[j].visible);
                            doc.layers[j].visible = false;
                        }}
                        
                        // 対象レイヤーを表示
                        doc.layers[i].visible = true;
                        
                        // エクスポート設定
                        var saveOptions;
                        var format = "{format}".toLowerCase();
                        
                        if (format === "png") {{
                            saveOptions = new PNGSaveOptions();
                            saveOptions.compression = 0;
                            saveOptions.interlaced = false;
                        }} else if (format === "jpeg" || format === "jpg") {{
                            saveOptions = new JPEGSaveOptions();
                            saveOptions.quality = 12;
                            saveOptions.embedColorProfile = true;
                        }} else if (format === "psd") {{
                            saveOptions = new PhotoshopSaveOptions();
                            saveOptions.embedColorProfile = true;
                        }} else {{
                            // デフォルトはPNG
                            saveOptions = new PNGSaveOptions();
                        }}
                        
                        // ファイル保存
                        var fileObj = new File("{export_path}");
                        doc.saveAs(fileObj, saveOptions, true);
                        
                        // レイヤーの表示状態を元に戻す
                        for (var j = 0; j < doc.layers.length; j++) {{
                            doc.layers[j].visible = visibilityState[j];
                        }}
                        
                        return true;
                    }}
                }}
                
                return layerFound;
            }}
            
            exportLayer();
            '''
            
            # JavaScriptを実行
            result = await self.execute_script(js_script)
            return result is True
        except Exception as e:
            logger.error(f"レイヤーエクスポート操作でエラー: {e}")
            return False
    
    async def run_action(self, action_set: str, action_name: str) -> bool:
        """
        アクションを実行する
        
        Args:
            action_set: アクションセット名
            action_name: アクション名
            
        Returns:
            成功したかどうか
        """
        try:
            result = await self.execute_script(f"app.doAction('{action_name}', '{action_set}');")
            return True
        except Exception as e:
            logger.error(f"アクション実行でエラー: {e}")
            return False
    
    async def execute_script(self, script: str) -> Any:
        """
        JavaScriptを実行する
        
        Args:
            script: 実行するJavaScriptコード
            
        Returns:
            実行結果
        """
        try:
            result = await self._send_command("execute_action", {
                "actionType": "executeJSX",
                "script": script
            })
            return result.get("result", {}).get("result")
        except Exception as e:
            logger.error(f"スクリプト実行でエラー: {e}")
            raise
    
    async def get_document_info(self) -> Dict[str, Any]:
        """
        現在のドキュメント情報を取得する
        
        Returns:
            ドキュメント情報
        """
        try:
            result = await self._send_command("get_document_info")
            info = result.get("info", {})
            if not info.get("success", False):
                return None
            return info.get("info", {})
        except Exception as e:
            logger.error(f"ドキュメント情報取得でエラー: {e}")
            return None
    
    async def stop(self):
        """WebSocketサーバーを停止"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("UXP WebSocketサーバーを停止しました")
    
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
        try:
            # ファイルを開く
            if not await self.open_file(path):
                raise RuntimeError(f"Failed to open file: {path}")
            
            # JavaScriptを使用してサムネイルを生成
            js_script = f'''
            async function generateThumbnail() {{
                try {{
                    const doc = app.activeDocument;
                    
                    // ドキュメントのサイズを取得
                    const originalWidth = doc.width.value;
                    const originalHeight = doc.height.value;
                    
                    // アスペクト比を維持したサイズを計算
                    const ratio = Math.min({width} / originalWidth, {height} / originalHeight);
                    const newWidth = Math.round(originalWidth * ratio);
                    const newHeight = Math.round(originalHeight * ratio);
                    
                    // 複製して新しいサイズにリサイズ
                    const docCopy = await doc.duplicate();
                    await docCopy.resizeImage({{
                        width: UnitValue(newWidth, "px"),
                        height: UnitValue(newHeight, "px"),
                        resolution: doc.resolution,
                        resampleMethod: ResampleMethod.BICUBIC
                    }});
                    
                    // Base64エンコードされた画像データを取得
                    const format = "{format}".toLowerCase();
                    const quality = {quality};
                    
                    let imageData;
                    if (format === "jpeg" || format === "jpg") {{
                        imageData = await docCopy.saveToOE({{
                            format: "image/jpeg",
                            quality: quality / 100
                        }});
                    }} else if (format === "png") {{
                        imageData = await docCopy.saveToOE({{
                            format: "image/png"
                        }});
                    }} else {{
                        // デフォルトはJPEG
                        imageData = await docCopy.saveToOE({{
                            format: "image/jpeg",
                            quality: quality / 100
                        }});
                    }}
                    
                    // 複製を閉じる
                    await docCopy.close(SaveOptions.DONOTSAVECHANGES);
                    
                    return {{
                        success: true,
                        thumbnail: imageData,
                        width: newWidth,
                        height: newHeight,
                        format: format
                    }};
                }} catch (error) {{
                    return {{
                        success: false,
                        error: error.toString()
                    }};
                }}
            }}
            
            return await generateThumbnail();
            '''
            
            # JavaScriptを実行
            result = await self.execute_script(js_script)
            
            # 結果を確認
            if not isinstance(result, dict) or not result.get("success", False):
                error_msg = result.get("error", "Unknown error") if isinstance(result, dict) else "Invalid result"
                raise RuntimeError(f"Failed to generate thumbnail: {error_msg}")
            
            return {
                "status": "ok",
                "thumbnail": result.get("thumbnail", ""),
                "width": result.get("width", width),
                "height": result.get("height", height),
                "format": result.get("format", format)
            }
            
        except Exception as e:
            logger.error(f"Error generating thumbnail: {e}")
            raise RuntimeError(f"Error generating thumbnail: {e}")
            
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
        try:
            # 開始通知
            if callback:
                await callback({
                    "type": "start",
                    "data": {
                        "path": path,
                        "width": width,
                        "height": height,
                        "format": format
                    }
                })
            
            # ファイルを開く
            if callback:
                await callback({
                    "type": "progress",
                    "data": {
                        "step": "opening_file",
                        "progress": 10,
                        "message": "ファイルを開いています..."
                    }
                })
                
            if not await self.open_file(path):
                if callback:
                    await callback({
                        "type": "error",
                        "data": {
                            "message": f"Failed to open file: {path}"
                        }
                    })
                raise RuntimeError(f"Failed to open file: {path}")
            
            # JavaScriptを使用してサムネイルを生成
            if callback:
                await callback({
                    "type": "progress",
                    "data": {
                        "step": "generating_thumbnail",
                        "progress": 30,
                        "message": "サムネイルを生成しています..."
                    }
                })
                
            # JavaScriptを使用してサムネイルを生成
            js_script = f'''
            async function generateThumbnail() {{
                try {{
                    const doc = app.activeDocument;
                    
                    // ドキュメントのサイズを取得
                    const originalWidth = doc.width.value;
                    const originalHeight = doc.height.value;
                    
                    // アスペクト比を維持したサイズを計算
                    const ratio = Math.min({width} / originalWidth, {height} / originalHeight);
                    const newWidth = Math.round(originalWidth * ratio);
                    const newHeight = Math.round(originalHeight * ratio);
                    
                    // 複製して新しいサイズにリサイズ
                    const docCopy = await doc.duplicate();
                    await docCopy.resizeImage({{
                        width: UnitValue(newWidth, "px"),
                        height: UnitValue(newHeight, "px"),
                        resolution: doc.resolution,
                        resampleMethod: ResampleMethod.BICUBIC
                    }});
                    
                    // Base64エンコードされた画像データを取得
                    const format = "{format}".toLowerCase();
                    const quality = {quality};
                    
                    let imageData;
                    if (format === "jpeg" || format === "jpg") {{
                        imageData = await docCopy.saveToOE({{
                            format: "image/jpeg",
                            quality: quality / 100
                        }});
                    }} else if (format === "png") {{
                        imageData = await docCopy.saveToOE({{
                            format: "image/png"
                        }});
                    }} else {{
                        // デフォルトはJPEG
                        imageData = await docCopy.saveToOE({{
                            format: "image/jpeg",
                            quality: quality / 100
                        }});
                    }}
                    
                    // 複製を閉じる
                    await docCopy.close(SaveOptions.DONOTSAVECHANGES);
                    
                    return {{
                        success: true,
                        thumbnail: imageData,
                        width: newWidth,
                        height: newHeight,
                        format: format
                    }};
                }} catch (error) {{
                    return {{
                        success: false,
                        error: error.toString()
                    }};
                }}
            }}
            
            return await generateThumbnail();
            '''
            
            # JavaScriptを実行
            if callback:
                await callback({
                    "type": "progress",
                    "data": {
                        "step": "executing_script",
                        "progress": 50,
                        "message": "スクリプトを実行しています..."
                    }
                })
                
            result = await self.execute_script(js_script)
            
            # 結果を確認
            if not isinstance(result, dict) or not result.get("success", False):
                error_msg = result.get("error", "Unknown error") if isinstance(result, dict) else "Invalid result"
                if callback:
                    await callback({
                        "type": "error",
                        "data": {
                            "message": f"Failed to generate thumbnail: {error_msg}"
                        }
                    })
                raise RuntimeError(f"Failed to generate thumbnail: {error_msg}")
            
            # 画像処理
            if callback:
                await callback({
                    "type": "progress",
                    "data": {
                        "step": "processing_image",
                        "progress": 80,
                        "message": "画像を処理しています..."
                    }
                })
            
            # 完了通知
            response = {
                "status": "ok",
                "thumbnail": result.get("thumbnail", ""),
                "width": result.get("width", width),
                "height": result.get("height", height),
                "format": result.get("format", format)
            }
            
            if callback:
                await callback({
                    "type": "complete",
                    "data": {
                        "width": result.get("width", width),
                        "height": result.get("height", height),
                        "format": result.get("format", format)
                    }
                })
                
            return response
            
        except Exception as e:
            logger.error(f"Error generating thumbnail: {e}")
            if callback:
                await callback({
                    "type": "error",
                    "data": {
                        "message": f"Error generating thumbnail: {e}"
                    }
                })
            raise RuntimeError(f"Error generating thumbnail: {e}")