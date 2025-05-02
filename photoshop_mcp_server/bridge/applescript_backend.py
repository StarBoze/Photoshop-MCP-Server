import asyncio
import json
from typing import Dict, Any, Optional

from . import PhotoshopBridge

class AppleScriptBridge(PhotoshopBridge):
    """AppleScriptを使用してPhotoshopと通信するブリッジ"""
    
    def __init__(self):
        self.app_name = "Adobe Photoshop 2024"  # デフォルトのアプリケーション名
    
    def as_quote(self, path: str) -> str:
        """POSIXパスをAppleScript用にクォートする"""
        return f'POSIX file "{path}"'
    
    async def _run_applescript(self, script: str) -> tuple[str, str, int]:
        """AppleScriptを実行し、結果を返す"""
        proc = await asyncio.create_subprocess_exec(
            "/usr/bin/osascript", "-e", script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        return stdout.decode().strip(), stderr.decode().strip(), proc.returncode
    
    async def open_file(self, path: str) -> bool:
        """ファイルを開く"""
        script = f'''
            tell application "{self.app_name}"
                activate
                open {self.as_quote(path)}
            end tell
        '''
        _, _, returncode = await self._run_applescript(script)
        return returncode == 0
    
    async def execute_script(self, script: str) -> Any:
        """JavaScriptを実行する"""
        # バックスラッシュの問題を回避するために文字列を分割
        escaped_script = script.replace('"', '\\"')
        applescript = f'''
            tell application "{self.app_name}"
                activate
                do javascript "{escaped_script}"
            end tell
        '''
        stdout, stderr, returncode = await self._run_applescript(applescript)
        if returncode != 0:
            raise RuntimeError(f"Script execution failed: {stderr}")
        
        # 結果をJSONとしてパースしてみる
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            # JSONでない場合は文字列として返す
            return stdout
    
    async def get_document_info(self) -> Optional[Dict[str, Any]]:
        """現在のドキュメント情報を取得する"""
        script = f'''
            tell application "{self.app_name}"
                if not (exists document 1) then
                    return "null"
                end if
                
                set docInfo to {{}}
                set docInfo to docInfo & "{{\\\"name\\\": \\\"" & name of document 1 & "\\\""
                set docInfo to docInfo & ", \\\"width\\\": " & width of document 1
                set docInfo to docInfo & ", \\\"height\\\": " & height of document 1
                set docInfo to docInfo & ", \\\"resolution\\\": " & resolution of document 1
                set docInfo to docInfo & "}}"
                
                return docInfo
            end tell
        '''
        stdout, _, returncode = await self._run_applescript(script)
        if returncode != 0 or stdout == "null":
            return None
        
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            raise RuntimeError(f"Failed to parse document info: {stdout}")
    
    async def close_file(self, save_changes: bool = False) -> bool:
        """ファイルを閉じる"""
        save_option = "saving yes" if save_changes else "saving no"
        script = f'''
            tell application "{self.app_name}"
                if not (exists document 1) then
                    return false
                end if
                close document 1 {save_option}
                return true
            end tell
        '''
        stdout, _, returncode = await self._run_applescript(script)
        if returncode != 0:
            return False
        return stdout.lower() == "true"
    
    async def save_file(self, path: str = None) -> bool:
        """ファイルを保存する"""
        if path:
            # 指定されたパスに保存
            script = f'''
                tell application "{self.app_name}"
                    if not (exists document 1) then
                        return false
                    end if
                    save document 1 in {self.as_quote(path)}
                    return true
                end tell
            '''
        else:
            # 現在のパスに保存
            script = f'''
                tell application "{self.app_name}"
                    if not (exists document 1) then
                        return false
                    end if
                    save document 1
                    return true
                end tell
            '''
        
        stdout, _, returncode = await self._run_applescript(script)
        if returncode != 0:
            return False
        return stdout.lower() == "true"
    
    async def export_layer(self, layer_name: str, export_path: str, format: str = "PNG") -> bool:
        """レイヤーをエクスポートする"""
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
        try:
            result = await self.execute_script(js_script)
            return result is True
        except Exception as e:
            print(f"Error exporting layer: {e}")
            return False
    
    async def run_action(self, action_set: str, action_name: str) -> bool:
        """アクションを実行する"""
        script = f'''
            tell application "{self.app_name}"
                if not (exists document 1) then
                    return false
                end if
                do javascript "app.doAction('{action_name}', '{action_set}');"
                return true
            end tell
        '''
        
        stdout, stderr, returncode = await self._run_applescript(script)
        if returncode != 0:
            print(f"Error running action: {stderr}")
            return False
        return stdout.lower() == "true"
    
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
        import tempfile
        import base64
        import os
        from PIL import Image
        
        # 一時ファイルを作成
        with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # ファイルを開く
            if not await self.open_file(path):
                raise RuntimeError(f"Failed to open file: {path}")
            
            # JavaScriptを使用してサムネイルを生成
            js_script = f'''
            function generateThumbnail() {{
                var doc = app.activeDocument;
                
                // ドキュメントのサイズを取得
                var originalWidth = doc.width.value;
                var originalHeight = doc.height.value;
                
                // アスペクト比を維持したサイズを計算
                var ratio = Math.min({width} / originalWidth, {height} / originalHeight);
                var newWidth = Math.round(originalWidth * ratio);
                var newHeight = Math.round(originalHeight * ratio);
                
                // 複製して新しいサイズにリサイズ
                var docCopy = doc.duplicate();
                docCopy.resizeImage(UnitValue(newWidth, "px"), UnitValue(newHeight, "px"), null, ResampleMethod.BICUBIC);
                
                // 保存オプションを設定
                var saveOptions;
                var format = "{format}".toLowerCase();
                
                if (format === "jpeg" || format === "jpg") {{
                    saveOptions = new JPEGSaveOptions();
                    saveOptions.quality = {quality};
                    saveOptions.embedColorProfile = true;
                    saveOptions.formatOptions = FormatOptions.STANDARDBASELINE;
                    saveOptions.matte = MatteType.NONE;
                }} else if (format === "png") {{
                    saveOptions = new PNGSaveOptions();
                    saveOptions.compression = 0;
                    saveOptions.interlaced = false;
                }} else {{
                    // デフォルトはJPEG
                    saveOptions = new JPEGSaveOptions();
                    saveOptions.quality = {quality};
                }}
                
                // ファイル保存
                var fileObj = new File("{temp_path}");
                docCopy.saveAs(fileObj, saveOptions, true);
                
                // 複製を閉じる
                docCopy.close(SaveOptions.DONOTSAVECHANGES);
                
                return {{
                    width: newWidth,
                    height: newHeight
                }};
            }}
            
            JSON.stringify(generateThumbnail());
            '''
            
            # JavaScriptを実行
            result = await self.execute_script(js_script)
            
            # 結果がJSONでない場合はエラー
            if not isinstance(result, dict):
                raise RuntimeError("Failed to generate thumbnail")
            
            # 画像ファイルを読み込み、Base64エンコード
            with open(temp_path, "rb") as img_file:
                thumbnail_data = base64.b64encode(img_file.read()).decode("utf-8")
            
            return {
                "status": "ok",
                "thumbnail": thumbnail_data,
                "width": result.get("width", width),
                "height": result.get("height", height),
                "format": format
            }
            
        except Exception as e:
            raise RuntimeError(f"Error generating thumbnail: {e}")
        finally:
            # 一時ファイルを削除
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
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
        import tempfile
        import base64
        import os
        import time
        from PIL import Image
        
        # 一時ファイルを作成
        with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False) as temp_file:
            temp_path = temp_file.name
        
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
                
            js_script = f'''
            function generateThumbnail() {{
                var doc = app.activeDocument;
                
                // ドキュメントのサイズを取得
                var originalWidth = doc.width.value;
                var originalHeight = doc.height.value;
                
                // アスペクト比を維持したサイズを計算
                var ratio = Math.min({width} / originalWidth, {height} / originalHeight);
                var newWidth = Math.round(originalWidth * ratio);
                var newHeight = Math.round(originalHeight * ratio);
                
                // 複製して新しいサイズにリサイズ
                var docCopy = doc.duplicate();
                docCopy.resizeImage(UnitValue(newWidth, "px"), UnitValue(newHeight, "px"), null, ResampleMethod.BICUBIC);
                
                // 保存オプションを設定
                var saveOptions;
                var format = "{format}".toLowerCase();
                
                if (format === "jpeg" || format === "jpg") {{
                    saveOptions = new JPEGSaveOptions();
                    saveOptions.quality = {quality};
                    saveOptions.embedColorProfile = true;
                    saveOptions.formatOptions = FormatOptions.STANDARDBASELINE;
                    saveOptions.matte = MatteType.NONE;
                }} else if (format === "png") {{
                    saveOptions = new PNGSaveOptions();
                    saveOptions.compression = 0;
                    saveOptions.interlaced = false;
                }} else {{
                    // デフォルトはJPEG
                    saveOptions = new JPEGSaveOptions();
                    saveOptions.quality = {quality};
                }}
                
                // ファイル保存
                var fileObj = new File("{temp_path}");
                docCopy.saveAs(fileObj, saveOptions, true);
                
                // 複製を閉じる
                docCopy.close(SaveOptions.DONOTSAVECHANGES);
                
                return {{
                    width: newWidth,
                    height: newHeight
                }};
            }}
            
            JSON.stringify(generateThumbnail());
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
            
            # 結果がJSONでない場合はエラー
            if not isinstance(result, dict):
                if callback:
                    await callback({
                        "type": "error",
                        "data": {
                            "message": "Failed to generate thumbnail"
                        }
                    })
                raise RuntimeError("Failed to generate thumbnail")
            
            # 画像ファイルを読み込み、Base64エンコード
            if callback:
                await callback({
                    "type": "progress",
                    "data": {
                        "step": "encoding_image",
                        "progress": 80,
                        "message": "画像をエンコードしています..."
                    }
                })
                
            with open(temp_path, "rb") as img_file:
                thumbnail_data = base64.b64encode(img_file.read()).decode("utf-8")
            
            # 完了通知
            response = {
                "status": "ok",
                "thumbnail": thumbnail_data,
                "width": result.get("width", width),
                "height": result.get("height", height),
                "format": format
            }
            
            if callback:
                await callback({
                    "type": "complete",
                    "data": {
                        "width": result.get("width", width),
                        "height": result.get("height", height),
                        "format": format
                    }
                })
                
            return response
            
        except Exception as e:
            if callback:
                await callback({
                    "type": "error",
                    "data": {
                        "message": f"Error generating thumbnail: {e}"
                    }
                })
            raise RuntimeError(f"Error generating thumbnail: {e}")
        finally:
            # 一時ファイルを削除
            if os.path.exists(temp_path):
                os.remove(temp_path)