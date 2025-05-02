from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, BackgroundTasks
from typing import Optional, Dict, List, Set, Any, Callable, Union
import asyncio
import json
import logging
import uuid
import time
from datetime import datetime

from photoshop_mcp_server.bridge import get_bridge
from photoshop_mcp_server.schema import (
    OpenFileRequest, CloseFileRequest, SaveFileRequest,
    ExportLayerRequest, RunActionRequest, ExecuteScriptRequest,
    GetDocumentInfoRequest, StatusResponse, HealthResponse,
    GenerateThumbnailRequest, ThumbnailResponse,
    StreamMessage, ThumbnailStreamRequest,
    AutoRetouchRequest, AutoRetouchResponse,
    JobRequest, JobResponse, JobStatusResponse
)

# LLM自動レタッチモジュールのインポート
from photoshop_mcp_server.llm_retouch import LLMRetouchManager

# クラスターモジュールのインポート
from photoshop_mcp_server.cluster.dispatcher import ClusterDispatcher, DispatcherConfig, Job, JobStatus

# ロガーの設定
logger = logging.getLogger(__name__)

app = FastAPI(title="Photoshop MCP Server", version="2.0.0")

# クラスターディスパッチャーのインスタンス
cluster_dispatcher: Optional[ClusterDispatcher] = None

# WebSocketクライアント管理
ws_clients: Set[WebSocket] = set()
uxp_bridge = None

@app.post("/openFile", response_model=StatusResponse)
async def open_file(body: OpenFileRequest):
    """PSDファイルを開く"""
    bridge = get_bridge(body.bridge_mode)
    ok = await bridge.open_file(body.path)
    if not ok:
        raise HTTPException(status_code=500, detail="Photoshop failed to open file")
    return {"status": "ok"}

@app.post("/closeFile", response_model=StatusResponse)
async def close_file(body: CloseFileRequest):
    """現在開いているファイルを閉じる"""
    bridge = get_bridge(body.bridge_mode)
    ok = await bridge.close_file(body.save_changes)
    if not ok:
        raise HTTPException(status_code=500, detail="Photoshop failed to close file")
    return {"status": "ok"}

@app.post("/saveFile", response_model=StatusResponse)
async def save_file(body: SaveFileRequest):
    """現在開いているファイルを保存する"""
    bridge = get_bridge(body.bridge_mode)
    ok = await bridge.save_file(body.path)
    if not ok:
        raise HTTPException(status_code=500, detail="Photoshop failed to save file")
    return {"status": "ok"}

@app.post("/exportLayer", response_model=StatusResponse)
async def export_layer(body: ExportLayerRequest):
    """指定したレイヤーをエクスポートする"""
    bridge = get_bridge(body.bridge_mode)
    ok = await bridge.export_layer(body.layer, body.dest, body.format)
    if not ok:
        raise HTTPException(status_code=500, detail="Photoshop failed to export layer")
    return {"status": "ok"}

@app.post("/runAction", response_model=StatusResponse)
async def run_action(body: RunActionRequest):
    """Photoshopアクションを実行する"""
    bridge = get_bridge(body.bridge_mode)
    ok = await bridge.run_action(body.set, body.action)
    if not ok:
        raise HTTPException(status_code=500, detail="Photoshop failed to run action")
    return {"status": "ok"}

@app.post("/executeScript")
async def execute_script(body: ExecuteScriptRequest):
    """JavaScriptを実行する"""
    bridge = get_bridge(body.bridge_mode)
    result = await bridge.execute_script(body.script)
    return {"status": "ok", "result": result}

@app.post("/getDocumentInfo")
async def get_document_info(body: GetDocumentInfoRequest):
    """現在のドキュメント情報を取得する"""
    bridge = get_bridge(body.bridge_mode)
    info = await bridge.get_document_info()
    if not info:
        raise HTTPException(status_code=404, detail="No active document")
    return info

@app.post("/generateThumbnail", response_model=ThumbnailResponse)
async def generate_thumbnail(body: GenerateThumbnailRequest):
    """サムネイルを生成する"""
    try:
        bridge = get_bridge(body.bridge_mode)
        result = await bridge.generate_thumbnail(
            path=body.path,
            width=body.width,
            height=body.height,
            format=body.format,
            quality=body.quality
        )
        if not result:
            raise HTTPException(status_code=500, detail="Failed to generate thumbnail")
        return result
    except Exception as e:
        logger.error(f"サムネイル生成エラー: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating thumbnail: {str(e)}")

@app.get("/healthz", response_model=HealthResponse)
async def health_check(bridge_mode: str = "applescript"):
    """サーバーとPhotoshopの状態を確認する"""
    try:
        # 指定されたブリッジモードでPhotoshopが起動しているか確認
        bridge = get_bridge(bridge_mode)
        
        # ドキュメント情報を取得してみる
        doc_info = await bridge.get_document_info()
        
        # UXPプラグインの接続状態を確認
        uxp_connected = False
        if bridge_mode == "uxp":
            uxp_connected = len(ws_clients) > 0
        
        if doc_info:
            return {
                "status": "ok",
                "photoshop_running": True,
                "active_document": doc_info.get("name"),
                "uxp_connected": uxp_connected if bridge_mode == "uxp" else None
            }
        else:
            return {
                "status": "ok",
                "photoshop_running": True,
                "active_document": None,
                "uxp_connected": uxp_connected if bridge_mode == "uxp" else None
            }
    except Exception as e:
        logger.error(f"ヘルスチェックエラー: {e}")
        # エラーが発生した場合はPhotoshopが起動していないと判断
        return {
            "status": "ok",
            "photoshop_running": False,
            "active_document": None,
            "uxp_connected": False if bridge_mode == "uxp" else None
        }

@app.get("/health")
async def legacy_health_check():
    """レガシーヘルスチェックエンドポイント（互換性のために維持）"""
    return {"status": "ok"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocketエンドポイント"""
    await websocket.accept()
    ws_clients.add(websocket)
    logger.info(f"WebSocket接続: {len(ws_clients)}個のクライアント")
    
    try:
        # 接続確認メッセージを送信
        await websocket.send_json({
            "type": "connection",
            "status": "connected",
            "message": "WebSocketサーバーに接続しました"
        })
        
        # メッセージ処理ループ
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                message_type = message.get("type", "unknown")
                
                if message_type == "ping":
                    # Pingに応答
                    await websocket.send_json({"type": "pong"})
                elif message_type == "command":
                    # Photoshopコマンドを実行
                    command = message.get("command")
                    params = message.get("params", {})
                    
                    # UXPブリッジを使用してコマンドを実行
                    try:
                        bridge = get_bridge("uxp")
                        result = await bridge.execute_script(command)
                        await websocket.send_json({
                            "type": "result",
                            "command": command,
                            "result": result
                        })
                    except Exception as e:
                        logger.error(f"コマンド実行エラー: {e}")
                        await websocket.send_json({
                            "type": "error",
                            "command": command,
                            "error": str(e)
                        })
                else:
                    # 未知のメッセージタイプ
                    await websocket.send_json({
                        "type": "error",
                        "error": f"未知のメッセージタイプ: {message_type}"
                    })
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "error": "無効なJSONフォーマット"
                })
            except Exception as e:
                logger.error(f"WebSocketメッセージ処理エラー: {e}")
                await websocket.send_json({
                    "type": "error",
                    "error": f"メッセージ処理エラー: {str(e)}"
                })
    except WebSocketDisconnect:
        logger.info("WebSocket切断")
    except Exception as e:
        logger.error(f"WebSocketエラー: {e}")
    finally:
        ws_clients.remove(websocket)
        logger.info(f"WebSocket切断: {len(ws_clients)}個のクライアント")

@app.websocket("/generateThumbnail/stream")
async def generate_thumbnail_stream(websocket: WebSocket):
    """サムネイル生成のストリーミングエンドポイント"""
    await websocket.accept()
    logger.info("サムネイル生成ストリーミング接続")
    
    try:
        # クライアントからのリクエストを受信
        data = await websocket.receive_text()
        try:
            request_data = json.loads(data)
            request = ThumbnailStreamRequest(**request_data)
            
            # コールバック関数を定義
            async def send_progress(message: Dict[str, Any]):
                stream_message = StreamMessage(
                    type=message["type"],
                    data=message["data"]
                )
                await websocket.send_json(stream_message.dict())
            
            # ブリッジを取得
            bridge = get_bridge(request.bridge_mode)
            
            # サムネイル生成を開始
            try:
                result = await bridge.generate_thumbnail_stream(
                    path=request.path,
                    width=request.width,
                    height=request.height,
                    format=request.format,
                    quality=request.quality,
                    callback=send_progress
                )
                
                # 最終結果を送信
                await websocket.send_json({
                    "type": "result",
                    "data": result
                })
                
            except Exception as e:
                logger.error(f"サムネイル生成エラー: {e}")
                await websocket.send_json({
                    "type": "error",
                    "data": {
                        "message": f"Error generating thumbnail: {str(e)}"
                    }
                })
                
        except json.JSONDecodeError:
            logger.error(f"JSONパースエラー: {data}")
            await websocket.send_json({
                "type": "error",
                "data": {
                    "message": "Invalid JSON format"
                }
            })
        except Exception as e:
            logger.error(f"リクエスト処理エラー: {e}")
            await websocket.send_json({
                "type": "error",
                "data": {
                    "message": f"Request processing error: {str(e)}"
                }
            })
            
    except WebSocketDisconnect:
        logger.info("サムネイル生成ストリーミング切断")
    except Exception as e:
        logger.error(f"WebSocketエラー: {e}")
    finally:
        logger.info("サムネイル生成ストリーミング終了")

@app.post("/autoRetouch", response_model=AutoRetouchResponse)
async def auto_retouch(body: AutoRetouchRequest):
    """画像を自動レタッチする"""
    try:
        logger.info(f"自動レタッチ開始: {body.path}")
        
        # LLMRetouchManagerを初期化
        retouch_manager = LLMRetouchManager(bridge_mode=body.bridge_mode)
        
        # 自動レタッチを実行
        result = await retouch_manager.auto_retouch(
            image_path=body.path,
            instructions=body.instructions
        )
        
        logger.info(f"自動レタッチ完了: {len(result['retouch_actions'])} アクション")
        return result
        
    except Exception as e:
        logger.error(f"自動レタッチエラー: {e}")
        raise HTTPException(status_code=500, detail=f"Error during auto retouch: {str(e)}")

# クラスターモード関連のエンドポイント
@app.post("/submit_job", response_model=JobResponse)
async def submit_job(job_request: JobRequest):
    """ジョブをクラスターに送信する"""
    if not cluster_dispatcher:
        raise HTTPException(status_code=400, detail="Cluster mode is not enabled")
    
    try:
        # ジョブIDを生成
        job_id = str(uuid.uuid4())
        
        # ジョブペイロードをシリアライズ
        payload = json.dumps(job_request.payload).encode('utf-8')
        
        # ジョブを作成
        job = Job(
            job_id=job_id,
            job_type=job_request.job_type,
            payload=payload,
            priority=job_request.priority,
            callback_url=job_request.callback_url
        )
        
        # ジョブをディスパッチャーに追加
        await cluster_dispatcher.add_job(job)
        
        return {
            "job_id": job_id,
            "status": "queued",
            "message": f"Job {job_id} submitted successfully"
        }
    except Exception as e:
        logger.error(f"ジョブ送信エラー: {e}")
        raise HTTPException(status_code=500, detail=f"Error submitting job: {str(e)}")

@app.get("/job_status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """ジョブのステータスを取得する"""
    if not cluster_dispatcher:
        raise HTTPException(status_code=400, detail="Cluster mode is not enabled")
    
    try:
        # ジョブを取得
        job = await cluster_dispatcher.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        # ジョブステータスを返す
        return {
            "job_id": job.job_id,
            "status": job.status.value,
            "created_at": datetime.fromtimestamp(job.created_at).isoformat(),
            "assigned_at": datetime.fromtimestamp(job.assigned_at).isoformat() if job.assigned_at else None,
            "started_at": datetime.fromtimestamp(job.started_at).isoformat() if job.started_at else None,
            "completed_at": datetime.fromtimestamp(job.completed_at).isoformat() if job.completed_at else None,
            "assigned_node_id": job.assigned_node_id,
            "progress": job.progress,
            "result": job.result,
            "error_message": job.error_message
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ジョブステータス取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting job status: {str(e)}")

@app.get("/cluster_status")
async def get_cluster_status():
    """クラスターの状態を取得する"""
    if not cluster_dispatcher:
        raise HTTPException(status_code=400, detail="Cluster mode is not enabled")
    
    try:
        # クラスターの状態を取得
        nodes = {}
        for node_id, node in cluster_dispatcher.nodes.items():
            nodes[node_id] = node.to_dict()
        
        # ジョブの状態を取得
        jobs = {}
        for job_id, job in cluster_dispatcher.jobs.items():
            jobs[job_id] = {
                "job_id": job.job_id,
                "job_type": job.job_type,
                "status": job.status.value,
                "priority": job.priority,
                "created_at": datetime.fromtimestamp(job.created_at).isoformat(),
                "assigned_node_id": job.assigned_node_id,
                "progress": job.progress
            }
        
        # 統計情報
        stats = {
            "total_nodes": len(cluster_dispatcher.nodes),
            "active_nodes": sum(1 for node in cluster_dispatcher.nodes.values() if node.is_available),
            "total_jobs_processed": cluster_dispatcher.total_jobs_processed,
            "total_jobs_failed": cluster_dispatcher.total_jobs_failed,
            "queued_jobs": len(cluster_dispatcher.job_queue),
            "uptime": time.time() - cluster_dispatcher.start_time
        }
        
        return {
            "cluster_id": cluster_dispatcher.config.cluster_id,
            "routing_strategy": cluster_dispatcher.config.routing_strategy.value,
            "nodes": nodes,
            "jobs": jobs,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"クラスターステータス取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting cluster status: {str(e)}")

@app.post("/cancel_job/{job_id}", response_model=StatusResponse)
async def cancel_job(job_id: str):
    """ジョブをキャンセルする"""
    if not cluster_dispatcher:
        raise HTTPException(status_code=400, detail="Cluster mode is not enabled")
    
    try:
        # ジョブをキャンセル
        success = await cluster_dispatcher.cancel_job(job_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found or already completed")
        
        return {"status": "ok", "message": f"Job {job_id} cancelled successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ジョブキャンセルエラー: {e}")
        raise HTTPException(status_code=500, detail=f"Error cancelling job: {str(e)}")

def init_uxp_bridge():
    """UXPブリッジを初期化"""
    global uxp_bridge
    try:
        uxp_bridge = get_bridge("uxp")
        logger.info("UXPブリッジを初期化しました")
    except Exception as e:
        logger.error(f"UXPブリッジ初期化エラー: {e}")

def start_server(host: str = "127.0.0.1", port: int = 8000, init_uxp: bool = False, cluster_mode: bool = False, cluster_config: Dict[str, Any] = None):
    """サーバーを起動する"""
    import uvicorn
    
    # UXPブリッジを初期化（オプション）
    if init_uxp:
        init_uxp_bridge()
    
    # クラスターモードを初期化（オプション）
    if cluster_mode:
        global cluster_dispatcher
        config = DispatcherConfig(**cluster_config) if cluster_config else DispatcherConfig()
        cluster_dispatcher = ClusterDispatcher(config)
        asyncio.create_task(cluster_dispatcher.start())
        logger.info(f"クラスターモードを有効化しました (ID: {config.cluster_id})")
    
    # サーバー起動
    uvicorn.run(app, host=host, port=port)

def start_cluster_dispatcher(host: str = "0.0.0.0", port: int = 50051, routing_strategy: str = "least_busy", node_timeout: float = 60.0):
    """クラスターディスパッチャーを起動する"""
    from photoshop_mcp_server.cluster.dispatcher import RoutingStrategy
    
    # ルーティング戦略を設定
    strategy_map = {
        "least_busy": RoutingStrategy.LEAST_BUSY,
        "round_robin": RoutingStrategy.ROUND_ROBIN,
        "random": RoutingStrategy.RANDOM,
        "lowest_latency": RoutingStrategy.LOWEST_LATENCY,
        "capability_based": RoutingStrategy.CAPABILITY_BASED
    }
    strategy = strategy_map.get(routing_strategy, RoutingStrategy.LEAST_BUSY)
    
    # ディスパッチャー設定
    config = DispatcherConfig(
        host=host,
        port=port,
        routing_strategy=strategy,
        node_timeout=node_timeout
    )
    
    # ディスパッチャーを起動
    dispatcher = ClusterDispatcher(config)
    
    # イベントループを取得
    loop = asyncio.get_event_loop()
    
    # ディスパッチャーを起動
    loop.run_until_complete(dispatcher.start())
    
    try:
        # イベントループを実行
        loop.run_forever()
    except KeyboardInterrupt:
        # ディスパッチャーを停止
        loop.run_until_complete(dispatcher.stop())
    finally:
        # イベントループを閉じる
        loop.close()

def start_cluster_node(host: str = "0.0.0.0", port: int = 50052, dispatcher_address: str = "localhost:50051", capabilities: List[str] = None, max_concurrent_jobs: int = 5):
    """クラスターノードを起動する"""
    from photoshop_mcp_server.cluster.node import ClusterNode, NodeConfig
    
    # ノード設定
    config = NodeConfig(
        host=host,
        port=port,
        dispatcher_address=dispatcher_address,
        capabilities=capabilities or ["open_file", "save_file", "export_layer", "run_action", "auto_retouch"],
        max_concurrent_jobs=max_concurrent_jobs
    )
    
    # ノードを起動
    node = ClusterNode(config)
    
    # イベントループを取得
    loop = asyncio.get_event_loop()
    
    # ノードを起動
    loop.run_until_complete(node.start())
    
    try:
        # イベントループを実行
        loop.run_forever()
    except KeyboardInterrupt:
        # ノードを停止
        loop.run_until_complete(node.stop())
    finally:
        # イベントループを閉じる
        loop.close()

if __name__ == "__main__":
    start_server()