# インストールガイド

このガイドでは、Photoshop MCP Serverのインストール方法を説明します。

## 共通の手順

### 1. Pythonのインストール

Python 3.11以上が必要です。

- [Python公式サイト](https://www.python.org/downloads/)からダウンロードしてインストール
- インストール時に「Add Python to PATH」オプションを有効にしてください

### 2. Photoshop MCP Serverのインストール

```bash
pip install photoshop-mcp-server
```

または、ソースからインストール：

```bash
git clone https://github.com/StarBoze/photoshop-mcp-server.git
cd photoshop-mcp-server
pip install -e .
```

## macOS固有の設定

### 1. AppleScriptの権限設定

1. システム環境設定 > セキュリティとプライバシー > プライバシー > オートメーション
2. ターミナルまたはVS Codeに「Photoshop」へのアクセスを許可

### 2. py-applescriptのインストール

```bash
pip install py-applescript
```

## Windows固有の設定

### 1. PowerShellの実行ポリシー設定

PowerShellを管理者権限で開き、以下のコマンドを実行：

```powershell
Set-ExecutionPolicy RemoteSigned
```

### 2. pywin32のインストール

```bash
pip install pywin32
```

詳細なWindows環境の設定については[Windows設定ガイド](windows_setup.md)を参照してください。

## UXPプラグインのインストール

UXPバックエンドを使用する場合は、プラグインのインストールが必要です：

1. プラグインをパッケージング
```bash
photoshop-mcp-server package_plugin
```

2. インストール手順を表示
```bash
photoshop-mcp-server install_plugin
```

3. 表示された手順に従ってプラグインをインストール

## 動作確認

インストールが完了したら、以下のコマンドでサーバーを起動し、動作確認を行います：

```bash
# macOSの場合（AppleScriptバックエンド）
photoshop-mcp-server start --bridge-mode applescript

# Windowsの場合（PowerShellバックエンド）
photoshop-mcp-server start --bridge-mode powershell

# UXPバックエンドを使用する場合（クロスプラットフォーム）
photoshop-mcp-server start --bridge-mode uxp
```

サーバーが正常に起動すると、以下のようなメッセージが表示されます：

```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:5001 (Press CTRL+C to quit)
```

## トラブルシューティング

### 一般的な問題

- **依存関係のエラー**: 必要なパッケージがインストールされていない場合は、以下のコマンドを実行してください：
  ```bash
  pip install -r requirements.txt
  ```

- **ポートの競合**: デフォルトポート（5001）が既に使用されている場合は、別のポートを指定してください：
  ```bash
  photoshop-mcp-server start --port 5002
  ```

### macOS固有の問題

- **AppleScriptの権限エラー**: Photoshopの制御に失敗する場合は、システム環境設定でAppleScriptの権限を確認してください。

- **Photoshopが応答しない**: Photoshopを再起動し、最新バージョンを使用していることを確認してください。

### Windows固有の問題

- **PowerShellの実行ポリシーエラー**: スクリプトの実行が許可されていない場合は、PowerShellの実行ポリシーを変更してください。

- **COMオブジェクトの作成エラー**: Photoshopが起動していることを確認し、管理者権限でPowerShellを実行してください。

詳細なトラブルシューティングについては、[Windows設定ガイド](windows_setup.md)を参照してください。

## 次のステップ

- [基本的な使用方法](../README.md#使用方法)を確認する
- [APIリファレンス](api_reference.md)を参照する（近日公開予定）
- [チュートリアル](tutorials.md)を試す（近日公開予定）