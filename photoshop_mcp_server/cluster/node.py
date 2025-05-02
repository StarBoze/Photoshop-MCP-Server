"""
Photoshop MCP Server - Cluster Node

このモジュールはPhotoshop MCPサーバーのクラスターノードを実装します。
各ノードは1つのPhotoshopインスタンスを管理し、ディスパッチャーからのジョブを処理します。
"""

import asyncio
import grpc
import logging
import os
import platform
import psutil
import time
import uuid
from concurrent import futures
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union

# gRPCで生成されたコードをインポート（実際の実装時にはprotoからコードを生成後にインポート）
# from .proto import photoshop_pb2, photoshop_pb2_grpc

# Photoshopブリッジをインポート
from ..bridge import applescript_backend, uxp_backend

logger = logging.getLogger(__name__)


@dataclass
class NodeConfig:
    """ノードの設定を保持するデータクラス"""
    node_id: str
    host: str
    port: int
    max_concurrent_jobs: int
    capabilities: List[str]
    dispatcher_address: str
    photoshop_path: Optional[str] = None
    heartbeat_interval: int = 30  # 秒単位


class JobStatus:
    """ジョブのステータスを表す列挙型的クラス"""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Job:
    """ジョブ情報を保持するデータクラス"""
    job_id: str
    job_type: str
    payload: bytes
    priority: int
    status: str = JobStatus.QUEUED
    assigned_time: float = 0.0
    start_time: float = 0.0
    end_time: float = 0.0
    result: Optional[str] = None
    error_message: Optional[str] = None
    progress: int = 0
    callback_url: Optional[str] = None


class ClusterNode:
    """
    Photoshop MCPサーバーのクラスターノード
    
    各ノードは1つのPhotoshopインスタンスを管理し、
    ディスパッチャーからのジョブを処理します。
    """
    
    def __init__(self, config: NodeConfig):
        """
        クラスターノードを初期化
        
        Args:
            config: ノードの設定
        """
        self.config = config
        self.node_id = config.node_id or str(uuid.uuid4())
        self.jobs: Dict[str, Job] = {}
        self.active_jobs: Dict[str, Job] = {}
        self.completed_jobs: Dict[str, Job] = {}
        self.failed_jobs: Dict[str, Job] = {}
        
        self.is_running = False
        self.is_registered = False
        self.last_heartbeat = 0.0
        
        # Photoshopバックエンドの選択
        self.backend = self._select_backend()
        
        # gRPCサーバー
        self.server = None
        self.dispatcher_channel = None
        self.dispatcher_stub = None
        
        # 統計情報
        self.start_time = time.time()
        self.total_jobs_processed = 0
        
        logger.info(f"Node {self.node_id} initialized with config: {config}")
    
    def _select_backend(self):
        """
        システムに適したPhotoshopバックエンドを選択
        
        Returns:
            Photoshopバックエンド
        """
        system = platform.system()
        
        if system == "Darwin":  # macOS
            # UXPバックエンドが利用可能かチェック
            try:
                return uxp_backend.UXPBackend()
            except Exception as e:
                logger.warning(f"UXP backend initialization failed: {e}, falling back to AppleScript")
                return applescript_backend.AppleScriptBackend()
        else:
            raise NotImplementedError(f"Unsupported platform: {system}")
    
    async def start(self):
        """ノードを起動し、ディスパッチャーに登録"""
        if self.is_running:
            logger.warning(f"Node {self.node_id} is already running")
            return
        
        # バックエンドの初期化
        try:
            await self.backend.initialize()
            logger.info(f"Backend initialized successfully: {type(self.backend).__name__}")
        except Exception as e:
            logger.error(f"Failed to initialize backend: {e}")
            raise
        
        # gRPCサーバーの起動
        self.server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
        # photoshop_pb2_grpc.add_PhotoshopServiceServicer_to_server(self, self.server)
        server_address = f"{self.config.host}:{self.config.port}"
        self.server.add_insecure_port(server_address)
        await self.server.start()
        logger.info(f"Node server started on {server_address}")
        
        # ディスパッチャーへの接続
        try:
            self.dispatcher_channel = grpc.aio.insecure_channel(self.config.dispatcher_address)
            # self.dispatcher_stub = photoshop_pb2_grpc.ClusterDispatcherServiceStub(self.dispatcher_channel)
            logger.info(f"Connected to dispatcher at {self.config.dispatcher_address}")
        except Exception as e:
            logger.error(f"Failed to connect to dispatcher: {e}")
            await self.server.stop(0)
            raise
        
        # ディスパッチャーへの登録
        await self._register_to_dispatcher()
        
        # ヘルスチェックタスクの開始
        asyncio.create_task(self._heartbeat_task())
        
        # ジョブ処理タスクの開始
        asyncio.create_task(self._job_processor_task())
        
        self.is_running = True
        logger.info(f"Node {self.node_id} started successfully")
    
    async def stop(self):
        """ノードを停止し、ディスパッチャーから登録解除"""
        if not self.is_running:
            logger.warning(f"Node {self.node_id} is not running")
            return
        
        # ディスパッチャーからの登録解除
        if self.is_registered:
            await self._unregister_from_dispatcher()
        
        # 実行中のジョブをキャンセル
        for job_id, job in list(self.active_jobs.items()):
            job.status = JobStatus.CANCELLED
            job.end_time = time.time()
            job.error_message = "Node shutdown"
            self.active_jobs.pop(job_id)
            self.failed_jobs[job_id] = job
        
        # バックエンドの終了処理
        try:
            await self.backend.shutdown()
            logger.info("Backend shutdown successfully")
        except Exception as e:
            logger.error(f"Error during backend shutdown: {e}")
        
        # gRPCサーバーの停止
        if self.server:
            await self.server.stop(0)
            logger.info("gRPC server stopped")
        
        # ディスパッチャーチャネルのクローズ
        if self.dispatcher_channel:
            await self.dispatcher_channel.close()
            logger.info("Dispatcher channel closed")
        
        self.is_running = False
        logger.info(f"Node {self.node_id} stopped successfully")
    
    async def _register_to_dispatcher(self):
        """ディスパッチャーにノードを登録"""
        if not self.dispatcher_stub:
            logger.error("Dispatcher stub not initialized")
            return False
        
        try:
            # request = photoshop_pb2.RegisterNodeRequest(
            #     node_id=self.node_id,
            #     host=self.config.host,
            #     port=self.config.port,
            #     capabilities=self.config.capabilities,
            #     max_concurrent_jobs=self.config.max_concurrent_jobs
            # )
            # response = await self.dispatcher_stub.RegisterNode(request)
            # if response.success:
            #     self.is_registered = True
            #     logger.info(f"Node {self.node_id} registered to dispatcher with cluster ID: {response.cluster_id}")
            #     return True
            # else:
            #     logger.error(f"Failed to register node: {response.error_message}")
            #     return False
            
            # 仮実装（gRPCコード生成前）
            self.is_registered = True
            logger.info(f"Node {self.node_id} registered to dispatcher (mock)")
            return True
        except Exception as e:
            logger.error(f"Error registering node to dispatcher: {e}")
            return False
    
    async def _unregister_from_dispatcher(self):
        """ディスパッチャーからノードの登録を解除"""
        if not self.dispatcher_stub:
            logger.error("Dispatcher stub not initialized")
            return False
        
        try:
            # request = photoshop_pb2.UnregisterNodeRequest(
            #     node_id=self.node_id,
            #     cluster_id="cluster_id"  # 実際の実装ではregister_responseから取得
            # )
            # response = await self.dispatcher_stub.UnregisterNode(request)
            # if response.success:
            #     self.is_registered = False
            #     logger.info(f"Node {self.node_id} unregistered from dispatcher")
            #     return True
            # else:
            #     logger.error(f"Failed to unregister node: {response.error_message}")
            #     return False
            
            # 仮実装（gRPCコード生成前）
            self.is_registered = False
            logger.info(f"Node {self.node_id} unregistered from dispatcher (mock)")
            return True
        except Exception as e:
            logger.error(f"Error unregistering node from dispatcher: {e}")
            return False
    
    async def _heartbeat_task(self):
        """定期的にディスパッチャーにヘルスチェック情報を送信"""
        while self.is_running:
            if self.is_registered:
                await self._send_health_check()
            
            await asyncio.sleep(self.config.heartbeat_interval)
    
    async def _send_health_check(self):
        """ディスパッチャーにヘルスチェック情報を送信"""
        if not self.dispatcher_stub:
            logger.error("Dispatcher stub not initialized")
            return
        
        try:
            # システムリソース使用状況の取得
            process = psutil.Process(os.getpid())
            cpu_usage = process.cpu_percent(interval=1.0) / psutil.cpu_count()
            memory_usage = process.memory_info().rss / (1024 * 1024)  # MB単位
            
            # request = photoshop_pb2.HealthCheckRequest(node_id=self.node_id)
            # response = await self.dispatcher_stub.HealthCheck(request)
            # logger.debug(f"Health check response: {response}")
            
            # 仮実装（gRPCコード生成前）
            self.last_heartbeat = time.time()
            logger.debug(f"Health check sent (mock): CPU: {cpu_usage:.1f}%, Memory: {memory_usage:.1f}MB, Active jobs: {len(self.active_jobs)}")
        except Exception as e:
            logger.error(f"Error sending health check: {e}")
    
    async def _job_processor_task(self):
        """キューに入っているジョブを処理"""
        while self.is_running:
            # 同時実行ジョブ数の制限を確認
            if len(self.active_jobs) >= self.config.max_concurrent_jobs:
                await asyncio.sleep(1.0)
                continue
            
            # キューからジョブを取得（優先度順）
            pending_jobs = [job for job in self.jobs.values() if job.status == JobStatus.QUEUED]
            if not pending_jobs:
                await asyncio.sleep(1.0)
                continue
            
            # 優先度でソート（高い順）
            pending_jobs.sort(key=lambda job: job.priority, reverse=True)
            job = pending_jobs[0]
            
            # ジョブの処理を開始
            job.status = JobStatus.RUNNING
            job.start_time = time.time()
            self.active_jobs[job.job_id] = job
            
            # 非同期でジョブを処理
            asyncio.create_task(self._process_job(job))
            
            await asyncio.sleep(0.1)  # 短い待機で他のタスクに制御を渡す
    
    async def _process_job(self, job: Job):
        """
        ジョブを処理
        
        Args:
            job: 処理するジョブ
        """
        logger.info(f"Processing job {job.job_id} of type {job.job_type}")
        
        try:
            # ジョブタイプに応じた処理
            if job.job_type == "execute_command":
                result = await self._handle_execute_command(job)
            elif job.job_type == "get_document_info":
                result = await self._handle_get_document_info(job)
            elif job.job_type == "export_document":
                result = await self._handle_export_document(job)
            else:
                raise ValueError(f"Unknown job type: {job.job_type}")
            
            # ジョブの完了
            job.status = JobStatus.COMPLETED
            job.end_time = time.time()
            job.result = result
            job.progress = 100
            
            # 統計情報の更新
            self.total_jobs_processed += 1
            
            # アクティブジョブから完了ジョブへ移動
            self.active_jobs.pop(job.job_id)
            self.completed_jobs[job.job_id] = job
            
            logger.info(f"Job {job.job_id} completed successfully")
            
            # コールバックがあれば実行
            if job.callback_url:
                await self._send_job_callback(job)
        
        except Exception as e:
            # ジョブの失敗
            job.status = JobStatus.FAILED
            job.end_time = time.time()
            job.error_message = str(e)
            
            # アクティブジョブから失敗ジョブへ移動
            self.active_jobs.pop(job.job_id)
            self.failed_jobs[job.job_id] = job
            
            logger.error(f"Job {job.job_id} failed: {e}")
            
            # コールバックがあれば実行
            if job.callback_url:
                await self._send_job_callback(job)
    
    async def _handle_execute_command(self, job: Job) -> str:
        """
        コマンド実行ジョブの処理
        
        Args:
            job: 処理するジョブ
        
        Returns:
            コマンド実行結果
        """
        # ペイロードからコマンドとパラメータを取得
        # command_request = photoshop_pb2.CommandRequest()
        # command_request.ParseFromString(job.payload)
        
        # 仮実装（gRPCコード生成前）
        import json
        command_data = json.loads(job.payload.decode('utf-8'))
        command = command_data.get('command', '')
        parameters = command_data.get('parameters', {})
        
        # バックエンドでコマンドを実行
        result = await self.backend.execute_command(command, parameters)
        return json.dumps(result)
    
    async def _handle_get_document_info(self, job: Job) -> str:
        """
        ドキュメント情報取得ジョブの処理
        
        Args:
            job: 処理するジョブ
        
        Returns:
            ドキュメント情報
        """
        # ペイロードからドキュメントIDを取得
        # document_info_request = photoshop_pb2.DocumentInfoRequest()
        # document_info_request.ParseFromString(job.payload)
        
        # 仮実装（gRPCコード生成前）
        import json
        document_data = json.loads(job.payload.decode('utf-8'))
        document_id = document_data.get('document_id', '')
        
        # バックエンドでドキュメント情報を取得
        document_info = await self.backend.get_document_info(document_id)
        return json.dumps(document_info)
    
    async def _handle_export_document(self, job: Job) -> str:
        """
        ドキュメントエクスポートジョブの処理
        
        Args:
            job: 処理するジョブ
        
        Returns:
            エクスポート結果
        """
        # ペイロードからエクスポート設定を取得
        # export_request = photoshop_pb2.ExportRequest()
        # export_request.ParseFromString(job.payload)
        
        # 仮実装（gRPCコード生成前）
        import json
        export_data = json.loads(job.payload.decode('utf-8'))
        document_id = export_data.get('document_id', '')
        format = export_data.get('format', 'jpeg')
        path = export_data.get('path', '')
        quality = export_data.get('quality', 90)
        include_metadata = export_data.get('include_metadata', False)
        
        # バックエンドでドキュメントをエクスポート
        export_result = await self.backend.export_document(
            document_id, format, path, quality, include_metadata
        )
        return json.dumps(export_result)
    
    async def _send_job_callback(self, job: Job):
        """
        ジョブ完了時のコールバックを送信
        
        Args:
            job: コールバックを送信するジョブ
        """
        if not job.callback_url:
            return
        
        try:
            import aiohttp
            
            # コールバックデータの準備
            callback_data = {
                "job_id": job.job_id,
                "status": job.status,
                "result": job.result,
                "error_message": job.error_message,
                "start_time": job.start_time,
                "end_time": job.end_time,
                "node_id": self.node_id
            }
            
            # コールバックの送信
            async with aiohttp.ClientSession() as session:
                async with session.post(job.callback_url, json=callback_data) as response:
                    if response.status >= 200 and response.status < 300:
                        logger.info(f"Callback for job {job.job_id} sent successfully")
                    else:
                        logger.warning(f"Callback for job {job.job_id} failed with status {response.status}")
        
        except Exception as e:
            logger.error(f"Error sending callback for job {job.job_id}: {e}")
    
    # gRPCサービスメソッド（実際の実装時にはphotoshop_pb2_grpcから生成されたクラスを継承）
    
    # async def ExecuteCommand(self, request, context):
    #     """
    #     コマンド実行RPC
    #     """
    #     job_id = request.job_id or str(uuid.uuid4())
    #     job = Job(
    #         job_id=job_id,
    #         job_type="execute_command",
    #         payload=request.SerializeToString(),
    #         priority=1
    #     )
    #     self.jobs[job_id] = job
    #     
    #     # 同期的に処理する場合
    #     await self._process_job(job)
    #     
    #     if job.status == JobStatus.COMPLETED:
    #         return photoshop_pb2.CommandResponse(
    #             success=True,
    #             result=job.result,
    #             status_code=200
    #         )
    #     else:
    #         return photoshop_pb2.CommandResponse(
    #             success=False,
    #             error_message=job.error_message,
    #             status_code=500
    #         )
    # 
    # async def GetDocumentInfo(self, request, context):
    #     """
    #     ドキュメント情報取得RPC
    #     """
    #     job_id = str(uuid.uuid4())
    #     job = Job(
    #         job_id=job_id,
    #         job_type="get_document_info",
    #         payload=request.SerializeToString(),
    #         priority=1
    #     )
    #     self.jobs[job_id] = job
    #     
    #     # 同期的に処理する場合
    #     await self._process_job(job)
    #     
    #     if job.status == JobStatus.COMPLETED:
    #         import json
    #         doc_info = json.loads(job.result)
    #         return photoshop_pb2.DocumentInfoResponse(
    #             success=True,
    #             document_id=doc_info.get("document_id", ""),
    #             name=doc_info.get("name", ""),
    #             width=doc_info.get("width", 0),
    #             height=doc_info.get("height", 0),
    #             color_mode=doc_info.get("color_mode", ""),
    #             resolution=doc_info.get("resolution", 0),
    #             layer_ids=doc_info.get("layer_ids", [])
    #         )
    #     else:
    #         return photoshop_pb2.DocumentInfoResponse(
    #             success=False,
    #             error_message=job.error_message
    #         )
    # 
    # async def HealthCheck(self, request, context):
    #     """
    #     ヘルスチェックRPC
    #     """
    #     process = psutil.Process(os.getpid())
    #     cpu_usage = process.cpu_percent(interval=1.0) / psutil.cpu_count()
    #     memory_usage = process.memory_info().rss / (1024 * 1024 * 1024)  # GB単位
    #     
    #     # Photoshopの状態をチェック
    #     photoshop_status = await self.backend.check_status()
    #     
    #     if photoshop_status.get("running", False):
    #         status = photoshop_pb2.HealthCheckResponse.Status.HEALTHY
    #     else:
    #         status = photoshop_pb2.HealthCheckResponse.Status.UNHEALTHY
    #     
    #     return photoshop_pb2.HealthCheckResponse(
    #         status=status,
    #         message=photoshop_status.get("message", ""),
    #         cpu_usage=cpu_usage,
    #         memory_usage=memory_usage,
    #         active_jobs=len(self.active_jobs),
    #         timestamp=int(time.time())
    #     )
    
    def get_status(self) -> Dict:
        """
        ノードの現在のステータスを取得
        
        Returns:
            ノードのステータス情報
        """
        uptime = time.time() - self.start_time
        
        return {
            "node_id": self.node_id,
            "status": "healthy" if self.is_running else "stopped",
            "uptime": uptime,
            "active_jobs": len(self.active_jobs),
            "completed_jobs": len(self.completed_jobs),
            "failed_jobs": len(self.failed_jobs),
            "total_jobs_processed": self.total_jobs_processed,
            "backend_type": type(self.backend).__name__,
            "last_heartbeat": self.last_heartbeat,
            "is_registered": self.is_registered
        }