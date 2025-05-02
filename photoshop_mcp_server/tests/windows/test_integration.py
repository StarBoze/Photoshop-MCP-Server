import unittest
import os
import platform
import tempfile
import time
import logging
from unittest.mock import patch

from photoshop_mcp_server.bridge import get_bridge

@unittest.skipIf(platform.system() != "Windows", "Windows専用のテスト")
class TestWindowsIntegration(unittest.TestCase):
    """Windows環境での統合テスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.bridge = get_bridge("powershell")
        # テスト用の一時ディレクトリ
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_file = os.path.join(self.temp_dir.name, "test.psd")
        
        # ログ設定
        self.logger = logging.getLogger('photoshop_mcp_server.test')
        self.logger.setLevel(logging.DEBUG)
        
        # ファイルハンドラの設定
        log_file = os.path.join(self.temp_dir.name, "test_log.txt")
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
    def tearDown(self):
        """テスト後のクリーンアップ"""
        self.temp_dir.cleanup()
    
    @unittest.skip("Photoshopが必要なため、CI環境ではスキップ")
    async def test_workflow(self):
        """基本的なワークフローのテスト"""
        self.logger.info("ワークフローテスト開始")
        
        try:
            # ファイルを開く
            self.logger.info(f"ファイルを開く: {self.test_file}")
            result = await self.bridge.open_file(self.test_file)
            self.assertTrue(result)
            
            # ドキュメント情報を取得
            self.logger.info("ドキュメント情報を取得")
            info = await self.bridge.get_document_info()
            self.assertIsNotNone(info)
            self.assertEqual(info["name"], os.path.basename(self.test_file))
            
            # ファイルを保存
            save_path = os.path.join(self.temp_dir.name, "saved.psd")
            self.logger.info(f"ファイルを保存: {save_path}")
            result = await self.bridge.save_file(save_path)
            self.assertTrue(result)
            self.assertTrue(os.path.exists(save_path))
            
            # ファイルを閉じる
            self.logger.info("ファイルを閉じる")
            result = await self.bridge.close_file()
            self.assertTrue(result)
            
            self.logger.info("ワークフローテスト完了")
        except Exception as e:
            self.logger.error(f"テスト中にエラーが発生: {e}")
            raise
    
    @unittest.skip("Photoshopが必要なため、CI環境ではスキップ")
    async def test_layer_export(self):
        """レイヤーエクスポートのテスト"""
        self.logger.info("レイヤーエクスポートテスト開始")
        
        try:
            # ファイルを開く
            result = await self.bridge.open_file(self.test_file)
            self.assertTrue(result)
            
            # レイヤーをエクスポート
            export_path = os.path.join(self.temp_dir.name, "layer.jpg")
            self.logger.info(f"レイヤーをエクスポート: {export_path}")
            result = await self.bridge.export_layer_async("Layer 1", export_path)
            self.assertEqual(result["status"], "success")
            self.assertTrue(os.path.exists(export_path))
            
            # ファイルを閉じる
            result = await self.bridge.close_file()
            self.assertTrue(result)
            
            self.logger.info("レイヤーエクスポートテスト完了")
        except Exception as e:
            self.logger.error(f"テスト中にエラーが発生: {e}")
            raise
    
    @unittest.skip("Photoshopが必要なため、CI環境ではスキップ")
    async def test_action_execution(self):
        """アクション実行のテスト"""
        self.logger.info("アクション実行テスト開始")
        
        try:
            # ファイルを開く
            result = await self.bridge.open_file(self.test_file)
            self.assertTrue(result)
            
            # アクションを実行
            self.logger.info("アクションを実行")
            result = await self.bridge.run_action_async("Default Actions", "Vignette (selection)")
            self.assertEqual(result["status"], "success")
            
            # ファイルを閉じる
            result = await self.bridge.close_file()
            self.assertTrue(result)
            
            self.logger.info("アクション実行テスト完了")
        except Exception as e:
            self.logger.error(f"テスト中にエラーが発生: {e}")
            raise
    
    @unittest.skip("Photoshopが必要なため、CI環境ではスキップ")
    async def test_thumbnail_generation(self):
        """サムネイル生成のテスト"""
        self.logger.info("サムネイル生成テスト開始")
        
        try:
            # サムネイルを生成
            self.logger.info(f"サムネイルを生成: {self.test_file}")
            result = await self.bridge.generate_thumbnail_async(self.test_file, 256, 256)
            self.assertEqual(result["status"], "success")
            self.assertIn("thumbnail", result)
            self.assertEqual(result["width"], 256)
            self.assertEqual(result["height"], 256)
            
            self.logger.info("サムネイル生成テスト完了")
        except Exception as e:
            self.logger.error(f"テスト中にエラーが発生: {e}")
            raise
    
    @patch('photoshop_mcp_server.bridge.powershell_backend.PowerShellBridge._run_powershell_script')
    async def test_error_recovery(self, mock_run_script):
        """エラー回復のテスト"""
        self.logger.info("エラー回復テスト開始")
        
        # 最初は成功、2回目は失敗、3回目は成功するようにモックを設定
        mock_results = [
            ('{"status": "success", "message": "Test"}', '', 0),
            ('', 'エラーが発生しました', 1),
            ('{"status": "success", "message": "Recovered"}', '', 0)
        ]
        mock_run_script.side_effect = mock_results
        
        # リトライ機能を持つブリッジを使用
        self.bridge.max_retries = 3
        self.bridge.retry_delay = 0.1
        
        try:
            # 1回目の呼び出し（成功）
            result = await self.bridge.execute_script("test")
            self.assertEqual(result["message"], "Test")
            
            # 2回目の呼び出し（失敗→リトライ→成功）
            result = await self.bridge.execute_script("test")
            self.assertEqual(result["message"], "Recovered")
            
            self.logger.info("エラー回復テスト完了")
        except Exception as e:
            self.logger.error(f"テスト中にエラーが発生: {e}")
            raise
    
    @patch('photoshop_mcp_server.bridge.powershell_backend.PowerShellBridge._run_powershell_script')
    async def test_performance(self, mock_run_script):
        """パフォーマンステスト"""
        self.logger.info("パフォーマンステスト開始")
        
        # モックの設定
        mock_run_script.return_value = ('{"status": "success", "message": "Test"}', '', 0)
        
        # パフォーマンス測定
        start_time = time.time()
        iterations = 100
        
        for i in range(iterations):
            await self.bridge.execute_script(f"test_{i}")
            
        end_time = time.time()
        elapsed = end_time - start_time
        
        # 結果をログに記録
        self.logger.info(f"パフォーマンステスト: {iterations}回の実行に{elapsed:.2f}秒かかりました")
        self.logger.info(f"1回あたりの平均時間: {(elapsed/iterations)*1000:.2f}ミリ秒")
        
        # キャッシュを有効にした場合のテスト
        self.bridge._script_cache = {}
        
        start_time = time.time()
        script = "cached_test"
        
        for i in range(iterations):
            await self.bridge.execute_script(script)
            
        end_time = time.time()
        elapsed_cached = end_time - start_time
        
        # 結果をログに記録
        self.logger.info(f"キャッシュ有効時: {iterations}回の実行に{elapsed_cached:.2f}秒かかりました")
        self.logger.info(f"1回あたりの平均時間: {(elapsed_cached/iterations)*1000:.2f}ミリ秒")
        
        # キャッシュの効果を検証
        self.assertLess(elapsed_cached, elapsed)
        self.logger.info(f"キャッシュによる高速化: {(elapsed - elapsed_cached) / elapsed * 100:.2f}%")
        
        self.logger.info("パフォーマンステスト完了")

if __name__ == '__main__':
    unittest.main()