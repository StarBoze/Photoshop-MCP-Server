# LLM Integration Examples

このディレクトリには、`litellm`ライブラリを使用してPhotoshop MCP ServerとLLM（Large Language Models）を連携させる例が含まれています。

## 概要

これらの例では、以下の方法を示しています：

1. 様々なLLMプロバイダー（OpenAI、Anthropic、Google等）と統一的に連携するためのインターフェースの作成
2. ビジョン機能を持つLLMを使用した画像分析
3. 画像分析とユーザー指示に基づくPhotoshopレタッチ指示の生成
4. PSDファイルのレイヤー構造の分析
5. 調整レイヤーを使用した非破壊的なレタッチ指示の生成

## 要件

- Python 3.11+
- litellm
- Photoshop MCP Server

## インストール

```bash
pip install litellm
```

## 設定

適切なAPIキーを環境変数として設定します：

```bash
# OpenAI用
export OPENAI_API_KEY=your_openai_api_key

# Anthropic用
export ANTHROPIC_API_KEY=your_anthropic_api_key

# Google用
export GOOGLE_API_KEY=your_google_api_key

# Azure OpenAI用
export AZURE_OPENAI_API_KEY=your_azure_api_key
export AZURE_API_BASE=your_azure_endpoint
```

## 使用例

### 画像分析

ビジョン機能を持つLLMを使用して画像を分析する：

```bash
python image_analysis.py path/to/image.jpg --provider openai --advanced --output analysis.json
```

オプション：
- `--provider`：使用するLLMプロバイダー（openai、anthropic、google）
- `--model`：使用する特定のモデル（オプション）
- `--advanced`：高度な分析プロンプトを使用する
- `--output`：分析結果を保存するパス（指定しない場合はコンソールに出力）

### レタッチ生成

画像分析とユーザー指示に基づいてPhotoshopレタッチ指示を生成する：

```bash
python retouch_generation.py path/to/image.jpg --instructions "画像を明るくして色を強調する" --style natural --output retouch.json
```

オプション：
- `--instructions`：レタッチのためのユーザー指示
- `--provider`：使用するLLMプロバイダー（openai、anthropic、google）
- `--model`：使用する特定のモデル（オプション）
- `--style`：適用するレタッチスタイル（natural、dramatic、vintage、black_and_white、high_key、low_key）
- `--analysis`：既存の分析JSONへのパス（指定しない場合は画像を分析する）
- `--output`：レタッチ指示を保存するパス（指定しない場合はコンソールに出力）

### レイヤー分析

PSDファイルのレイヤー構造を分析する：

```bash
python adjustment_layer_retouch.py path/to/file.psd --analyze-only --output layer_analysis.json
```

オプション：
- `--analyze-only`：レタッチ指示を生成せずにレイヤーのみを分析する
- `--provider`：使用するLLMプロバイダー（openai、anthropic、google）
- `--model`：使用する特定のモデル（オプション）
- `--output`：レイヤー分析結果を保存するパス（指定しない場合はコンソールに出力）

### 調整レイヤーを使ったレタッチ

調整レイヤーを使用した非破壊的なレタッチ指示を生成して適用する：

```bash
python adjustment_layer_retouch.py path/to/image.psd --instructions "コントラストを強調し、色をより鮮やかにする" --output retouch.json --apply
```

オプション：
- `--instructions`：レタッチのためのユーザー指示
- `--provider`：使用するLLMプロバイダー（openai、anthropic、google）
- `--model`：使用する特定のモデル（オプション）
- `--layer-analysis`：既存のレイヤー分析JSONへのパス（指定しない場合でPSDファイルの場合は、レイヤーを分析する）
- `--output`：レタッチ指示を保存するパス（指定しない場合はコンソールに出力）
- `--apply`：Photoshop MCP Serverを使用して生成されたレタッチ指示を適用する
- `--server-url`：Photoshop MCP ServerのURL（デフォルト：http://localhost:5001）

## Photoshop MCP Serverとの連携

これらの例はPhotoshop MCP Serverと連携してレタッチプロセスを自動化できます：

1. `image_analysis.py`を使用して画像を分析する
2. `retouch_generation.py`を使用してレタッチ指示を生成する
3. Photoshop MCP ServerのAPIを使用して、レタッチ指示を画像に適用する

ワークフロー例：

```python
import json
import requests

# 1. 画像分析
analysis_result = analyze_image("path/to/image.jpg", provider="openai", advanced=True)

# 2. レタッチ指示の生成
retouch_instructions = generate_retouch(
    "path/to/image.jpg",
    instructions="色を強調してより鮮やかにする",
    provider="openai",
    style="natural",
)

# 3. Photoshop MCP Serverを使用してレタッチ指示を適用
for step in retouch_instructions["retouch_steps"]:
    # ステップをMCP Serverコマンドに変換
    command = {
        "action": step["action"],
        "parameters": step["parameters"]
    }
    
    # コマンドをMCP Serverに送信
    response = requests.post(
        "http://localhost:5001/api/execute",
        json=command,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"ステップ {step['step']}: {response.status_code}")

# 4. 結果を保存
save_command = {
    "action": "save_file",
    "parameters": {
        "path": "path/to/output.jpg",
        "format": "jpg",
        "quality": 90
    }
}

response = requests.post(
    "http://localhost:5001/api/execute",
    json=save_command,
    headers={"Content-Type": "application/json"}
)

print(f"保存結果: {response.status_code}")
```

### 非破壊的な調整レイヤーワークフロー

```python
import json
import requests

# 1. PSDレイヤーを分析
layer_analysis = analyze_layers("path/to/image.psd", provider="openai")

# 2. 調整レイヤーレタッチ指示の生成
retouch_instructions = generate_adjustment_layer_retouch(
    "path/to/image.psd",
    instructions="コントラストを強調し、色をより鮮やかにする",
    provider="openai",
    layer_analysis=layer_analysis,
)

# 3. Photoshop MCP Serverを使用して調整レイヤーを適用
for step in retouch_instructions["retouch_steps"]:
    # ステップが調整レイヤーの作成かどうかを確認
    if step["action"] != "create_adjustment_layer":
        continue
    
    # MCP Serverコマンドを準備
    command = {
        "action": "create_adjustment_layer",
        "parameters": step["parameters"]
    }
    
    # コマンドをMCP Serverに送信
    response = requests.post(
        "http://localhost:5001/api/execute",
        json=command,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"ステップ {step['step']}: {response.status_code}")

# 4. レイヤーを保持するためにPSD形式で結果を保存
save_command = {
    "action": "save_file",
    "parameters": {
        "path": "path/to/output.psd",
        "format": "psd"
    }
}

response = requests.post(
    "http://localhost:5001/api/execute",
    json=save_command,
    headers={"Content-Type": "application/json"}
)

print(f"保存結果: {response.status_code}")
```

## 高度な使用法

### カスタムプロンプト

各スクリプト内のテンプレートを変更することで、分析やレタッチのプロンプトをカスタマイズできます。

### 複数のLLMプロバイダー

`LLMClient`クラスは複数のLLMプロバイダーをサポートしており、簡単に切り替えることができます：

```python
# OpenAIを使用
openai_client = LLMClient(provider="openai", model="gpt-4-vision-preview")

# Anthropicを使用
anthropic_client = LLMClient(provider="anthropic", model="claude-3-sonnet-20240229")

# Googleを使用
google_client = LLMClient(provider="google", model="gemini-pro-vision")
```

### エラー処理

例には基本的なエラー処理が含まれていますが、本番環境での使用にはより堅牢なエラー処理を追加することをお勧めします。