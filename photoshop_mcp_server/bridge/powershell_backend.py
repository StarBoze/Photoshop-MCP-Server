import os
import json
import asyncio
import tempfile
import base64
import logging
import subprocess
import time
from typing import Dict, Any, Optional, Union, Tuple, Dict, Callable

from . import PhotoshopBridge
from .path_utils import normalize_path, format_path_for_script

class PowerShellBridge(PhotoshopBridge):
    """PowerShellを使用してPhotoshopと通信するWindows用ブリッジ"""
    
    def __init__(self):
        """PowerShellブリッジの初期化"""
        self.ps_executable = "powershell.exe"
        self.app_name = "Photoshop.Application"  # COMオブジェクト名
        self.timeout = 30  # スクリプト実行のタイムアウト（秒）
        self.max_retries = 3  # エラー時の最大リトライ回数
        self.retry_delay = 1.0  # リトライ間の待機時間（秒）
        self._script_cache = {}  # スクリプトキャッシュ
        
        # ロガーの設定
        self.logger = logging.getLogger('photoshop_mcp_server.bridge.powershell')
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    async def _run_powershell_script(self, script: str) -> tuple[str, str, int]:
        """PowerShellスクリプトを実行し、結果を返す"""
        # 一時ファイルにスクリプトを書き込む
        with tempfile.NamedTemporaryFile(suffix='.ps1', delete=False, mode='w', encoding='utf-8') as f:
            f.write(script)
            temp_script_path = f.name
            
        try:
            # PowerShellスクリプトを実行
            proc = await asyncio.create_subprocess_exec(
                self.ps_executable,
                "-ExecutionPolicy", "Bypass",
                "-File", temp_script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            return stdout.decode().strip(), stderr.decode().strip(), proc.returncode
        except Exception as e:
            raise RuntimeError(f"PowerShell script execution failed: {str(e)}")
        finally:
            # 一時ファイルを削除
            os.unlink(temp_script_path)
            
    def _run_powershell_script_sync(self, script: str) -> str:
        """PowerShellスクリプトを実行し、結果を返す（同期版、最適化）"""
        # スクリプトキャッシュの確認
        script_hash = hash(script)
        if script_hash in self._script_cache:
            self.logger.debug("Using cached script result")
            return self._script_cache[script_hash]
            
        # 一時ファイルにスクリプトを書き込む
        with tempfile.NamedTemporaryFile(suffix='.ps1', delete=False, mode='w', encoding='utf-8') as f:
            f.write(script)
            temp_script_path = f.name
            
        try:
            # PowerShellスクリプトを実行（タイムアウト設定追加）
            start_time = time.time()
            self.logger.debug(f"Executing PowerShell script (timeout: {self.timeout}s)")
            
            result = subprocess.run(
                [self.ps_executable, "-ExecutionPolicy", "Bypass", "-File", temp_script_path],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            execution_time = time.time() - start_time
            self.logger.debug(f"Script execution completed in {execution_time:.2f}s")
            
            if result.returncode != 0:
                self.logger.warning(f"PowerShell script execution failed: {result.stderr}")
                
            output = result.stdout.strip()
            
            # 結果をキャッシュ（成功した場合のみ）
            if result.returncode == 0:
                self._script_cache[script_hash] = output
                
            return output
        except subprocess.TimeoutExpired:
            error_msg = f"PowerShell script execution timed out after {self.timeout} seconds"
            self.logger.error(error_msg)
            raise TimeoutError(error_msg)
        except subprocess.CalledProcessError as e:
            # エラーログの詳細化
            error_msg = f"PowerShell script execution failed: {e.stderr}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            error_msg = f"PowerShell script execution failed: {str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
        finally:
            # 一時ファイルを削除
            try:
                os.unlink(temp_script_path)
            except Exception as e:
                self.logger.warning(f"Failed to delete temporary script file: {e}")
    
    async def open_file(self, path: str) -> bool:
        """ファイルを開く"""
        path = normalize_path(path)
        script = f"""
        try {{
            $app = New-Object -ComObject {self.app_name}
            $app.Open("{path}")
            Write-Output "true"
            exit 0
        }} catch {{
            Write-Error $_.Exception.Message
            Write-Output "false"
            exit 1
        }}
        """
        stdout, stderr, returncode = await self._run_powershell_script(script)
        if returncode != 0:
            print(f"Error opening file: {stderr}")
            return False
        return stdout.lower() == "true"
    
    async def close_file(self, save_changes: bool = False) -> bool:
        """ファイルを閉じる"""
        save_option = "$true" if save_changes else "$false"
        script = f"""
        try {{
            $app = New-Object -ComObject {self.app_name}
            if ($app.Documents.Count -eq 0) {{
                Write-Output "false"
                exit 0
            }}
            
            $doc = $app.ActiveDocument
            $doc.Close({save_option})
            Write-Output "true"
            exit 0
        }} catch {{
            Write-Error $_.Exception.Message
            Write-Output "false"
            exit 1
        }}
        """
        stdout, stderr, returncode = await self._run_powershell_script(script)
        if returncode != 0:
            print(f"Error closing file: {stderr}")
            return False
        return stdout.lower() == "true"
    
    async def save_file(self, path: str = None) -> bool:
        """現在のドキュメントを保存する"""
        if path:
            path = normalize_path(path)
            script = f"""
            try {{
                $app = New-Object -ComObject {self.app_name}
                if ($app.Documents.Count -eq 0) {{
                    Write-Output "false"
                    exit 0
                }}
                
                $doc = $app.ActiveDocument
                $saveOptions = New-Object -ComObject Photoshop.PhotoshopSaveOptions
                $doc.SaveAs("{path}", $saveOptions, $true)
                Write-Output "true"
                exit 0
            }} catch {{
                Write-Error $_.Exception.Message
                Write-Output "false"
                exit 1
            }}
            """
        else:
            script = f"""
            try {{
                $app = New-Object -ComObject {self.app_name}
                if ($app.Documents.Count -eq 0) {{
                    Write-Output "false"
                    exit 0
                }}
                
                $doc = $app.ActiveDocument
                $doc.Save()
                Write-Output "true"
                exit 0
            }} catch {{
                Write-Error $_.Exception.Message
                Write-Output "false"
                exit 1
            }}
            """
        
        stdout, stderr, returncode = await self._run_powershell_script(script)
        if returncode != 0:
            print(f"Error saving file: {stderr}")
            return False
        return stdout.lower() == "true"
    
    async def execute_script(self, script: str) -> Any:
        """JavaScriptを実行する（エラーリトライ機能付き）"""
        # JavaScriptのエスケープ
        escaped_script = script.replace('"', '`"').replace("'", "`'")
        
        ps_script = f"""
        try {{
            $app = New-Object -ComObject {self.app_name}
            $result = $app.DoJavaScript("{escaped_script}")
            Write-Output $result
            exit 0
        }} catch {{
            Write-Error $_.Exception.Message
            exit 1
        }}
        """
        
        # リトライロジックの実装
        retry_count = 0
        last_error = None
        
        while retry_count <= self.max_retries:
            try:
                if retry_count > 0:
                    self.logger.info(f"Retrying script execution (attempt {retry_count}/{self.max_retries})")
                    # リトライ間の待機
                    await asyncio.sleep(self.retry_delay)
                
                stdout, stderr, returncode = await self._run_powershell_script(ps_script)
                if returncode != 0:
                    raise RuntimeError(f"Script execution failed: {stderr}")
                
                # 結果をJSONとしてパースしてみる
                try:
                    return json.loads(stdout)
                except json.JSONDecodeError:
                    # JSONでない場合は文字列として返す
                    return stdout
                    
            except Exception as e:
                last_error = e
                retry_count += 1
                self.logger.warning(f"Error during script execution: {e}. Retry {retry_count}/{self.max_retries}")
                
        # すべてのリトライが失敗した場合
        self.logger.error(f"Script execution failed after {self.max_retries} retries: {last_error}")
        raise last_error
    
    async def get_document_info(self) -> Optional[Dict[str, Any]]:
        """現在のドキュメント情報を取得する"""
        script = f"""
        try {{
            $app = New-Object -ComObject {self.app_name}
            if ($app.Documents.Count -eq 0) {{
                Write-Output "null"
                exit 0
            }}
            
            $doc = $app.ActiveDocument
            $info = @{{
                "name" = $doc.Name
                "width" = $doc.Width
                "height" = $doc.Height
                "resolution" = $doc.Resolution
                "path" = $doc.FullName
            }}
            
            $jsonInfo = ConvertTo-Json $info
            Write-Output $jsonInfo
            exit 0
        }} catch {{
            Write-Error $_.Exception.Message
            exit 1
        }}
        """
        
        stdout, stderr, returncode = await self._run_powershell_script(script)
        if returncode != 0 or stdout == "null":
            return None
        
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            raise RuntimeError(f"Failed to parse document info: {stdout}")
    
    def export_layer(self, layer_id: str, path: str, format: str = "jpeg", quality: int = 80) -> Dict[str, Any]:
        """指定したレイヤーをエクスポートする"""
        path = normalize_path(path)
        script = f"""
        try {{
            $app = New-Object -ComObject Photoshop.Application
            if ($app.Documents.Count -eq 0) {{
                Write-Output "{{ \\"status\\": \\"error\\", \\"message\\": \\"No document is open\\" }}"
                exit
            }}
            
            $doc = $app.ActiveDocument
            
            # レイヤーの表示/非表示を設定
            foreach ($layer in $doc.ArtLayers) {{
                if ($layer.Name -eq "{layer_id}") {{
                    $layer.Visible = $true
                    $targetLayer = $layer
                }} else {{
                    $layer.Visible = $false
                }}
            }}
            
            # ファイル形式の設定
            $saveOptions = $null
            switch ("{format.lower()}") {{
                "jpeg" {{
                    $saveOptions = New-Object -ComObject Photoshop.JPEGSaveOptions
                    $saveOptions.Quality = {quality}
                    $saveOptions.EmbedColorProfile = $true
                    $saveOptions.FormatOptions = 1  # StandardBaseline
                    $saveOptions.Matte = 1  # None
                    $extension = ".jpg"
                }}
                "png" {{
                    $saveOptions = New-Object -ComObject Photoshop.PNGSaveOptions
                    $saveOptions.Interlaced = $false
                    $extension = ".png"
                }}
                "tiff" {{
                    $saveOptions = New-Object -ComObject Photoshop.TiffSaveOptions
                    $saveOptions.EmbedColorProfile = $true
                    $saveOptions.ImageCompression = 1  # LZW
                    $extension = ".tif"
                }}
                default {{
                    Write-Output "{{ \\"status\\": \\"error\\", \\"message\\": \\"Unsupported format: {format}\\" }}"
                    exit
                }}
            }}
            
            # ファイルの保存
            $doc.SaveAs("{path}", $saveOptions, $true, 2)  # 2 = Extension Type: Lowercase
            
            Write-Output "{{ \\"status\\": \\"success\\", \\"message\\": \\"Layer exported successfully\\", \\"path\\": \\"{path}\\", \\"format\\": \\"{format}\\" }}"
        }} catch {{
            Write-Output "{{ \\"status\\": \\"error\\", \\"message\\": \\"$($_.Exception.Message)\\" }}"
        }} finally {{
            # すべてのレイヤーを再表示
            if ($doc -ne $null) {{
                foreach ($layer in $doc.ArtLayers) {{
                    $layer.Visible = $true
                }}
            }}
        }}
        """
        result = self._run_powershell_script_sync(script)
        return json.loads(result)
        
    async def export_layer_async(self, layer_id: str, path: str, format: str = "jpeg", quality: int = 80) -> Dict[str, Any]:
        """指定したレイヤーをエクスポートする（非同期版）"""
        path = normalize_path(path)
        script = f"""
        try {{
            $app = New-Object -ComObject Photoshop.Application
            if ($app.Documents.Count -eq 0) {{
                Write-Output "{{ \\"status\\": \\"error\\", \\"message\\": \\"No document is open\\" }}"
                exit
            }}
            
            $doc = $app.ActiveDocument
            
            # レイヤーの表示/非表示を設定
            foreach ($layer in $doc.ArtLayers) {{
                if ($layer.Name -eq "{layer_id}") {{
                    $layer.Visible = $true
                    $targetLayer = $layer
                }} else {{
                    $layer.Visible = $false
                }}
            }}
            
            # ファイル形式の設定
            $saveOptions = $null
            switch ("{format.lower()}") {{
                "jpeg" {{
                    $saveOptions = New-Object -ComObject Photoshop.JPEGSaveOptions
                    $saveOptions.Quality = {quality}
                    $saveOptions.EmbedColorProfile = $true
                    $saveOptions.FormatOptions = 1  # StandardBaseline
                    $saveOptions.Matte = 1  # None
                    $extension = ".jpg"
                }}
                "png" {{
                    $saveOptions = New-Object -ComObject Photoshop.PNGSaveOptions
                    $saveOptions.Interlaced = $false
                    $extension = ".png"
                }}
                "tiff" {{
                    $saveOptions = New-Object -ComObject Photoshop.TiffSaveOptions
                    $saveOptions.EmbedColorProfile = $true
                    $saveOptions.ImageCompression = 1  # LZW
                    $extension = ".tif"
                }}
                default {{
                    Write-Output "{{ \\"status\\": \\"error\\", \\"message\\": \\"Unsupported format: {format}\\" }}"
                    exit
                }}
            }}
            
            # ファイルの保存
            $doc.SaveAs("{path}", $saveOptions, $true, 2)  # 2 = Extension Type: Lowercase
            
            Write-Output "{{ \\"status\\": \\"success\\", \\"message\\": \\"Layer exported successfully\\", \\"path\\": \\"{path}\\", \\"format\\": \\"{format}\\" }}"
        }} catch {{
            Write-Output "{{ \\"status\\": \\"error\\", \\"message\\": \\"$($_.Exception.Message)\\" }}"
        }} finally {{
            # すべてのレイヤーを再表示
            if ($doc -ne $null) {{
                foreach ($layer in $doc.ArtLayers) {{
                    $layer.Visible = $true
                }}
            }}
        }}
        """
        stdout, stderr, returncode = await self._run_powershell_script(script)
        if returncode != 0:
            return {"status": "error", "message": stderr}
        return json.loads(stdout)
    
    def run_action(self, action_set: str, action_name: str) -> Dict[str, Any]:
        """アクションを実行する"""
        script = f"""
        try {{
            $app = New-Object -ComObject Photoshop.Application
            if ($app.Documents.Count -eq 0) {{
                Write-Output "{{ \\"status\\": \\"error\\", \\"message\\": \\"No document is open\\" }}"
                exit
            }}
            
            # アクションの実行
            $app.DoAction("{action_name}", "{action_set}")
            
            Write-Output "{{ \\"status\\": \\"success\\", \\"message\\": \\"Action executed successfully\\", \\"action_set\\": \\"{action_set}\\", \\"action_name\\": \\"{action_name}\\" }}"
        }} catch {{
            Write-Output "{{ \\"status\\": \\"error\\", \\"message\\": \\"$($_.Exception.Message)\\" }}"
        }}
        """
        result = self._run_powershell_script_sync(script)
        return json.loads(result)
        
    async def run_action_async(self, action_set: str, action_name: str) -> Dict[str, Any]:
        """アクションを実行する（非同期版）"""
        script = f"""
        try {{
            $app = New-Object -ComObject Photoshop.Application
            if ($app.Documents.Count -eq 0) {{
                Write-Output "{{ \\"status\\": \\"error\\", \\"message\\": \\"No document is open\\" }}"
                exit
            }}
            
            # アクションの実行
            $app.DoAction("{action_name}", "{action_set}")
            
            Write-Output "{{ \\"status\\": \\"success\\", \\"message\\": \\"Action executed successfully\\", \\"action_set\\": \\"{action_set}\\", \\"action_name\\": \\"{action_name}\\" }}"
        }} catch {{
            Write-Output "{{ \\"status\\": \\"error\\", \\"message\\": \\"$($_.Exception.Message)\\" }}"
        }}
        """
        stdout, stderr, returncode = await self._run_powershell_script(script)
        if returncode != 0:
            return {"status": "error", "message": stderr}
        return json.loads(stdout)
    
    def generate_thumbnail(self, path: str, width: int, height: int, format: str = "jpeg", quality: int = 80) -> Dict[str, Any]:
        """サムネイルを生成する"""
        path = normalize_path(path)
        temp_file = os.path.join(tempfile.gettempdir(), f"thumbnail_{os.path.basename(path)}")
        
        script = f"""
        try {{
            $app = New-Object -ComObject Photoshop.Application
            
            # ファイルを開く
            $doc = $app.Open("{path}")
            
            # ドキュメントのサイズを取得
            $originalWidth = $doc.Width
            $originalHeight = $doc.Height
            
            # アスペクト比を維持したリサイズ
            $ratio = [Math]::Min({width} / $originalWidth, {height} / $originalHeight)
            $newWidth = [Math]::Round($originalWidth * $ratio)
            $newHeight = [Math]::Round($originalHeight * $ratio)
            
            # ドキュメントをリサイズ
            $doc.ResizeImage($newWidth, $newHeight, $doc.Resolution, 1, 0)  # 1 = Bicubic, 0 = No automatic interpolation
            
            # ファイル形式の設定
            $saveOptions = $null
            switch ("{format.lower()}") {{
                "jpeg" {{
                    $saveOptions = New-Object -ComObject Photoshop.JPEGSaveOptions
                    $saveOptions.Quality = {quality}
                    $saveOptions.EmbedColorProfile = $true
                    $saveOptions.FormatOptions = 1  # StandardBaseline
                    $saveOptions.Matte = 1  # None
                    $extension = ".jpg"
                }}
                "png" {{
                    $saveOptions = New-Object -ComObject Photoshop.PNGSaveOptions
                    $saveOptions.Interlaced = $false
                    $extension = ".png"
                }}
                default {{
                    $saveOptions = New-Object -ComObject Photoshop.JPEGSaveOptions
                    $saveOptions.Quality = {quality}
                    $extension = ".jpg"
                }}
            }}
            
            # サムネイルを保存
            $thumbnailPath = "{temp_file}" + $extension
            $doc.SaveAs($thumbnailPath, $saveOptions, $true, 2)  # 2 = Extension Type: Lowercase
            
            # ドキュメントを閉じる
            $doc.Close(2)  # 2 = Don't save changes
            
            # サムネイルのBase64エンコード
            $bytes = [System.IO.File]::ReadAllBytes($thumbnailPath)
            $base64 = [Convert]::ToBase64String($bytes)
            
            # 一時ファイルを削除
            Remove-Item $thumbnailPath
            
            Write-Output "{{ \\"status\\": \\"success\\", \\"thumbnail\\": \\"$base64\\", \\"width\\": $newWidth, \\"height\\": $newHeight, \\"format\\": \\"{format}\\" }}"
        }} catch {{
            Write-Output "{{ \\"status\\": \\"error\\", \\"message\\": \\"$($_.Exception.Message)\\" }}"
        }}
        """
        result = self._run_powershell_script_sync(script)
        return json.loads(result)
        
    async def generate_thumbnail_async(self, path: str, width: int, height: int, format: str = "jpeg", quality: int = 80) -> Dict[str, Any]:
        """サムネイルを生成する（非同期版）"""
        path = normalize_path(path)
        temp_file = os.path.join(tempfile.gettempdir(), f"thumbnail_{os.path.basename(path)}")
        
        script = f"""
        try {{
            $app = New-Object -ComObject Photoshop.Application
            
            # ファイルを開く
            $doc = $app.Open("{path}")
            
            # ドキュメントのサイズを取得
            $originalWidth = $doc.Width
            $originalHeight = $doc.Height
            
            # アスペクト比を維持したリサイズ
            $ratio = [Math]::Min({width} / $originalWidth, {height} / $originalHeight)
            $newWidth = [Math]::Round($originalWidth * $ratio)
            $newHeight = [Math]::Round($originalHeight * $ratio)
            
            # ドキュメントをリサイズ
            $doc.ResizeImage($newWidth, $newHeight, $doc.Resolution, 1, 0)  # 1 = Bicubic, 0 = No automatic interpolation
            
            # ファイル形式の設定
            $saveOptions = $null
            switch ("{format.lower()}") {{
                "jpeg" {{
                    $saveOptions = New-Object -ComObject Photoshop.JPEGSaveOptions
                    $saveOptions.Quality = {quality}
                    $saveOptions.EmbedColorProfile = $true
                    $saveOptions.FormatOptions = 1  # StandardBaseline
                    $saveOptions.Matte = 1  # None
                    $extension = ".jpg"
                }}
                "png" {{
                    $saveOptions = New-Object -ComObject Photoshop.PNGSaveOptions
                    $saveOptions.Interlaced = $false
                    $extension = ".png"
                }}
                default {{
                    $saveOptions = New-Object -ComObject Photoshop.JPEGSaveOptions
                    $saveOptions.Quality = {quality}
                    $extension = ".jpg"
                }}
            }}
            
            # サムネイルを保存
            $thumbnailPath = "{temp_file}" + $extension
            $doc.SaveAs($thumbnailPath, $saveOptions, $true, 2)  # 2 = Extension Type: Lowercase
            
            # ドキュメントを閉じる
            $doc.Close(2)  # 2 = Don't save changes
            
            # サムネイルのBase64エンコード
            $bytes = [System.IO.File]::ReadAllBytes($thumbnailPath)
            $base64 = [Convert]::ToBase64String($bytes)
            
            # 一時ファイルを削除
            Remove-Item $thumbnailPath
            
            Write-Output "{{ \\"status\\": \\"success\\", \\"thumbnail\\": \\"$base64\\", \\"width\\": $newWidth, \\"height\\": $newHeight, \\"format\\": \\"{format}\\" }}"
        }} catch {{
            Write-Output "{{ \\"status\\": \\"error\\", \\"message\\": \\"$($_.Exception.Message)\\" }}"
        }}
        """
        stdout, stderr, returncode = await self._run_powershell_script(script)
        if returncode != 0:
            return {"status": "error", "message": stderr}
        return json.loads(stdout)
    
    async def generate_thumbnail_stream(self, path: str, width: int = 256, height: int = 256, format: str = "jpeg", quality: int = 80, callback=None) -> dict:
        """サムネイルを生成し、進捗状況をコールバックで通知する"""
        import tempfile
        import base64
        import os
        import time
        
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
                
            # Windowsパスのバックスラッシュをエスケープ
            temp_path_js = temp_path.replace('\\', '\\\\')
            
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
                var fileObj = new File("{temp_path_js}");
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
                    "data": response
                })
                
            return response
            
        except Exception as e:
            if callback:
                await callback({
                    "type": "error",
                    "data": {
                        "message": f"Error generating thumbnail: {str(e)}"
                    }
                })
            raise RuntimeError(f"Error generating thumbnail: {e}")
        finally:
            # 一時ファイルを削除
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    def execute_javascript(self, script: str) -> Dict[str, Any]:
        """JavaScriptを実行する"""
        # JavaScriptのエスケープ
        escaped_script = script.replace('"', '`"').replace("'", "`'")
        
        ps_script = f"""
        try {{
            $app = New-Object -ComObject Photoshop.Application
            if ($app.Documents.Count -eq 0) {{
                Write-Output "{{ \\"status\\": \\"error\\", \\"message\\": \\"No document is open\\" }}"
                exit
            }}
            
            # JavaScriptの実行
            $result = $app.DoJavaScript("{escaped_script}")
            
            Write-Output "{{ \\"status\\": \\"success\\", \\"result\\": \\"$result\\" }}"
        }} catch {{
            Write-Output "{{ \\"status\\": \\"error\\", \\"message\\": \\"$($_.Exception.Message)\\" }}"
        }}
        """
        result = self._run_powershell_script_sync(ps_script)
        return json.loads(result)
        
    async def execute_javascript_async(self, script: str) -> Dict[str, Any]:
        """JavaScriptを実行する（非同期版）"""
        # JavaScriptのエスケープ
        escaped_script = script.replace('"', '`"').replace("'", "`'")
        
        ps_script = f"""
        try {{
            $app = New-Object -ComObject Photoshop.Application
            if ($app.Documents.Count -eq 0) {{
                Write-Output "{{ \\"status\\": \\"error\\", \\"message\\": \\"No document is open\\" }}"
                exit
            }}
            
            # JavaScriptの実行
            $result = $app.DoJavaScript("{escaped_script}")
            
            Write-Output "{{ \\"status\\": \\"success\\", \\"result\\": \\"$result\\" }}"
        }} catch {{
            Write-Output "{{ \\"status\\": \\"error\\", \\"message\\": \\"$($_.Exception.Message)\\" }}"
        }}
        """
        stdout, stderr, returncode = await self._run_powershell_script(ps_script)
        if returncode != 0:
            return {"status": "error", "message": stderr}
        return json.loads(stdout)