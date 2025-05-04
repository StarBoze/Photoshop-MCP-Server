# Claude Desktop + Photoshop MCP 連携ガイド

このガイドでは、Claude DesktopからPhotoshop MCP Serverを操作する方法について説明します。Claude DesktopのMCP（Model Context Protocol）機能を使用して、Photoshopの操作を自動化し、画像編集ワークフローを効率化する方法を学びましょう。

## 概要

Claude DesktopのMCP機能を使用すると、Claudeから外部システムやAPIと連携することができます。このリポジトリでは、Claude DesktopからPhotoshop MCP Serverに接続し、Photoshopの操作を自動化する方法を示します。

主な機能：
- Claude DesktopからPhotoshopを開く・保存する
- 画像分析と自動レタッチ
- 調整レイヤーの作成と編集
- フィルターの適用
- バッチ処理の自動化

## 前提条件

以下のソフトウェアとツールが必要です：

1. **Claude Desktop**
   - 最新バージョンのClaude Desktopがインストールされていること
   - MCPサーバー連携機能が有効になっていること

2. **Adobe Photoshop**
   - Adobe Photoshop 2022以降
   - UXPプラグインがサポートされているバージョン

3. **Photoshop MCP Server**
   - このリポジトリのPhotoshop MCP Serverがインストールされていること
   - 必要な依存関係がインストールされていること

4. **Python環境**
   - Python 3.11以上
   - pipパッケージマネージャー

## セットアップ手順

### 1. Photoshop MCP Serverのインストール

まだインストールしていない場合は、以下のコマンドでPhotoshop MCP Serverをインストールします：

```bash
git clone https://github.com/your-repo/photoshop_mcp_server.git
cd photoshop_mcp_server
pip install -e .
```

### 2. 必要なライブラリのインストール

このサンプルで必要なライブラリをインストールします：

```bash
pip install requests
```

### 3. Photoshop MCP Serverの設定

1. Photoshop MCP Serverを起動します：

```bash
python -m photoshop_mcp_server.server
```

2. Photoshopを起動し、UXPプラグインが正しく読み込まれていることを確認します。

### 4. Claude DesktopのMCP設定

1. Claude Desktopを起動します。
2. 設定メニューから「MCP設定」を開きます。
3. 「新規MCP接続」をクリックします。
4. 以下の情報を入力します：
   - サーバー名: `photoshop-mcp`
   - エンドポイント: `http://localhost:5001`
   - 説明: `Photoshop MCP Server`
5. 「テスト接続」をクリックして接続をテストします。
6. 「保存」をクリックして設定を保存します。

## 使用例

### 基本的な操作方法

Claude Desktopで以下のようなプロンプトを使用して、Photoshopを操作できます：

```
Photoshopで新しい画像を作成し、テキストレイヤーを追加して「Hello World」と表示してください。
```

Claude Desktopは、MCPを通じてPhotoshop MCP Serverに接続し、指示を実行します。

### サンプルコードの実行方法

このリポジトリには、Claude DesktopからPhotoshop MCP Serverを操作するサンプルコードが含まれています。以下のコマンドで実行できます：

```bash
python claude_photoshop_mcp.py --operation open --file path/to/image.jpg
```

利用可能な操作：
- `open`: 画像ファイルを開く
- `save`: 現在の画像を保存する
- `analyze`: 画像を分析する
- `retouch`: 画像を自動レタッチする
- `apply_filter`: フィルターを適用する

詳細なオプションについては、`--help`オプションを使用してください：

```bash
python claude_photoshop_mcp.py --help
```

### カスタマイズ方法

サンプルコードは、自分のニーズに合わせて簡単にカスタマイズできます：

1. 新しい操作を追加する場合は、`PhotoshopMCPClient`クラスに新しいメソッドを追加します。
2. 複雑なワークフローを作成する場合は、複数の操作を組み合わせて新しい関数を作成します。
3. 独自のプロンプトテンプレートを作成して、特定のタスクに最適化することができます。

## トラブルシューティング

### 接続の問題

- Photoshop MCP Serverが実行されていることを確認してください。
- ポート5001が他のアプリケーションで使用されていないことを確認してください。
- ファイアウォールがポート5001への接続を許可していることを確認してください。

### Photoshopの問題

- Photoshopが起動していることを確認してください。
- UXPプラグインが正しく読み込まれていることを確認してください。
- Photoshopを再起動して、プラグインを再読み込みしてみてください。

### Claude Desktopの問題

- Claude DesktopのMCP設定が正しいことを確認してください。
- Claude Desktopを再起動してみてください。
- MCP接続のログを確認して、エラーメッセージを確認してください。

## 詳細情報

- [Photoshop MCP Server ドキュメント](https://github.com/your-repo/photoshop_mcp_server/README.md)
- [Claude Desktop MCP ドキュメント](https://claude.ai/docs/mcp)
- [Adobe UXP プラグイン開発ガイド](https://developer.adobe.com/photoshop/uxp/2022/)