#!/usr/bin/env python
"""
Claude Desktop + Photoshop MCP Integration

このスクリプトは、Claude DesktopのMCP機能を使用してPhotoshop MCP Serverと連携し、
Photoshopの操作を自動化するサンプルコードです。
"""

import os
import sys
import json
import base64
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Literal

import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PhotoshopMCPClient:
    """
    Claude DesktopからPhotoshop MCP Serverを操作するためのクライアントクラス
    
    このクラスは、Claude DesktopのMCP機能を使用してPhotoshop MCP Serverと連携し、
    Photoshopの操作を自動化するための機能を提供します。
    """
    
    def __init__(
        self,
        server_url: str = "http://localhost:5001",
        timeout: int = 30,
    ):
        """
        PhotoshopMCPClientを初期化します。
        
        Args:
            server_url: Photoshop MCP ServerのURL
            timeout: リクエストのタイムアウト時間（秒）
        """
        self.server_url = server_url
        self.timeout = timeout
        self.api_endpoint = f"{server_url}/api/execute"
        self.headers = {"Content-Type": "application/json"}
        
        # サーバー接続をテスト
        self._test_connection()
        
        logger.info(f"Initialized Photoshop MCP Client with server: {server_url}")
    
    def _test_connection(self) -> None:
        """
        Photoshop MCP Serverへの接続をテストします。
        """
        try:
            response = requests.get(
                f"{self.server_url}/api/status",
                timeout=self.timeout
            )
            response.raise_for_status()
            logger.info("Successfully connected to Photoshop MCP Server")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to Photoshop MCP Server: {e}")
            raise ConnectionError(f"Failed to connect to Photoshop MCP Server: {e}")
    
    def _execute_command(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Photoshop MCP Serverにコマンドを送信して実行します。
        
        Args:
            action: 実行するアクション
            parameters: アクションのパラメータ
            
        Returns:
            サーバーからのレスポンス
        """
        command = {
            "action": action,
            "parameters": parameters
        }
        
        try:
            response = requests.post(
                self.api_endpoint,
                json=command,
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to execute command {action}: {e}")
            raise
    
    def open_document(self, file_path: str) -> Dict[str, Any]:
        """
        Photoshopでドキュメントを開きます。
        
        Args:
            file_path: 開くファイルのパス
            
        Returns:
            サーバーからのレスポンス
        """
        # ファイルの存在確認
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # 絶対パスに変換
        abs_path = os.path.abspath(file_path)
        
        logger.info(f"Opening document: {abs_path}")
        
        return self._execute_command(
            action="open_document",
            parameters={"path": abs_path}
        )
    
    def save_document(
        self,
        file_path: str,
        format: str = "psd",
        quality: int = 90,
        copy: bool = True
    ) -> Dict[str, Any]:
        """
        現在のドキュメントを保存します。
        
        Args:
            file_path: 保存先のファイルパス
            format: ファイル形式（psd, jpg, png, tiff, etc.）
            quality: 保存品質（JPEGの場合）
            copy: コピーとして保存するかどうか
            
        Returns:
            サーバーからのレスポンス
        """
        # 絶対パスに変換
        abs_path = os.path.abspath(file_path)
        
        # 保存先ディレクトリの作成
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        
        logger.info(f"Saving document to: {abs_path} (format: {format})")
        
        return self._execute_command(
            action="save_document",
            parameters={
                "path": abs_path,
                "format": format,
                "quality": quality,
                "copy": copy
            }
        )
    
    def get_document_info(self) -> Dict[str, Any]:
        """
        現在のドキュメントの情報を取得します。
        
        Returns:
            ドキュメント情報
        """
        logger.info("Getting document info")
        
        return self._execute_command(
            action="get_document_info",
            parameters={}
        )
    
    def create_adjustment_layer(
        self,
        layer_type: str,
        name: str,
        settings: Dict[str, Any],
        blend_mode: str = "normal",
        opacity: int = 100,
        mask: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        調整レイヤーを作成します。
        
        Args:
            layer_type: 調整レイヤーの種類
            name: レイヤー名
            settings: 調整レイヤーの設定
            blend_mode: ブレンドモード
            opacity: 不透明度
            mask: マスク設定
            
        Returns:
            サーバーからのレスポンス
        """
        logger.info(f"Creating adjustment layer: {name} (type: {layer_type})")
        
        parameters = {
            "type": layer_type,
            "name": name,
            "settings": settings,
            "blend_mode": blend_mode,
            "opacity": opacity
        }
        
        if mask:
            parameters["mask"] = mask
        
        return self._execute_command(
            action="create_adjustment_layer",
            parameters=parameters
        )
    
    def apply_filter(
        self,
        filter_type: str,
        settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        フィルターを適用します。
        
        Args:
            filter_type: フィルターの種類
            settings: フィルターの設定
            
        Returns:
            サーバーからのレスポンス
        """
        logger.info(f"Applying filter: {filter_type}")
        
        return self._execute_command(
            action="apply_filter",
            parameters={
                "type": filter_type,
                "settings": settings
            }
        )
    
    def get_layer_info(self) -> Dict[str, Any]:
        """
        現在のドキュメントのレイヤー情報を取得します。
        
        Returns:
            レイヤー情報
        """
        logger.info("Getting layer info")
        
        return self._execute_command(
            action="get_layer_info",
            parameters={}
        )
    
    def select_layer(self, layer_id: int) -> Dict[str, Any]:
        """
        レイヤーを選択します。
        
        Args:
            layer_id: レイヤーID
            
        Returns:
            サーバーからのレスポンス
        """
        logger.info(f"Selecting layer: {layer_id}")
        
        return self._execute_command(
            action="select_layer",
            parameters={"id": layer_id}
        )
    
    def create_text_layer(
        self,
        text: str,
        name: str,
        position: Dict[str, int],
        font: str = "Arial",
        size: int = 24,
        color: Dict[str, int] = {"r": 0, "g": 0, "b": 0}
    ) -> Dict[str, Any]:
        """
        テキストレイヤーを作成します。
        
        Args:
            text: テキスト内容
            name: レイヤー名
            position: テキストの位置 {"x": x, "y": y}
            font: フォント名
            size: フォントサイズ
            color: テキストの色 {"r": r, "g": g, "b": b}
            
        Returns:
            サーバーからのレスポンス
        """
        logger.info(f"Creating text layer: {name} (text: {text})")
        
        return self._execute_command(
            action="create_text_layer",
            parameters={
                "text": text,
                "name": name,
                "position": position,
                "font": font,
                "size": size,
                "color": color
            }
        )


class ClaudeDesktopMCPClient:
    """
    Claude DesktopのMCP機能を使用するためのクライアントクラス
    
    このクラスは、Claude DesktopのMCP機能を使用して外部サービスと連携するための
    機能を提供します。実際のClaude Desktop環境では、このクラスは自動的に提供されます。
    このサンプルコードでは、Claude DesktopのMCP機能をシミュレートしています。
    """
    
    def __init__(
        self,
        server_name: str = "photoshop-mcp",
        server_url: str = "http://localhost:5001"
    ):
        """
        ClaudeDesktopMCPClientを初期化します。
        
        Args:
            server_name: MCPサーバー名
            server_url: MCPサーバーのURL
        """
        self.server_name = server_name
        self.server_url = server_url
        self.photoshop_client = PhotoshopMCPClient(server_url=server_url)
        
        logger.info(f"Initialized Claude Desktop MCP Client with server: {server_name}")
    
    def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        MCPツールを実行します。
        
        Args:
            tool_name: ツール名
            **kwargs: ツールのパラメータ
            
        Returns:
            ツールの実行結果
        """
        logger.info(f"Executing tool: {tool_name} with parameters: {kwargs}")
        
        # PhotoshopMCPClientのメソッドを呼び出す
        if hasattr(self.photoshop_client, tool_name):
            method = getattr(self.photoshop_client, tool_name)
            return method(**kwargs)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    
    def analyze_image(self, image_path: str, prompt: str) -> Dict[str, Any]:
        """
        画像を分析します。
        
        Args:
            image_path: 画像ファイルのパス
            prompt: 分析プロンプト
            
        Returns:
            分析結果
        """
        # 実際のClaude Desktop環境では、Claude自身が画像分析を行います
        # このサンプルコードでは、シンプルな分析結果を返します
        logger.info(f"Analyzing image: {image_path} with prompt: {prompt}")
        
        # ファイルの存在確認
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        # 画像の基本情報を取得
        image_info = {
            "path": image_path,
            "size": os.path.getsize(image_path),
            "format": os.path.splitext(image_path)[1][1:].lower(),
        }
        
        # シンプルな分析結果を返す
        return {
            "analysis": {
                "description": "This is a sample image analysis result.",
                "image_info": image_info,
                "prompt": prompt,
                "content": "The image appears to be a photograph with various elements.",
                "colors": ["#FF0000", "#00FF00", "#0000FF"],
                "objects": ["person", "building", "sky"],
                "composition": "The composition is balanced with main subject in the center."
            }
        }
    
    def generate_retouch_instructions(
        self,
        image_path: str,
        instructions: str,
        style: str = "natural"
    ) -> Dict[str, Any]:
        """
        レタッチ指示を生成します。
        
        Args:
            image_path: 画像ファイルのパス
            instructions: レタッチ指示
            style: レタッチスタイル
            
        Returns:
            レタッチ指示
        """
        # 実際のClaude Desktop環境では、Claude自身がレタッチ指示を生成します
        # このサンプルコードでは、シンプルなレタッチ指示を返します
        logger.info(f"Generating retouch instructions for: {image_path}")
        logger.info(f"Instructions: {instructions}")
        logger.info(f"Style: {style}")
        
        # ファイルの存在確認
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        # シンプルなレタッチ指示を返す
        return {
            "retouch_steps": [
                {
                    "step": 1,
                    "action": "create_adjustment_layer",
                    "parameters": {
                        "type": "brightness_contrast",
                        "name": "Brightness/Contrast 1",
                        "settings": {
                            "brightness": 10,
                            "contrast": 15
                        },
                        "blend_mode": "normal",
                        "opacity": 100,
                        "mask": None
                    },
                    "description": "Increase brightness and contrast slightly to enhance overall appearance"
                },
                {
                    "step": 2,
                    "action": "create_adjustment_layer",
                    "parameters": {
                        "type": "vibrance",
                        "name": "Vibrance 1",
                        "settings": {
                            "vibrance": 20,
                            "saturation": 5
                        },
                        "blend_mode": "normal",
                        "opacity": 100,
                        "mask": None
                    },
                    "description": "Add vibrance to make colors more vivid while preserving skin tones"
                },
                {
                    "step": 3,
                    "action": "create_adjustment_layer",
                    "parameters": {
                        "type": "curves",
                        "name": "Curves 1",
                        "settings": {
                            "curve_points": {
                                "rgb": [[0, 0], [64, 60], [192, 200], [255, 255]]
                            },
                            "channel": "rgb"
                        },
                        "blend_mode": "normal",
                        "opacity": 90,
                        "mask": None
                    },
                    "description": "Apply subtle S-curve to increase contrast while preserving details"
                }
            ]
        }


def apply_retouch_instructions(
    client: PhotoshopMCPClient,
    retouch_instructions: Dict[str, Any]
) -> None:
    """
    レタッチ指示を適用します。
    
    Args:
        client: PhotoshopMCPClientインスタンス
        retouch_instructions: レタッチ指示
    """
    # レタッチ指示の存在確認
    if "retouch_steps" not in retouch_instructions:
        logger.error("Invalid retouch instructions: 'retouch_steps' not found")
        return
    
    # 各ステップを適用
    for step in retouch_instructions["retouch_steps"]:
        logger.info(f"Applying step {step['step']}: {step.get('description', '')}")
        
        # ステップのアクションを確認
        action = step["action"]
        parameters = step["parameters"]
        
        # アクションに応じた処理
        if action == "create_adjustment_layer":
            client.create_adjustment_layer(
                layer_type=parameters["type"],
                name=parameters["name"],
                settings=parameters["settings"],
                blend_mode=parameters["blend_mode"],
                opacity=parameters["opacity"],
                mask=parameters.get("mask")
            )
        elif action == "apply_filter":
            client.apply_filter(
                filter_type=parameters["type"],
                settings=parameters["settings"]
            )
        else:
            logger.warning(f"Unsupported action: {action}")
    
    logger.info("Finished applying retouch instructions")


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description="Claude Desktop + Photoshop MCP Integration")
    parser.add_argument("--server-url", default="http://localhost:5001", help="Photoshop MCP Server URL")
    
    subparsers = parser.add_subparsers(dest="operation", help="Operation to perform")
    
    # open操作のパーサー
    open_parser = subparsers.add_parser("open", help="Open a document")
    open_parser.add_argument("--file", required=True, help="Path to the file to open")
    
    # save操作のパーサー
    save_parser = subparsers.add_parser("save", help="Save the current document")
    save_parser.add_argument("--file", required=True, help="Path to save the file")
    save_parser.add_argument("--format", default="psd", help="File format (psd, jpg, png, etc.)")
    save_parser.add_argument("--quality", type=int, default=90, help="Save quality (for JPEG)")
    save_parser.add_argument("--copy", action="store_true", help="Save as a copy")
    
    # analyze操作のパーサー
    analyze_parser = subparsers.add_parser("analyze", help="Analyze an image")
    analyze_parser.add_argument("--file", required=True, help="Path to the image file")
    analyze_parser.add_argument("--prompt", default="Analyze this image in detail", help="Analysis prompt")
    analyze_parser.add_argument("--output", help="Path to save analysis results")
    
    # retouch操作のパーサー
    retouch_parser = subparsers.add_parser("retouch", help="Generate and apply retouch instructions")
    retouch_parser.add_argument("--file", required=True, help="Path to the image file")
    retouch_parser.add_argument("--instructions", required=True, help="Retouch instructions")
    retouch_parser.add_argument("--style", default="natural", help="Retouch style")
    retouch_parser.add_argument("--output", help="Path to save retouch instructions")
    retouch_parser.add_argument("--apply", action="store_true", help="Apply the retouch instructions")
    
    # apply_filter操作のパーサー
    filter_parser = subparsers.add_parser("apply_filter", help="Apply a filter")
    filter_parser.add_argument("--type", required=True, help="Filter type")
    filter_parser.add_argument("--settings", required=True, help="Filter settings (JSON string)")
    
    args = parser.parse_args()
    
    # サーバーURLの取得
    server_url = args.server_url
    
    try:
        # Claude Desktop MCP Clientの初期化
        claude_client = ClaudeDesktopMCPClient(server_url=server_url)
        
        # 操作に応じた処理
        if args.operation == "open":
            result = claude_client.execute_tool("open_document", file_path=args.file)
            logger.info(f"Document opened: {result}")
        
        elif args.operation == "save":
            result = claude_client.execute_tool(
                "save_document",
                file_path=args.file,
                format=args.format,
                quality=args.quality,
                copy=args.copy
            )
            logger.info(f"Document saved: {result}")
        
        elif args.operation == "analyze":
            result = claude_client.analyze_image(args.file, args.prompt)
            
            if args.output:
                os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
                with open(args.output, "w") as f:
                    json.dump(result, f, indent=2)
                logger.info(f"Analysis results saved to: {args.output}")
            else:
                print(json.dumps(result, indent=2))
        
        elif args.operation == "retouch":
            result = claude_client.generate_retouch_instructions(
                args.file,
                args.instructions,
                args.style
            )
            
            if args.output:
                os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
                with open(args.output, "w") as f:
                    json.dump(result, f, indent=2)
                logger.info(f"Retouch instructions saved to: {args.output}")
            else:
                print(json.dumps(result, indent=2))
            
            if args.apply:
                apply_retouch_instructions(claude_client.photoshop_client, result)
        
        elif args.operation == "apply_filter":
            settings = json.loads(args.settings)
            result = claude_client.execute_tool(
                "apply_filter",
                filter_type=args.type,
                settings=settings
            )
            logger.info(f"Filter applied: {result}")
        
        else:
            parser.print_help()
    
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()