import typer
import uvicorn
import platform
import os
import signal
import subprocess
import sys
import time
import requests
import zipfile
import json
import shutil
from pathlib import Path
from typing import Optional, List

app = typer.Typer(help="Photoshop MCP Server for macOS - v2.0 Clusterモードと自動レタッチ機能をサポート")

# 定数
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5001
PLIST_NAME = "com.yourorg.psmcp"
PLIST_PATH_USER = os.path.expanduser(f"~/Library/LaunchAgents/{PLIST_NAME}.plist")
PLIST_PATH_SYSTEM = f"/Library/LaunchDaemons/{PLIST_NAME}.plist"
PID_FILE = "/tmp/photoshop_mcp_server.pid"

# UXP関連の定数
UXP_PLUGIN_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uxp_plugin")
UXP_PLUGIN_DIST_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dist")
UXP_PLUGIN_NAME = "photoshop-mcp"
UXP_PLUGIN_INSTALL_DIR = os.path.expanduser("~/Library/Application Support/Adobe/UXP/Developer/")

@app.callback()
def callback():
    """
    Photoshop MCP Server for macOS
    """
    # macOSでのみ実行可能
    if platform.system() != "Darwin":
        typer.echo("Error: This application is for macOS only")
        raise typer.Exit(code=1)

@app.command()
def start(
    host: str = typer.Option(DEFAULT_HOST, help="Host to bind the server to"),
    port: int = typer.Option(DEFAULT_PORT, help="Port to bind the server to"),
    reload: bool = typer.Option(False, help="Enable auto-reload for development"),
    foreground: bool = typer.Option(False, help="Run in foreground (don't daemonize)"),
    uxp: bool = typer.Option(False, help="Initialize UXP bridge on startup")
):
    """
    Start the Photoshop MCP server
    
    v1.2の新機能:
    - サムネイル生成 (/generateThumbnail)
    - WebSocketストリーミング (/generateThumbnail/stream)
    - 詳細はREADME.mdを参照
    """
    # サーバーが既に起動しているか確認
    if is_server_running(host, port):
        typer.echo(f"Photoshop MCP server is already running at http://{host}:{port}")
        return
    
    if foreground:
        # フォアグラウンドで実行
        typer.echo(f"Starting Photoshop MCP server at http://{host}:{port}")
        
        # UXPブリッジ初期化オプション
        if uxp:
            typer.echo("UXP bridge will be initialized")
            
        # サーバー起動
        from photoshop_mcp_server.server import start_server
        start_server(host=host, port=port, init_uxp=uxp)
    else:
        # バックグラウンドで実行
        typer.echo(f"Starting Photoshop MCP server at http://{host}:{port} in background")
        
        # 現在のスクリプトのパスを取得
        script_path = os.path.abspath(sys.argv[0])
        
        # サブプロセスとして起動
        cmd = [
            sys.executable,
            script_path,
            "start",
            "--host", host,
            "--port", str(port),
            "--foreground"
        ]
        
        # UXPオプションを追加
        if uxp:
            cmd.append("--uxp")
        
        with open("/tmp/photoshop_mcp_server.out", "w") as out, \
             open("/tmp/photoshop_mcp_server.err", "w") as err:
            
            process = subprocess.Popen(
                cmd,
                stdout=out,
                stderr=err,
                start_new_session=True
            )
            
        # PIDファイルに保存
        with open(PID_FILE, "w") as f:
            f.write(str(process.pid))
            
        typer.echo(f"Server started with PID {process.pid}")
        
        # サーバーが起動するまで少し待つ
        time.sleep(2)
        
        # 起動確認
        if is_server_running(host, port):
            typer.echo("Server is running")
        else:
            typer.echo("Warning: Server may not have started correctly")
            typer.echo("Check logs at /tmp/photoshop_mcp_server.out and /tmp/photoshop_mcp_server.err")

# 互換性のために残す
@app.command()
def run(
    host: str = typer.Option(DEFAULT_HOST, help="Host to bind the server to"),
    port: int = typer.Option(DEFAULT_PORT, help="Port to bind the server to"),
    reload: bool = typer.Option(False, help="Enable auto-reload for development")
):
    """
    Run the Photoshop MCP server (alias for 'start --foreground')
    """
    start(host=host, port=port, reload=reload, foreground=True)

@app.command()
def stop():
    """
    Stop the Photoshop MCP server
    """
    # PIDファイルからプロセスIDを取得
    if os.path.exists(PID_FILE):
        with open(PID_FILE, "r") as f:
            try:
                pid = int(f.read().strip())
                # プロセスを終了
                try:
                    os.kill(pid, signal.SIGTERM)
                    typer.echo(f"Sent SIGTERM to process {pid}")
                    
                    # プロセスが終了するまで少し待つ
                    for _ in range(5):
                        try:
                            os.kill(pid, 0)  # プロセスが存在するか確認
                            time.sleep(0.5)
                        except OSError:
                            # プロセスが終了した
                            break
                    else:
                        # 5回試行しても終了しなかった場合
                        typer.echo("Process did not terminate, sending SIGKILL")
                        try:
                            os.kill(pid, signal.SIGKILL)
                        except OSError:
                            pass
                    
                    # PIDファイルを削除
                    os.remove(PID_FILE)
                    typer.echo("Server stopped")
                except OSError as e:
                    if e.errno == 3:  # No such process
                        typer.echo(f"No process with PID {pid} found")
                        os.remove(PID_FILE)
                    else:
                        typer.echo(f"Error stopping server: {e}")
            except ValueError:
                typer.echo("Invalid PID in PID file")
                os.remove(PID_FILE)
    else:
        # launchdで実行されている場合
        if os.path.exists(PLIST_PATH_USER):
            os.system(f"launchctl unload {PLIST_PATH_USER}")
            typer.echo("Stopped launchd service (user)")
        elif os.path.exists(PLIST_PATH_SYSTEM):
            if os.geteuid() != 0:
                typer.echo("Error: Root privileges required to stop system-wide service")
                typer.echo("Please run with sudo")
                raise typer.Exit(code=1)
            os.system(f"launchctl unload {PLIST_PATH_SYSTEM}")
            typer.echo("Stopped launchd service (system)")
        else:
            typer.echo("Server is not running or was not started by this CLI")

@app.command()
def status(
    host: str = typer.Option(DEFAULT_HOST, help="Host to check"),
    port: int = typer.Option(DEFAULT_PORT, help="Port to check")
):
    """
    Check the status of the Photoshop MCP server
    """
    if is_server_running(host, port):
        typer.echo(f"Photoshop MCP server is running at http://{host}:{port}")
        
        # Photoshopの状態を確認
        try:
            response = requests.get(f"http://{host}:{port}/healthz")
            if response.status_code == 200:
                data = response.json()
                if data.get("photoshop_running", False):
                    active_doc = data.get("active_document")
                    if active_doc:
                        typer.echo(f"Photoshop is running with active document: {active_doc}")
                    else:
                        typer.echo("Photoshop is running but no document is open")
                else:
                    typer.echo("Photoshop is not running")
        except requests.RequestException:
            typer.echo("Server is running but health check failed")
    else:
        typer.echo(f"Photoshop MCP server is not running at http://{host}:{port}")
        
        # launchdの状態を確認
        if os.path.exists(PLIST_PATH_USER):
            typer.echo("Launchd service is installed (user)")
        elif os.path.exists(PLIST_PATH_SYSTEM):
            typer.echo("Launchd service is installed (system)")
        else:
            typer.echo("Launchd service is not installed")

@app.command()
def install(
    user: bool = typer.Option(True, help="Install as user agent (~/Library/LaunchAgents)"),
    host: str = typer.Option(DEFAULT_HOST, help="Host to bind the server to"),
    port: int = typer.Option(DEFAULT_PORT, help="Port to bind the server to")
):
    """
    Install as launchd service
    """
    if user:
        plist_dir = os.path.expanduser("~/Library/LaunchAgents")
        plist_path = PLIST_PATH_USER
    else:
        plist_dir = "/Library/LaunchDaemons"
        plist_path = PLIST_PATH_SYSTEM
        # 管理者権限が必要
        if os.geteuid() != 0:
            typer.echo("Error: Root privileges required for system-wide installation")
            typer.echo("Please run with sudo")
            raise typer.Exit(code=1)
    
    # 実行可能ファイルのパスを取得
    executable = sys.executable
    
    # plistファイルの内容
    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{PLIST_NAME}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{executable}</string>
        <string>-m</string>
        <string>photoshop_mcp_server.cli</string>
        <string>start</string>
        <string>--host</string>
        <string>{host}</string>
        <string>--port</string>
        <string>{port}</string>
        <string>--foreground</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/psmcp.out</string>
    <key>StandardErrorPath</key>
    <string>/tmp/psmcp.err</string>
</dict>
</plist>
"""
    
    # plistファイルを作成
    os.makedirs(plist_dir, exist_ok=True)
    with open(plist_path, "w") as f:
        f.write(plist_content)
    
    typer.echo(f"Created launchd plist at {plist_path}")
    
    # サービスを登録
    os.system(f"launchctl load {plist_path}")
    typer.echo("Service registered with launchd")
    typer.echo(f"Photoshop MCP server will start automatically at login on http://{host}:{port}")

@app.command()
def uninstall(
    user: bool = typer.Option(True, help="Uninstall user agent")
):
    """
    Uninstall launchd service
    """
    if user:
        plist_path = PLIST_PATH_USER
    else:
        plist_path = PLIST_PATH_SYSTEM
        # 管理者権限が必要
        if os.geteuid() != 0:
            typer.echo("Error: Root privileges required for system-wide uninstallation")
            typer.echo("Please run with sudo")
            raise typer.Exit(code=1)
    
    # サービスを停止
    os.system(f"launchctl unload {plist_path}")
    
    # plistファイルを削除
    if os.path.exists(plist_path):
        os.remove(plist_path)
        typer.echo(f"Removed launchd plist at {plist_path}")
    else:
        typer.echo(f"No launchd plist found at {plist_path}")

# 互換性のために残す
@app.command()
def install_launchd(
    user: bool = typer.Option(True, help="Install as user agent (~/Library/LaunchAgents)")
):
    """
    Install as launchd service (alias for 'install')
    """
    install(user=user)

# 互換性のために残す
@app.command()
def uninstall_launchd(
    user: bool = typer.Option(True, help="Uninstall user agent")
):
    """
    Uninstall launchd service (alias for 'uninstall')
    """
    uninstall(user=user)

@app.command()
def package_plugin(
    output: str = typer.Option(None, help="出力ZIPファイルのパス（デフォルト: ./dist/photoshop-mcp.zip）"),
    version: str = typer.Option(None, help="プラグインのバージョン（manifest.jsonを更新）")
):
    """
    UXPプラグインをパッケージング
    """
    # 出力ディレクトリの作成
    os.makedirs(UXP_PLUGIN_DIST_DIR, exist_ok=True)
    
    # 出力ファイルパスの設定
    if not output:
        output = os.path.join(UXP_PLUGIN_DIST_DIR, f"{UXP_PLUGIN_NAME}.zip")
    
    # バージョン更新（指定された場合）
    if version:
        manifest_path = os.path.join(UXP_PLUGIN_DIR, "manifest.json")
        try:
            with open(manifest_path, "r") as f:
                manifest = json.load(f)
            
            # バージョン更新
            manifest["version"] = version
            
            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)
                
            typer.echo(f"Updated plugin version to {version} in manifest.json")
        except Exception as e:
            typer.echo(f"Error updating version: {e}")
            raise typer.Exit(code=1)
    
    # ZIPファイル作成
    try:
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zipf:
            # プラグインディレクトリ内のファイルを追加
            for root, _, files in os.walk(UXP_PLUGIN_DIR):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, os.path.dirname(UXP_PLUGIN_DIR))
                    zipf.write(file_path, arcname)
        
        typer.echo(f"Plugin packaged successfully: {output}")
    except Exception as e:
        typer.echo(f"Error packaging plugin: {e}")
        raise typer.Exit(code=1)

@app.command()
def install_plugin():
    """
    UXPプラグインのインストール手順を表示
    """
    # プラグインのパッケージングが必要かチェック
    plugin_zip = os.path.join(UXP_PLUGIN_DIST_DIR, f"{UXP_PLUGIN_NAME}.zip")
    if not os.path.exists(plugin_zip):
        typer.echo("Plugin package not found. Creating package first...")
        package_plugin()
    
    # インストール手順の表示
    typer.echo("\nUXPプラグインのインストール手順:")
    typer.echo("------------------------------")
    typer.echo("1. Adobe UXP Developer Toolをインストール（まだの場合）")
    typer.echo("   https://developer.adobe.com/photoshop/uxp/devtools/")
    typer.echo("")
    typer.echo("2. UXP Developer Toolを起動")
    typer.echo("")
    typer.echo("3. 「Add Plugin」ボタンをクリック")
    typer.echo("")
    typer.echo(f"4. 以下のプラグインパッケージを選択: {plugin_zip}")
    typer.echo("")
    typer.echo("5. プラグインをロード")
    typer.echo("")
    typer.echo("6. Photoshopを起動し、プラグインを有効化")
    typer.echo("   プラグイン > Photoshop MCP")
    typer.echo("")
    typer.echo("7. MCPサーバーをUXPモードで起動:")
    typer.echo(f"   photoshop-mcp-server start --uxp")
    typer.echo("")
    typer.echo("注意: Photoshop CC 2021以上が必要です")

def is_server_running(host, port):
    """サーバーが起動しているかを確認する"""
    try:
        response = requests.get(f"http://{host}:{port}/health", timeout=1)
        return response.status_code == 200
    except requests.RequestException:
        return False

@app.command()
def start_cluster(
    host: str = typer.Option(DEFAULT_HOST, help="Host to bind the dispatcher to"),
    port: int = typer.Option(8001, help="Port to bind the dispatcher to"),
    routing_strategy: str = typer.Option("least_busy", help="Routing strategy (least_busy, round_robin, random, lowest_latency, capability_based)"),
    node_timeout: float = typer.Option(60.0, help="Node timeout in seconds")
):
    """
    クラスターディスパッチャーを起動する
    
    複数のPhotoshopインスタンス（ノード）を管理し、ジョブの分散と負荷分散を行います。
    """
    typer.echo(f"Starting cluster dispatcher on {host}:{port} with {routing_strategy} strategy")
    
    # サーバーが既に起動しているか確認
    if is_server_running(host, port):
        typer.echo(f"A server is already running at http://{host}:{port}")
        return
    
    # ディスパッチャーを起動
    from photoshop_mcp_server.server import start_cluster_dispatcher
    start_cluster_dispatcher(host=host, port=port, routing_strategy=routing_strategy, node_timeout=node_timeout)

@app.command()
def start_node(
    host: str = typer.Option(DEFAULT_HOST, help="Host to bind the node to"),
    port: int = typer.Option(8002, help="Port to bind the node to"),
    dispatcher: str = typer.Option("localhost:8001", help="Dispatcher address (host:port)"),
    max_jobs: int = typer.Option(5, help="Maximum concurrent jobs")
):
    """
    クラスターノードを起動する
    
    ディスパッチャーに接続し、ジョブを実行します。
    """
    typer.echo(f"Starting cluster node on {host}:{port} connecting to dispatcher at {dispatcher}")
    
    # サーバーが既に起動しているか確認
    if is_server_running(host, port):
        typer.echo(f"A server is already running at http://{host}:{port}")
        return
    
    # ノードを起動
    from photoshop_mcp_server.server import start_cluster_node
    
    # デフォルトの機能セット
    capabilities = [
        "open_file", "close_file", "save_file", "export_layer",
        "run_action", "execute_script", "get_document_info",
        "generate_thumbnail", "auto_retouch"
    ]
    
    start_cluster_node(
        host=host,
        port=port,
        dispatcher_address=dispatcher,
        capabilities=capabilities,
        max_concurrent_jobs=max_jobs
    )

@app.command()
def submit_job(
    job_type: str = typer.Argument(..., help="Job type (e.g., open_file, auto_retouch)"),
    payload: str = typer.Argument(..., help="Job payload as JSON string"),
    dispatcher: str = typer.Option("localhost:8001", help="Dispatcher address (host:port)"),
    priority: int = typer.Option(1, help="Job priority (higher number = higher priority)")
):
    """
    ジョブをクラスターに送信する
    
    例:
    photoshop-mcp-server submit_job open_file '{"path": "/path/to/file.psd"}'
    photoshop-mcp-server submit_job auto_retouch '{"path": "/path/to/image.jpg", "instructions": "肌をなめらかにする"}'
    """
    import requests
    import json
    
    try:
        # JSONペイロードをパース
        payload_dict = json.loads(payload)
        
        # リクエストデータを作成
        request_data = {
            "job_type": job_type,
            "payload": payload_dict,
            "priority": priority
        }
        
        # ジョブを送信
        response = requests.post(f"http://{dispatcher}/submit_job", json=request_data)
        
        if response.status_code == 200:
            data = response.json()
            typer.echo(f"Job submitted successfully: {data['job_id']}")
            typer.echo(f"Status: {data['status']}")
        else:
            typer.echo(f"Error: {response.status_code} - {response.text}")
    
    except json.JSONDecodeError:
        typer.echo("Error: Invalid JSON payload")
    except requests.RequestException as e:
        typer.echo(f"Error: Failed to connect to dispatcher: {e}")
    except Exception as e:
        typer.echo(f"Error: {e}")

@app.command()
def job_status(
    job_id: str = typer.Argument(..., help="Job ID"),
    dispatcher: str = typer.Option("localhost:8001", help="Dispatcher address (host:port)")
):
    """
    ジョブのステータスを取得する
    """
    import requests
    
    try:
        # ステータスを取得
        response = requests.get(f"http://{dispatcher}/job_status/{job_id}")
        
        if response.status_code == 200:
            data = response.json()
            typer.echo(f"Job ID: {data['job_id']}")
            typer.echo(f"Status: {data['status']}")
            typer.echo(f"Created: {data['created_at']}")
            
            if data['assigned_at']:
                typer.echo(f"Assigned: {data['assigned_at']}")
            
            if data['started_at']:
                typer.echo(f"Started: {data['started_at']}")
            
            if data['completed_at']:
                typer.echo(f"Completed: {data['completed_at']}")
            
            if data['assigned_node_id']:
                typer.echo(f"Node: {data['assigned_node_id']}")
            
            typer.echo(f"Progress: {data['progress']}%")
            
            if data['error_message']:
                typer.echo(f"Error: {data['error_message']}")
            
            if data['result']:
                typer.echo(f"Result: {data['result']}")
        else:
            typer.echo(f"Error: {response.status_code} - {response.text}")
    
    except requests.RequestException as e:
        typer.echo(f"Error: Failed to connect to dispatcher: {e}")
    except Exception as e:
        typer.echo(f"Error: {e}")

@app.command()
def cluster_status(
    dispatcher: str = typer.Option("localhost:8001", help="Dispatcher address (host:port)")
):
    """
    クラスターの状態を取得する
    """
    import requests
    
    try:
        # クラスターの状態を取得
        response = requests.get(f"http://{dispatcher}/cluster_status")
        
        if response.status_code == 200:
            data = response.json()
            
            typer.echo(f"Cluster ID: {data['cluster_id']}")
            typer.echo(f"Routing Strategy: {data['routing_strategy']}")
            typer.echo(f"Stats:")
            typer.echo(f"  Total Nodes: {data['stats']['total_nodes']}")
            typer.echo(f"  Active Nodes: {data['stats']['active_nodes']}")
            typer.echo(f"  Jobs Processed: {data['stats']['total_jobs_processed']}")
            typer.echo(f"  Jobs Failed: {data['stats']['total_jobs_failed']}")
            typer.echo(f"  Queued Jobs: {data['stats']['queued_jobs']}")
            typer.echo(f"  Uptime: {data['stats']['uptime']:.2f} seconds")
            
            typer.echo("\nNodes:")
            for node_id, node in data['nodes'].items():
                typer.echo(f"  {node_id} ({node['address']}):")
                typer.echo(f"    Status: {node['status']}")
                typer.echo(f"    Active Jobs: {node['active_jobs']}")
                typer.echo(f"    Completed Jobs: {node['completed_jobs']}")
                typer.echo(f"    Load Factor: {node['load_factor']:.2f}")
            
            typer.echo("\nJobs:")
            for job_id, job in data['jobs'].items():
                typer.echo(f"  {job_id}:")
                typer.echo(f"    Type: {job['job_type']}")
                typer.echo(f"    Status: {job['status']}")
                typer.echo(f"    Priority: {job['priority']}")
                typer.echo(f"    Created: {job['created_at']}")
                if job['assigned_node_id']:
                    typer.echo(f"    Node: {job['assigned_node_id']}")
                typer.echo(f"    Progress: {job['progress']}%")
        else:
            typer.echo(f"Error: {response.status_code} - {response.text}")
    
    except requests.RequestException as e:
        typer.echo(f"Error: Failed to connect to dispatcher: {e}")
    except Exception as e:
        typer.echo(f"Error: {e}")

@app.command()
def cancel_job(
    job_id: str = typer.Argument(..., help="Job ID"),
    dispatcher: str = typer.Option("localhost:8001", help="Dispatcher address (host:port)")
):
    """
    ジョブをキャンセルする
    """
    import requests
    
    try:
        # ジョブをキャンセル
        response = requests.post(f"http://{dispatcher}/cancel_job/{job_id}")
        
        if response.status_code == 200:
            data = response.json()
            typer.echo(f"Job cancelled successfully: {job_id}")
            typer.echo(f"Status: {data['status']}")
            if 'message' in data:
                typer.echo(f"Message: {data['message']}")
        else:
            typer.echo(f"Error: {response.status_code} - {response.text}")
    
    except requests.RequestException as e:
        typer.echo(f"Error: Failed to connect to dispatcher: {e}")
    except Exception as e:
        typer.echo(f"Error: {e}")

if __name__ == "__main__":
    app()