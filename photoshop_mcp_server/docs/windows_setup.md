# Windows設定ガイド

このガイドでは、Windows環境でPhotoshop MCP Serverを使用するための詳細な設定手順を説明します。

## 前提条件

- Windows 10/11
- Python 3.11以上
- Adobe Photoshop 2023以上

## 1. PowerShellの設定

### 実行ポリシーの変更

PowerShellスクリプトを実行するには、実行ポリシーを変更する必要があります：

1. PowerShellを管理者権限で開く
2. 以下のコマンドを実行：
   ```powershell
   Set-ExecutionPolicy RemoteSigned
   ```
3. 「Y」を入力して確定

### スクリプト実行の確認

以下のコマンドを実行して、スクリプトが実行できることを確認：

```powershell
Write-Output "Hello, World!"
```

## 2. Photoshopの設定

### COMオートメーションの有効化

1. Photoshopを起動
2. 編集 > 環境設定 > プラグイン
3. 「レガシースクリプトの実行を許可」にチェック
4. Photoshopを再起動

### セキュリティ設定

1. Windows セキュリティ > アプリとブラウザーコントロール
2. 「スマートスクリーン」の設定を確認
3. 必要に応じて、PowerShellスクリプトの実行を許可

## 3. 依存関係のインストール

### pywin32のインストール

```bash
pip install pywin32
```

### その他の依存関係

```bash
pip install -r requirements.txt
```

## 4. サーバーの起動

### PowerShellバックエンドの使用

```bash
photoshop-mcp-server start --bridge-mode powershell
```

### UXPバックエンドの使用

```bash
photoshop-mcp-server start --bridge-mode uxp
```

## 5. パス形式の注意点

Windows環境では、ファイルパスのバックスラッシュ（\）をエスケープするか、フォワードスラッシュ（/）を使用してください：

```json
// 正しいパス形式の例
{
  "path": "C:/Users/username/Documents/file.psd"
}

// または
{
  "path": "C:\\Users\\username\\Documents\\file.psd"
}
```

## トラブルシューティング

### COMオブジェクトの作成エラー

エラーメッセージ: `COMオブジェクト 'Photoshop.Application' を作成できません`

解決策:
1. Photoshopが起動していることを確認
2. 管理者権限でPowerShellを実行
3. Photoshopのバージョンが2023以上であることを確認

### スクリプト実行エラー

エラーメッセージ: `このシステムではスクリプトの実行が無効になっています`

解決策:
1. PowerShellを管理者権限で開く
2. `Set-ExecutionPolicy RemoteSigned` を実行
3. 「Y」を入力して確定

### パス関連のエラー

エラーメッセージ: `指定されたパスが見つかりません`

解決策:
1. パスがWindows形式で正しく指定されていることを確認
2. バックスラッシュ（\）をエスケープするか、フォワードスラッシュ（/）を使用

### Photoshopとの通信エラー

エラーメッセージ: `Photoshopとの通信に失敗しました`

解決策:
1. Photoshopが起動していることを確認
2. Photoshopを再起動
3. COMオートメーションが有効になっていることを確認
4. 管理者権限でサーバーを実行

### UXPプラグインの接続エラー

エラーメッセージ: `UXPプラグインに接続できません`

解決策:
1. プラグインが正しくインストールされていることを確認
2. Photoshopを再起動
3. プラグインを再インストール
   ```bash
   photoshop-mcp-server package_plugin
   photoshop-mcp-server install_plugin
   ```

## 詳細なログの有効化

問題の診断には、詳細なログを有効にすると役立ちます：

```bash
photoshop-mcp-server start --bridge-mode powershell --log-level debug
```

ログは以下の場所に保存されます：
```
%USERPROFILE%\.photoshop-mcp-server\logs\
```

## Windows固有の機能

### レジストリ設定の自動化

Photoshop MCP Serverは、必要なレジストリ設定を自動的に構成できます：

```bash
photoshop-mcp-server setup_windows
```

このコマンドは以下の設定を行います：
- PowerShellの実行ポリシーの設定
- Photoshop COMオートメーションの有効化
- 必要なセキュリティ例外の追加

### バッチ処理の最適化

Windows環境では、バッチ処理のパフォーマンスを最適化するための設定があります：

```bash
photoshop-mcp-server start --bridge-mode powershell --win-optimize-batch
```

この設定により、複数のファイルを処理する際のパフォーマンスが向上します。

## 高度な設定

### サービスとしてのインストール

Windows環境では、Photoshop MCP Serverをサービスとしてインストールすることができます：

```bash
photoshop-mcp-server install_service
```

これにより、システム起動時に自動的にサーバーが起動します。

### ファイアウォール設定

外部からアクセスする場合は、Windowsファイアウォールでポートを開放する必要があります：

1. コントロールパネル > システムとセキュリティ > Windows Defender ファイアウォール
2. 「詳細設定」をクリック
3. 「受信の規則」を選択し、「新しい規則」をクリック
4. 「ポート」を選択し、「次へ」をクリック
5. 「TCP」を選択し、「特定のローカルポート」に「5001」を入力
6. 「接続を許可する」を選択し、「次へ」をクリック
7. 適用するネットワークの種類を選択し、「次へ」をクリック
8. 名前と説明を入力し、「完了」をクリック

## 次のステップ

- [基本的な使用方法](../README.md#使用方法)を確認する
- [APIリファレンス](api_reference.md)を参照する（近日公開予定）
- [チュートリアル](tutorials.md)を試す（近日公開予定）