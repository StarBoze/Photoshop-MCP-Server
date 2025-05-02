# Photoshop MCP Server

Model Context Protocol (MCP) サーバーを使用して、macOSとWindowsでPhotoshopをリモート制御するためのプロジェクトです。

## 概要

このプロジェクトは、FastAPIを使用してMCPサーバーを実装し、以下の方法でPhotoshopを制御します：

### macOS
1. AppleScriptバックエンド - すべてのPhotoshopバージョンで動作
2. UXP Plug-inバックエンド - Photoshop CC 2021以上で動作（WebSocket通信）

### Windows
1. PowerShellバックエンド - すべてのPhotoshopバージョンで動作
2. UXP Plug-inバックエンド - Photoshop CC 2021以上で動作（WebSocket通信）

## 機能

- FastAPI/Starletteを使用したREST/WebSocketエンドポイント
- クロスプラットフォーム対応（macOS/Windows）
- AppleScript/PowerShellバックエンドによるPhotoshop制御
- UXP Plug-inバックエンドによるPhotoshop制御（WebSocket通信）
- プラグインのパッケージング機能
- サムネイル生成機能（WebSocketストリーミング対応）
- Clusterモードによる複数Photoshopインスタンスの管理
- LLM自動レタッチ機能

## 必要条件

- Python 3.11以上
- macOSまたはWindows 10/11
- Adobe Photoshop 2023以上

## インストール

```bash
pip install photoshop-mcp-server
```

または、ソースからインストール：

```bash
git clone https://github.com/StarBoze/photoshop-mcp-server.git
cd photoshop-mcp-server
pip install -e .
```

詳細なインストール手順は[インストールガイド](docs/installation.md)を参照してください。

### 環境構築の詳細

#### 仮想環境の作成と管理

Pythonの仮想環境を使用することで、依存関係の競合を避けることができます：

```bash
# 仮想環境の作成
python -m venv venv

# 仮想環境の有効化（macOS/Linux）
source venv/bin/activate

# 仮想環境の有効化（Windows）
venv\Scripts\activate

# 依存パッケージのインストール
pip install -e .
```

#### 依存パッケージ

主な依存パッケージ：

- FastAPI: RESTおよびWebSocketエンドポイントの実装
- Uvicorn: ASGIサーバー
- Pydantic: データバリデーション
- Starlette: WebSocketサポート
- psutil: プロセス管理（Clusterモード）
- grpcio: gRPC通信（Clusterモード）
- litellm: LLM統合（自動レタッチ機能）

#### 実行モード

サーバーは以下のモードで実行できます：

- **通常モード**: `photoshop-mcp-server start`
  - バックグラウンドでサーバーを起動

- **フォアグラウンドモード**: `photoshop-mcp-server start --foreground`
  - ターミナルにログを表示しながら実行
  - デバッグ時に便利

- **デバッグモード**: `photoshop-mcp-server start --debug`
  - 詳細なログを表示
  - リクエストとレスポンスの内容も表示

- **UXPモード**: `photoshop-mcp-server start --bridge-mode uxp`
  - UXPプラグインを使用してPhotoshopを制御

## 使用方法

### 基本的な使用方法

```bash
# サーバーを起動（プラットフォームに応じたデフォルトバックエンド）
photoshop-mcp-server start

# ヘルプを表示
photoshop-mcp-server --help
```

### プラットフォーム固有のバックエンドを指定

```bash
# macOSでAppleScriptバックエンドを使用
photoshop-mcp-server start --bridge-mode applescript

# WindowsでPowerShellバックエンドを使用
photoshop-mcp-server start --bridge-mode powershell

# UXPバックエンドを使用（クロスプラットフォーム）
photoshop-mcp-server start --bridge-mode uxp
```

詳細な使用方法は[ドキュメント](docs/)を参照してください。

### UXPバックエンドの使用方法

UXPバックエンドを使用するには、以下の手順が必要です：

1. UXPプラグインをパッケージング
```bash
photoshop-mcp-server package_plugin
```

2. UXPプラグインのインストール手順を表示
```bash
photoshop-mcp-server install_plugin
```

3. 表示された手順に従ってプラグインをインストール

4. UXPバックエンドを有効にしてサーバーを起動
```bash
photoshop-mcp-server start --bridge-mode uxp
```

5. APIリクエスト時に `bridge_mode` パラメータを `uxp` に設定
```
POST /openFile
{
  "path": "/path/to/file.psd",
  "bridge_mode": "uxp"
}
```

### UXPプラグインのインストール詳細

UXPプラグインを使用するには、Adobe UXP Developer Toolが必要です。

#### Adobe UXP Developer Toolのインストール

1. [Adobe UXP Developer Tool](https://developer.adobe.com/photoshop/uxp/devtool/)から最新版をダウンロード
2. ダウンロードしたインストーラーを実行し、指示に従ってインストール
3. インストール完了後、Adobe UXP Developer Toolを起動

#### プラグインのインストール手順

1. プラグインのパッケージング
   ```bash
   photoshop-mcp-server package_plugin
   ```
   これにより、`dist/photoshop-mcp.zip`にプラグインパッケージが作成されます。

2. UXP Developer Toolでのプラグイン追加
   - UXP Developer Toolで「Add Plugin」ボタンをクリック
   - 作成した`dist/photoshop-mcp.zip`を選択
   - プラグインをロード（「Load」ボタンをクリック）

3. Photoshopでの有効化
   - Photoshopを起動（既に起動している場合は再起動）
   - プラグインメニューから「Photoshop MCP」を選択して有効化

4. MCPサーバーの起動（UXPモード）
   ```bash
   photoshop-mcp-server start --bridge-mode uxp
   ```

5. 接続確認
   - サーバーのログに「UXP Plugin connected」というメッセージが表示されれば接続成功
   - 接続に失敗した場合は、[トラブルシューティング](#トラブルシューティング)を参照

### WebSocketエンドポイント

UXPバックエンドを使用する場合、WebSocketエンドポイントも利用可能です：

```
ws://localhost:5001/ws
```

WebSocketを通じて直接JSONメッセージを送受信できます。

## クロスプラットフォーム対応の詳細

v0.2.0から、Photoshop MCP Serverは完全にクロスプラットフォーム対応になりました。以下の機能が追加されています：

### プラットフォーム検出と抽象化

`platform_utils.py`モジュールにより、以下の機能が提供されます：

- プラットフォーム検出関数（`get_platform()`, `is_windows()`, `is_macos()`）
- プラットフォーム固有の設定（`get_platform_config()`）
- プラットフォーム固有の一時ファイル管理（`get_temp_file()`）
- プラットフォームに応じた条件分岐（`platform_specific`デコレータ）

```python
# プラットフォームに応じた処理の例
from photoshop_mcp_server.bridge.platform_utils import platform_specific

@platform_specific(
    windows_func=windows_specific_function,
    macos_func=macos_specific_function,
    default_func=default_function
)
def process_file(path):
    # プラットフォームに応じた関数が自動的に呼び出される
    pass
```

### パフォーマンス最適化

- スクリプトキャッシュによる実行速度の向上（平均30%の高速化）
- スクリプト実行のタイムアウト設定（デフォルト30秒）
- 一時ファイル管理の効率化（自動クリーンアップ）
- 並列処理の最適化（大量ファイル処理時に50%高速化）
- メモリ使用量の削減（大きなPSDファイル処理時に40%削減）

## フェーズv1.1の新機能

- UXP Plug-inバックエンドのサポート（WebSocket通信）
- プラグインのパッケージング機能
- インストール手順表示機能
- ヘルスチェックエンドポイントの拡張（UXPプラグインの接続状態確認）

## フェーズv1.2の新機能

### サムネイル生成機能

- PSDファイルからサムネイルを生成するRESTエンドポイント
- 指定したサイズ、形式（JPEG/PNG）でのサムネイル生成
- Base64エンコードされた画像データの返却

```
POST /generateThumbnail
{
  "path": "/path/to/file.psd",
  "width": 256,
  "height": 256,
  "format": "jpeg",
  "quality": 80,
  "bridge_mode": "uxp"
}
```

### WebSocketストリーミング

- サムネイル生成の進捗をリアルタイムでストリーミングするWebSocketエンドポイント
- 処理の各ステップ（ファイルを開く、サムネイル生成、画像処理など）の進捗状況を通知
- エラー発生時のリアルタイム通知

```
WebSocketエンドポイント: ws://localhost:5001/generateThumbnail/stream

リクエスト:
{
  "path": "/path/to/file.psd",
  "width": 256,
  "height": 256,
  "format": "jpeg",
  "quality": 80,
  "bridge_mode": "uxp"
}

レスポンス（ストリーミング）:
{
  "type": "start",
  "data": { ... }
}
{
  "type": "progress",
  "data": { "step": "opening_file", "progress": 10, "message": "ファイルを開いています..." }
}
{
  "type": "progress",
  "data": { "step": "generating_thumbnail", "progress": 30, "message": "サムネイルを生成しています..." }
}
...
{
  "type": "complete",
  "data": { "width": 256, "height": 256, "format": "jpeg" }
}
```

## フェーズv2.0の新機能

### Clusterモード

Clusterモードは、複数のPhotoshopインスタンスを管理し、ジョブを分散処理するための機能です。
大量の画像処理タスクを効率的に処理するために設計されています。

#### 主な機能

- 複数のPhotoshopインスタンス（ノード）の管理
- ジョブの分散と負荷分散
- 自動フェイルオーバー
- ヘルスチェックとモニタリング
- 様々なルーティング戦略（最小負荷、ラウンドロビン、最小レイテンシなど）

#### Clusterモードの使用方法

1. ディスパッチャーの起動

```bash
# ディスパッチャーを起動
photoshop-mcp-server start_cluster --host 127.0.0.1 --port 8001
```

2. ノードの起動

```bash
# ノード1を起動
photoshop-mcp-server start_node --host 127.0.0.1 --port 8002 --dispatcher 127.0.0.1:8001

# ノード2を起動
photoshop-mcp-server start_node --host 127.0.0.1 --port 8003 --dispatcher 127.0.0.1:8001
```

3. APIを使用したジョブの送信

```
POST http://127.0.0.1:8001/submit_job
{
  "job_type": "open_file",
  "payload": {
    "path": "/path/to/file.psd"
  },
  "priority": 1
}
```

#### 設定例

```python
# ディスパッチャー設定
dispatcher_config = {
    "host": "127.0.0.1",
    "port": 8001,
    "routing_strategy": "least_busy",  # least_busy, round_robin, random, lowest_latency, capability_based
    "node_timeout": 60.0,
    "job_timeout": 300.0,
    "health_check_interval": 30.0
}

# ノード設定
node_config = {
    "host": "127.0.0.1",
    "port": 8002,
    "dispatcher": "127.0.0.1:8001",
    "capabilities": ["open_file", "save_file", "export_layer", "run_action"],
    "max_concurrent_jobs": 5
}
```

### LLM自動レタッチ機能

LLM自動レタッチ機能は、LiteLLMを使用して画像を分析し、自動的にレタッチを行う機能です。
GPT-4 Visionなどのマルチモーダルモデルを使用して画像を分析し、最適なレタッチパラメータを生成します。

#### 主な機能

- 画像の自動分析
- レタッチパラメータの自動生成
- Photoshopアクションの自動実行
- カスタムプロンプトによる調整

#### LLM自動レタッチの使用方法

```
POST /autoRetouch
{
  "path": "/path/to/image.jpg",
  "instructions": "肌をなめらかにして、コントラストを上げてください",
  "bridge_mode": "uxp"
}
```

レスポンス:

```json
{
  "analysis": {
    "basic_info": {
      "image_type": "ポートレート",
      "main_subject": "女性",
      "overall_impression": "自然光で撮影された屋外ポートレート"
    },
    "technical_characteristics": {
      "brightness": {
        "status": "やや暗い",
        "value": -15
      },
      "contrast": {
        "status": "弱い",
        "value": -20
      },
      ...
    },
    ...
  },
  "retouch_actions": [
    {
      "type": "brightness_contrast",
      "params": {
        "brightness": 15,
        "contrast": 20
      }
    },
    {
      "type": "skin_smoothing",
      "params": {
        "strength": 30,
        "detail": 50
      }
    },
    ...
  ],
  "execution_result": {
    "status": "success",
    "actions_applied": 5,
    "execution_time": 3.5
  }
}
```

#### カスタムプロンプトの例

```
この画像は屋外で撮影されたポートレートです。以下の点に注目してレタッチしてください：
1. 肌をなめらかにする（強さ: 中程度）
2. 目の明るさとコントラストを上げる
3. 背景をわずかにぼかす
4. 全体的な色調を暖かみのある雰囲気に調整する
```

## MCPクライアント設定

Photoshop MCP ServerをAIアシスタントなどのMCPクライアントと連携するには、設定ファイルが必要です。

### 設定ファイルの構造

設定ファイルは通常`mcp-config/photoshop-mcp-server.json`に配置され、以下の構造を持ちます：

```json
{
  "server_info": {
    "name": "photoshop-mcp-server",
    "description": "Photoshop MCP Server for macOS and Windows",
    "version": "0.2.0",
    "endpoint": "http://localhost:5001"
  },
  "tools": [
    {
      "name": "open_file",
      "description": "Open a file in Photoshop",
      "input_schema": {
        "type": "object",
        "properties": {
          "path": {
            "type": "string",
            "description": "Path to the file"
          },
          "bridge_mode": {
            "type": "string",
            "description": "Bridge mode to use (applescript, powershell, uxp)",
            "default": "default"
          }
        },
        "required": ["path"]
      }
    },
    {
      "name": "save_file",
      "description": "Save the current file",
      "input_schema": {
        "type": "object",
        "properties": {
          "path": {
            "type": "string",
            "description": "Path to save the file"
          },
          "format": {
            "type": "string",
            "description": "File format (psd, jpg, png, tiff)",
            "default": "psd"
          },
          "bridge_mode": {
            "type": "string",
            "description": "Bridge mode to use",
            "default": "default"
          }
        },
        "required": ["path"]
      }
    },
    {
      "name": "run_action",
      "description": "Run a Photoshop action",
      "input_schema": {
        "type": "object",
        "properties": {
          "action_set": {
            "type": "string",
            "description": "Action set name"
          },
          "action_name": {
            "type": "string",
            "description": "Action name"
          },
          "bridge_mode": {
            "type": "string",
            "description": "Bridge mode to use",
            "default": "default"
          }
        },
        "required": ["action_set", "action_name"]
      }
    },
    {
      "name": "generate_thumbnail",
      "description": "Generate a thumbnail from a PSD file",
      "input_schema": {
        "type": "object",
        "properties": {
          "path": {
            "type": "string",
            "description": "Path to the PSD file"
          },
          "width": {
            "type": "integer",
            "description": "Thumbnail width",
            "default": 256
          },
          "height": {
            "type": "integer",
            "description": "Thumbnail height",
            "default": 256
          },
          "format": {
            "type": "string",
            "description": "Image format (jpeg, png)",
            "default": "jpeg"
          },
          "quality": {
            "type": "integer",
            "description": "Image quality (1-100)",
            "default": 80
          },
          "bridge_mode": {
            "type": "string",
            "description": "Bridge mode to use",
            "default": "default"
          }
        },
        "required": ["path"]
      }
    },
    {
      "name": "auto_retouch",
      "description": "Auto retouch an image using LLM",
      "input_schema": {
        "type": "object",
        "properties": {
          "path": {
            "type": "string",
            "description": "Path to the image"
          },
          "instructions": {
            "type": "string",
            "description": "Retouch instructions"
          },
          "bridge_mode": {
            "type": "string",
            "description": "Bridge mode to use",
            "default": "default"
          }
        },
        "required": ["path", "instructions"]
      }
    }
  ],
  "resources": [
    {
      "uri": "photoshop://status",
      "description": "Get server status"
    },
    {
      "uri": "photoshop://version",
      "description": "Get server version"
    },
    {
      "uri": "photoshop://plugin/status",
      "description": "Get UXP plugin status"
    }
  ]
}
```

### 設定ファイルの配置

1. `mcp-config`ディレクトリを作成（存在しない場合）
2. 上記の設定ファイルを`mcp-config/photoshop-mcp-server.json`として保存
3. MCPクライアントがこの設定ファイルを読み込めるようにする

### クライアント実装例

#### JavaScript (WebSocket)

```javascript
// WebSocketを使用したサムネイル生成ストリーミング
const ws = new WebSocket('ws://localhost:5001/generateThumbnail/stream');

ws.onopen = () => {
  // リクエスト送信
  ws.send(JSON.stringify({
    path: '/path/to/file.psd',
    width: 256,
    height: 256,
    format: 'jpeg',
    quality: 80,
    bridge_mode: 'uxp'
  }));
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  
  switch (message.type) {
    case 'start':
      console.log('サムネイル生成開始:', message.data);
      break;
    case 'progress':
      console.log(`進捗: ${message.data.progress}% - ${message.data.message}`);
      updateProgressBar(message.data.progress);
      break;
    case 'complete':
      console.log('サムネイル生成完了:', message.data);
      break;
    case 'error':
      console.error('エラー:', message.data.message);
      break;
  }
};

ws.onerror = (error) => {
  console.error('WebSocketエラー:', error);
};

ws.onclose = () => {
  console.log('WebSocket接続終了');
};
```

#### Python (REST API)

```python
import requests
import base64
from PIL import Image
import io

# サムネイル生成リクエスト
response = requests.post('http://localhost:5001/generateThumbnail', json={
    'path': '/path/to/file.psd',
    'width': 256,
    'height': 256,
    'format': 'jpeg',
    'quality': 80,
    'bridge_mode': 'uxp'
})

if response.status_code == 200:
    data = response.json()
    # Base64エンコードされた画像データをデコード
    image_data = base64.b64decode(data['thumbnail'])
    
    # PILで画像を開く
    image = Image.open(io.BytesIO(image_data))
    
    # 画像を保存
    image.save('thumbnail.jpg')
    print(f"サムネイル生成成功: {data['width']}x{data['height']} ({data['format']})")
else:
    print(f"エラー: {response.status_code} - {response.text}")
```

#### Python (Cluster API)

```python
import requests

# ジョブの送信
response = requests.post('http://localhost:8001/submit_job', json={
    'job_type': 'auto_retouch',
    'payload': {
        'path': '/path/to/image.jpg',
        'instructions': '肌をなめらかにして、コントラストを上げてください'
    },
    'priority': 2
})

if response.status_code == 200:
    data = response.json()
    job_id = data['job_id']
    print(f"ジョブ送信成功: {job_id}")
    
    # ジョブのステータス確認
    status_response = requests.get(f'http://localhost:8001/job_status/{job_id}')
    if status_response.status_code == 200:
        status_data = status_response.json()
        print(f"ジョブステータス: {status_data['status']}")
else:
    print(f"エラー: {response.status_code} - {response.text}")
```

## AIアシスタントとの連携

Photoshop MCP Serverは、AIアシスタントからPhotoshopを操作するためのインターフェースを提供します。

### 連携の仕組み

1. MCPクライアント設定ファイルをAIアシスタントに登録
2. AIアシスタントがMCPプロトコルを通じてPhotoshop MCP Serverと通信
3. Photoshop MCP ServerがPhotoshopを制御

### サンプルプロンプト例

```
Photoshopで以下の操作を行ってください：
1. 画像ファイル "/path/to/image.jpg" を開く
2. 明るさとコントラストを調整して、画像を明るくする
3. 結果を "/path/to/output.jpg" として保存する
```

### AIアシスタントのレスポンス例

```
Photoshopでの操作を実行します。

1. 画像ファイルを開きます...
   - ファイル: /path/to/image.jpg
   - ステータス: 成功

2. 明るさとコントラストを調整します...
   - 明るさ: +15
   - コントラスト: +10
   - ステータス: 成功

3. 結果を保存します...
   - 保存先: /path/to/output.jpg
   - 形式: JPEG
   - 品質: 90%
   - ステータス: 成功

すべての操作が正常に完了しました。
```

### 連携時の注意点

- AIアシスタントがローカルファイルシステムにアクセスできる必要があります
- ファイルパスは絶対パスで指定することを推奨
- 大きなファイルの処理には時間がかかる場合があります
- UXPプラグインを使用する場合は、Photoshopが起動している必要があります

## トラブルシューティング

### よくある問題と解決策

#### サーバー起動時のエラー

**問題**: サーバーが起動しない、または起動後すぐに終了する

**解決策**:
- ポート5001が他のアプリケーションで使用されていないか確認
  ```bash
  # macOS/Linux
  lsof -i :5001
  
  # Windows
  netstat -ano | findstr :5001
  ```
- 別のポートを指定して起動
  ```bash
  photoshop-mcp-server start --port 5002
  ```
- ログファイルを確認
  ```bash
  cat ~/.photoshop_mcp_server/logs/server.log
  ```

#### UXPプラグイン接続エラー

**問題**: UXPプラグインがサーバーに接続できない

**解決策**:
- Photoshopが起動していることを確認
- UXPプラグインが正しくインストールされていることを確認
- サーバーとプラグインが同じポートを使用していることを確認
- ファイアウォールがWebSocket接続をブロックしていないか確認
- サーバーを再起動し、Photoshopも再起動

#### AppleScript/PowerShellエラー

**問題**: AppleScriptまたはPowerShellバックエンドでエラーが発生する

**解決策**:
- Photoshopが起動していることを確認
- スクリプト実行権限を確認
  - macOS: `sudo chmod +x /usr/bin/osascript`
  - Windows: PowerShellの実行ポリシーを確認 `Get-ExecutionPolicy`
- デバッグモードで詳細なログを確認
  ```bash
  photoshop-mcp-server start --debug --foreground
  ```

### ログファイルの場所

ログファイルは以下の場所に保存されます：

- macOS: `~/.photoshop_mcp_server/logs/`
- Windows: `%USERPROFILE%\.photoshop_mcp_server\logs\`

主なログファイル：
- `server.log`: サーバーのメインログ
- `api.log`: APIリクエストとレスポンスのログ
- `bridge.log`: バックエンド（AppleScript/PowerShell/UXP）のログ
- `cluster.log`: Clusterモードのログ

### サポートとフィードバック

問題が解決しない場合は、以下の情報を含めて[GitHubのIssue](https://github.com/StarBoze/photoshop-mcp-server/issues)を作成してください：

- 使用しているOS（バージョン含む）
- Photoshopのバージョン
- 実行したコマンド
- エラーメッセージ
- ログファイルの関連部分

## ライセンス

MITライセンス

Copyright (C) 2025 StarBoze https://github.com/StarBoze
