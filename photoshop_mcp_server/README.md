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

### WebSocketエンドポイント

UXPバックエンドを使用する場合、WebSocketエンドポイントも利用可能です：

```
ws://localhost:5001/ws
```

WebSocketを通じて直接JSONメッセージを送受信できます。

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

## ライセンス

MITライセンス

Copyright (C) 2025 StarBoze https://github.com/StarBoze