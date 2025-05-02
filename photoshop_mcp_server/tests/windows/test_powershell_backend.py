import unittest
import os
import platform
import tempfile
import logging
from unittest.mock import patch, MagicMock

from photoshop_mcp_server.bridge.powershell_backend import PowerShellBridge

@unittest.skipIf(platform.system() != "Windows", "Windows専用のテスト")
class TestPowerShellBackend(unittest.TestCase):
    """PowerShellバックエンドのテスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.bridge = PowerShellBridge()
        # テスト用の一時ファイル
        self.temp_file = tempfile.NamedTemporaryFile(suffix='.psd', delete=False)
        self.temp_file.close()
        
    def tearDown(self):
        """テスト後のクリーンアップ"""
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)
    
    @patch('subprocess.run')
    def test_run_powershell_script(self, mock_run):
        """PowerShellスクリプト実行機能のテスト"""
        # モックの設定
        mock_process = MagicMock()
        mock_process.stdout = '{"status": "success", "message": "Test"}'
        mock_process.returncode = 0
        mock_run.return_value = mock_process
        
        # テスト実行
        result = self.bridge._run_powershell_script_sync("Test script")
        
        # 検証
        self.assertEqual(result, '{"status": "success", "message": "Test"}')
        mock_run.assert_called_once()
        
    @patch('photoshop_mcp_server.bridge.powershell_backend.PowerShellBridge._run_powershell_script_sync')
    def test_open_file(self, mock_run_script):
        """ファイルを開く機能のテスト"""
        # モックの設定
        mock_run_script.return_value = 'true'
        
        # テスト実行
        result = self.bridge.open_file(self.temp_file.name)
        
        # 検証 - 非同期メソッドの結果を取得するためにasyncioのイベントループを使用
        import asyncio
        result = asyncio.run(result)
        self.assertTrue(result)
        mock_run_script.assert_called_once()
        
    @patch('photoshop_mcp_server.bridge.powershell_backend.PowerShellBridge._run_powershell_script_sync')
    def test_close_file(self, mock_run_script):
        """ファイルを閉じる機能のテスト"""
        # モックの設定
        mock_run_script.return_value = 'true'
        
        # テスト実行
        result = self.bridge.close_file()
        
        # 検証
        result = asyncio.run(result)
        self.assertTrue(result)
        mock_run_script.assert_called_once()
        
    @patch('photoshop_mcp_server.bridge.powershell_backend.PowerShellBridge._run_powershell_script_sync')
    def test_save_file(self, mock_run_script):
        """ファイルを保存する機能のテスト"""
        # モックの設定
        mock_run_script.return_value = 'true'
        
        # テスト実行 - パスを指定
        result = self.bridge.save_file(self.temp_file.name)
        
        # 検証
        result = asyncio.run(result)
        self.assertTrue(result)
        mock_run_script.assert_called_once()
        
        # モックをリセット
        mock_run_script.reset_mock()
        mock_run_script.return_value = 'true'
        
        # テスト実行 - パスを指定しない
        result = self.bridge.save_file()
        
        # 検証
        result = asyncio.run(result)
        self.assertTrue(result)
        mock_run_script.assert_called_once()
        
    @patch('photoshop_mcp_server.bridge.powershell_backend.PowerShellBridge._run_powershell_script_sync')
    def test_get_document_info(self, mock_run_script):
        """ドキュメント情報を取得する機能のテスト"""
        # モックの設定
        mock_run_script.return_value = '{"name": "test.psd", "width": 800, "height": 600, "resolution": 72, "path": "C:\\\\test.psd"}'
        
        # テスト実行
        result = self.bridge.get_document_info()
        
        # 検証
        result = asyncio.run(result)
        self.assertEqual(result["name"], "test.psd")
        self.assertEqual(result["width"], 800)
        self.assertEqual(result["height"], 600)
        self.assertEqual(result["resolution"], 72)
        self.assertEqual(result["path"], "C:\\test.psd")
        mock_run_script.assert_called_once()
        
    @patch('photoshop_mcp_server.bridge.powershell_backend.PowerShellBridge._run_powershell_script_sync')
    def test_export_layer(self, mock_run_script):
        """レイヤーをエクスポートする機能のテスト"""
        # モックの設定
        mock_run_script.return_value = '{"status": "success", "message": "Layer exported successfully", "path": "C:\\\\test_layer.jpg", "format": "jpeg"}'
        
        # テスト実行
        result = self.bridge.export_layer("layer1", "C:\\test_layer.jpg")
        
        # 検証
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], "Layer exported successfully")
        self.assertEqual(result["path"], "C:\\test_layer.jpg")
        self.assertEqual(result["format"], "jpeg")
        mock_run_script.assert_called_once()
        
    @patch('photoshop_mcp_server.bridge.powershell_backend.PowerShellBridge._run_powershell_script_sync')
    def test_run_action(self, mock_run_script):
        """アクションを実行する機能のテスト"""
        # モックの設定
        mock_run_script.return_value = '{"status": "success", "message": "Action executed successfully", "action_set": "TestSet", "action_name": "TestAction"}'
        
        # テスト実行
        result = self.bridge.run_action("TestSet", "TestAction")
        
        # 検証
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], "Action executed successfully")
        self.assertEqual(result["action_set"], "TestSet")
        self.assertEqual(result["action_name"], "TestAction")
        mock_run_script.assert_called_once()
        
    @patch('photoshop_mcp_server.bridge.powershell_backend.PowerShellBridge._run_powershell_script_sync')
    def test_generate_thumbnail(self, mock_run_script):
        """サムネイルを生成する機能のテスト"""
        # モックの設定
        mock_run_script.return_value = '{"status": "success", "thumbnail": "base64data", "width": 256, "height": 256, "format": "jpeg"}'
        
        # テスト実行
        result = self.bridge.generate_thumbnail(self.temp_file.name, 256, 256)
        
        # 検証
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["thumbnail"], "base64data")
        self.assertEqual(result["width"], 256)
        self.assertEqual(result["height"], 256)
        self.assertEqual(result["format"], "jpeg")
        mock_run_script.assert_called_once()
        
    @patch('subprocess.run')
    def test_error_handling(self, mock_run):
        """エラーハンドリングのテスト"""
        # モックの設定 - エラーを発生させる
        mock_run.side_effect = Exception("Test error")
        
        # テスト実行 - 例外が発生することを確認
        with self.assertRaises(RuntimeError):
            self.bridge._run_powershell_script_sync("Test script")
            
        # モックが呼ばれたことを確認
        mock_run.assert_called_once()
        
    @patch('subprocess.run')
    def test_timeout_handling(self, mock_run):
        """タイムアウト処理のテスト"""
        # モックの設定 - タイムアウトを発生させる
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="powershell.exe", timeout=10)
        
        # タイムアウト設定を持つブリッジを作成
        self.bridge.timeout = 10
        
        # テスト実行 - TimeoutErrorが発生することを確認
        with self.assertRaises(TimeoutError):
            self.bridge._run_powershell_script_sync("Test script")
            
        # モックが呼ばれたことを確認
        mock_run.assert_called_once()
        
    @patch('subprocess.run')
    def test_script_cache(self, mock_run):
        """スクリプトキャッシュのテスト"""
        # キャッシュを持つブリッジを作成
        self.bridge._script_cache = {}
        
        # モックの設定
        mock_process = MagicMock()
        mock_process.stdout = '{"status": "success", "message": "Test"}'
        mock_process.returncode = 0
        mock_run.return_value = mock_process
        
        # 1回目の実行
        script = "Test script"
        result1 = self.bridge._run_powershell_script_sync(script)
        
        # 2回目の実行（キャッシュから取得されるはず）
        result2 = self.bridge._run_powershell_script_sync(script)
        
        # 検証
        self.assertEqual(result1, result2)
        # モックは1回だけ呼ばれるはず（2回目はキャッシュから取得）
        mock_run.assert_called_once()
        
if __name__ == '__main__':
    unittest.main()