"""
Photoshop MCP Server - Cluster Dispatcher

このモジュールはPhotoshop MCPサーバーのクラスターディスパッチャーを実装します。
複数のPhotoshopインスタンス（ノード）を管理し、ジョブの分散と負荷分散を行います。
LiteLLMのルーター機能を参考にした実装です。
"""

import asyncio
import grpc
import heapq
import json
import logging
import random
import time
import uuid
from concurrent import futures
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Union, Any

# gRPCで生成されたコードをインポート（実際の実装時にはprotoからコードを生成後にインポート）
# from .proto import photoshop_pb2, photoshop_pb2_grpc

logger = logging.getLogger(__name__)


class NodeStatus(Enum):
    """ノードのステータスを表す列挙型"""
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class JobStatus(Enum):
    """ジョブのステータスを表す列挙型"""
    QUEUED = "queued"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RoutingStrategy(Enum):
    """ルーティング戦略を表す列挙型"""
    LEAST_BUSY = "least_busy"  # 最も忙しくないノードを選択
    ROUND_ROBIN = "round_robin"  # ラウンドロビン方式
    RANDOM = "random"  # ランダム選択
    LOWEST_LATENCY = "lowest_latency"  # 最も低いレイテンシのノードを選択
    CAPABILITY_BASED = "capability_based"  # 機能ベースの選択


@dataclass
class Node:
    """クラスターノード情報を保持するデータクラス"""
    node_id: str
    host: str
    port: int
    capabilities: List[str]
    max_concurrent_jobs: int
    status: NodeStatus = NodeStatus.UNKNOWN
    active_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    last_heartbeat: float = 0.0
    uptime: float = 0.0
    latency_history: List[float] = field(default_factory=list)
    current_jobs: Set[str] = field(default_factory=set)
    
    @property
    def address(self) -> str:
        """ノードのアドレスを取得"""
        return f"{self.host}:{self.port}"
    
    @property
    def is_available(self) -> bool:
        """ノードが利用可能かどうかを判定"""
        return (self.status == NodeStatus.HEALTHY or 
                self.status == NodeStatus.DEGRADED) and \
               self.active_jobs < self.max_concurrent_jobs
    
    @property
    def load_factor(self) -> float:
        """ノードの負荷係数を計算（0.0-1.0）"""
        if self.max_concurrent_jobs == 0:
            return 1.0
        return self.active_jobs / self.max_concurrent_jobs
    
    @property
    def average_latency(self) -> float:
        """平均レイテンシを計算"""
        if not self.latency_history:
            return float('inf')
        return sum(self.latency_history) / len(self.latency_history)
    
    def update_latency(self, latency: float):
        """レイテンシ履歴を更新（最新の10件を保持）"""
        self.latency_history.append(latency)
        if len(self.latency_history) > 10:
            self.latency_history.pop(0)
    
    def to_dict(self) -> Dict:
        """ノード情報を辞書形式で取得"""
        return {
            "node_id": self.node_id,
            "address": self.address,
            "status": self.status.value,
            "capabilities": self.capabilities,
            "active_jobs": self.active_jobs,
            "completed_jobs": self.completed_jobs,
            "failed_jobs": self.failed_jobs,
            "load_factor": self.load_factor,
            "last_heartbeat": self.last_heartbeat,
            "uptime": self.uptime,
            "average_latency": self.average_latency,
            "current_jobs": list(self.current_jobs)
        }


@dataclass
class Job:
    """ジョブ情報を保持するデータクラス"""
    job_id: str
    job_type: str
    payload: bytes
    priority: int = 0
    status: JobStatus = JobStatus.QUEUED
    created_at: float = field(default_factory=time.time)
    assigned_at: Optional[float] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    assigned_node_id: Optional[str] = None
    result: Optional[str] = None
    error_message: Optional[str] = None
    progress: int = 0
    callback_url: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """ジョブ情報を辞書形式で取得"""
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "priority": self.priority,
            "status": self.status.value,
            "created_at": self.created_at,
            "assigned_at": self.assigned_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "assigned_node_id": self.assigned_node_id,
            "progress": self.progress,
            "error_message": self.error_message,
            "callback_url": self.callback_url
        }


@dataclass
class DispatcherConfig:
    """ディスパッチャーの設定を保持するデータクラス"""
    host: str = "0.0.0.0"
    port: int = 50051
    routing_strategy: RoutingStrategy = RoutingStrategy.LEAST_BUSY
    node_timeout: float = 60.0  # ノードのタイムアウト（秒）
    job_timeout: float = 300.0  # ジョブのタイムアウト（秒）
    health_check_interval: float = 30.0  # ヘルスチェック間隔（秒）
    cleanup_interval: float = 3600.0  # クリーンアップ間隔（秒）
    max_retries: int = 3  # ジョブの最大リトライ回数
    cluster_id: str = field(default_factory=lambda: str(uuid.uuid4()))


class ClusterDispatcher:
    """
    Photoshop MCPサーバーのクラスターディスパッチャー
    
    複数のPhotoshopインスタンス（ノード）を管理し、
    ジョブの分散と負荷分散を行います。
    """
    
    def __init__(self, config: DispatcherConfig = None):
        """
        クラスターディスパッチャーを初期化
        
        Args:
            config: ディスパッチャーの設定
        """
        self.config = config or DispatcherConfig()
        self.nodes: Dict[str, Node] = {}
        self.jobs: Dict[str, Job] = {}
        self.job_queue: List[Tuple[int, float, str]] = []  # (priority, created_at, job_id)
        
        self.is_running = False
        self.server = None
        
        # 統計情報
        self.start_time = time.time()
        self.total_jobs_processed = 0
        self.total_jobs_failed = 0
        
        # ノード選択のラウンドロビンインデックス
        self.round_robin_index = 0
        
        logger.info(f"Dispatcher initialized with cluster ID: {self.config.cluster_id}")
    
    async def start(self):
        """ディスパッチャーを起動"""
        if self.is_running:
            logger.warning("Dispatcher is already running")
            return
        
        # gRPCサーバーの起動
        self.server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
        # photoshop_pb2_grpc.add_ClusterDispatcherServiceServicer_to_server(self, self.server)
        server_address = f"{self.config.host}:{self.config.port}"
        self.server.add_insecure_port(server_address)
        await self.server.start()
        logger.info(f"Dispatcher server started on {server_address}")
        
        # バックグラウンドタスクの開始
        asyncio.create_task(self._health_check_task())
        asyncio.create_task(self._job_dispatcher_task())
        asyncio.create_task(self._cleanup_task())
        
        self.is_running = True
        logger.info("Dispatcher started successfully")
    
    async def stop(self):
        """ディスパッチャーを停止"""
        if not self.is_running:
            logger.warning("Dispatcher is not running")
            return
        
        # 実行中のジョブをキャンセル
        for job_id, job in list(self.jobs.items()):
            if job.status in [JobStatus.QUEUED, JobStatus.ASSIGNED, JobStatus.RUNNING]:
                job.status = JobStatus.CANCELLED
                job.completed_at = time.time()
                job.error_message = "Dispatcher shutdown"
        
        # gRPCサーバーの停止
        if self.server:
            await self.server.stop(0)
            logger.info("gRPC server stopped")
        
        self.is_running = False
        logger.info("Dispatcher stopped successfully")
    
    async def _health_check_task(self):
        """定期的にノードのヘルスチェックを行うタスク"""
        while self.is_running:
            await self._check_node_health()
            await asyncio.sleep(self.config.health_check_interval)
    
    async def _check_node_health(self):
        """全ノードのヘルスチェックを実行"""
        current_time = time.time()
        
        for node_id, node in list(self.nodes.items()):
            # タイムアウトチェック
            if current_time - node.last_heartbeat > self.config.node_timeout:
                if node.status != NodeStatus.UNHEALTHY:
                    logger.warning(f"Node {node_id} timed out, marking as unhealthy")
                    node.status = NodeStatus.UNHEALTHY
                    
                    # 割り当て済みのジョブを再キューイング
                    await self._requeue_node_jobs(node_id)
            
            # ヘルスチェックの実行（実際の実装ではgRPCリクエストを送信）
            if node.status != NodeStatus.UNHEALTHY:
                try:
                    # channel = grpc.aio.insecure_channel(node.address)
                    # stub = photoshop_pb2_grpc.PhotoshopServiceStub(channel)
                    # request = photoshop_pb2.HealthCheckRequest(node_id=node_id)
                    # 
                    # start_time = time.time()
                    # response = await stub.HealthCheck(request)
                    # latency = time.time() - start_time
                    # 
                    # node.update_latency(latency)
                    # node.status = NodeStatus(response.status.name.lower())
                    # node.active_jobs = response.active_jobs
                    # node.last_heartbeat = current_time
                    
                    # 仮実装（gRPCコード生成前）
                    # ランダムなレイテンシとステータスを生成
                    latency = random.uniform(0.01, 0.1)
                    node.update_latency(latency)
                    node.status = random.choices(
                        [NodeStatus.HEALTHY, NodeStatus.DEGRADED, NodeStatus.UNHEALTHY],
                        weights=[0.8, 0.15, 0.05]
                    )[0]
                    node.last_heartbeat = current_time
                    
                    logger.debug(f"Health check for node {node_id}: {node.status.value}, latency: {latency:.3f}s")
                
                except Exception as e:
                    logger.error(f"Health check failed for node {node_id}: {e}")
                    node.status = NodeStatus.UNHEALTHY
                    
                    # 割り当て済みのジョブを再キューイング
                    await self._requeue_node_jobs(node_id)
    
    async def _requeue_node_jobs(self, node_id: str):
        """
        ノードに割り当てられたジョブを再キューイング
        
        Args:
            node_id: 再キューイング対象のノードID
        """
        node = self.nodes.get(node_id)
        if not node:
            return
        
        for job_id in list(node.current_jobs):
            job = self.jobs.get(job_id)
            if not job:
                continue
            
            if job.status in [JobStatus.ASSIGNED, JobStatus.RUNNING]:
                logger.info(f"Requeuing job {job_id} from unhealthy node {node_id}")
                
                # ジョブを再キューイング
                job.status = JobStatus.QUEUED
                job.assigned_node_id = None
                job.assigned_at = None
                job.started_at = None
                
                # キューに追加
                heapq.heappush(self.job_queue, (-job.priority, job.created_at, job.job_id))
    def _select_node(self, job: Job, available_nodes: List[Node]) -> Optional[Node]:
        """
        ルーティング戦略に基づいてノードを選択
        
        Args:
            job: 割り当てるジョブ
            available_nodes: 利用可能なノードのリスト
        
        Returns:
            選択されたノード、または適切なノードがない場合はNone
        """
        if not available_nodes:
            return None
        
        # ジョブタイプに必要な機能を持つノードをフィルタリング
        # 実際の実装ではジョブタイプに応じた機能要件を定義
        # この例では単純化のため、すべてのノードが対象
        
        strategy = self.config.routing_strategy
        
        if strategy == RoutingStrategy.LEAST_BUSY:
            # 最も忙しくないノードを選択
            return min(available_nodes, key=lambda node: node.load_factor)
        
        elif strategy == RoutingStrategy.ROUND_ROBIN:
            # ラウンドロビン方式
            if not available_nodes:
                return None
            
            # 現在のインデックスから開始して利用可能なノードを探す
            start_idx = self.round_robin_index
            for _ in range(len(self.nodes)):
                self.round_robin_index = (self.round_robin_index + 1) % len(self.nodes)
                node_id = list(self.nodes.keys())[self.round_robin_index]
                node = self.nodes.get(node_id)
                
                if node and node in available_nodes:
                    return node
            
            # 見つからなかった場合は最初の利用可能なノードを返す
            return available_nodes[0]
        
        elif strategy == RoutingStrategy.RANDOM:
            # ランダム選択
            return random.choice(available_nodes)
        
        elif strategy == RoutingStrategy.LOWEST_LATENCY:
            # 最も低いレイテンシのノードを選択
            return min(available_nodes, key=lambda node: node.average_latency)
        
        elif strategy == RoutingStrategy.CAPABILITY_BASED:
            # 機能ベースの選択（ジョブタイプに応じた機能を持つノードを選択）
            # 実際の実装ではジョブタイプと機能の対応を定義
            # この例では単純化のため、最も忙しくないノードを選択
            return min(available_nodes, key=lambda node: node.load_factor)
        
        # デフォルトは最も忙しくないノード
        return min(available_nodes, key=lambda node: node.load_factor)
    
    async def _assign_job_to_node(self, job: Job, node: Node):
        """
        ジョブをノードに割り当て
        
        Args:
            job: 割り当てるジョブ
            node: 割り当て先のノード
        """
        job.status = JobStatus.ASSIGNED
        job.assigned_node_id = node.node_id
        job.assigned_at = time.time()
# ノードの状態を更新
        node.active_jobs += 1
        node.current_jobs.add(job.job_id)
        
        logger.info(f"Job {job.job_id} assigned to node {node.node_id}")
        
        try:
            # ノードにジョブを送信（実際の実装ではgRPCリクエストを送信）
            # channel = grpc.aio.insecure_channel(node.address)
            # 
            # if job.job_type == "execute_command":
            #     stub = photoshop_pb2_grpc.PhotoshopServiceStub(channel)
            #     command_request = photoshop_pb2.CommandRequest()
            #     command_request.ParseFromString(job.payload)
            #     command_request.job_id = job.job_id
            #     asyncio.create_task(self._execute_command(stub, command_request, job, node))
            # 
            # elif job.job_type == "get_document_info":
            #     stub = photoshop_pb2_grpc.PhotoshopServiceStub(channel)
            #     doc_info_request = photoshop_pb2.DocumentInfoRequest()
            #     doc_info_request.ParseFromString(job.payload)
            #     asyncio.create_task(self._get_document_info(stub, doc_info_request, job, node))
            # 
            # elif job.job_type == "export_document":
            #     stub = photoshop_pb2_grpc.PhotoshopServiceStub(channel)
            #     export_request = photoshop_pb2.ExportRequest()
            #     export_request.ParseFromString(job.payload)
            #     asyncio.create_task(self._export_document(stub, export_request, job, node))
            
            # 仮実装（gRPCコード生成前）
            # ジョブの実行をシミュレート
            asyncio.create_task(self._simulate_job_execution(job, node))
        
        except Exception as e:
            logger.error(f"Failed to send job {job.job_id} to node {node.node_id}: {e}")
            
            # ジョブを再キューイング
            job.status = JobStatus.QUEUED
            job.assigned_node_id = None
            job.assigned_at = None
            
            # ノードの状態を更新
            node.active_jobs = max(0, node.active_jobs - 1)
            node.current_jobs.remove(job.job_id)
            
            # キューに追加
            heapq.heappush(self.job_queue, (-job.priority, job.created_at, job.job_id))
    
    async def _simulate_job_execution(self, job: Job, node: Node):
        """
        ジョブ実行のシミュレーション（仮実装）
        
        Args:
            job: 実行するジョブ
            node: 実行先のノード
        """
        # ジョブの開始
        job.status = JobStatus.RUNNING
        job.started_at = time.time()
        
        # 実行時間をシミュレート（1〜5秒）
        execution_time = random.uniform(1.0, 5.0)
        await asyncio.sleep(execution_time)
        
        # 成功確率（90%）
        if random.random() < 0.9:
            # ジョブ成功
            job.status = JobStatus.COMPLETED
            job.completed_at = time.time()
            job.progress = 100
            job.result = json.dumps({"success": True, "execution_time": execution_time})
            
            # 統計情報の更新
            self.total_jobs_processed += 1
            node.completed_jobs += 1
        else:
            # ジョブ失敗
            job.status = JobStatus.FAILED
            job.completed_at = time.time()
            job.error_message = "Simulated failure"
            
            # 統計情報の更新
            self.total_jobs_failed += 1
            node.failed_jobs += 1
        
        # ノードの状態を更新
        node.active_jobs = max(0, node.active_jobs - 1)
        node.current_jobs.remove(job.job_id)
        
        logger.info(f"Job {job.job_id} {job.status.value} on node {node.node_id}")
    
    async def _cleanup_task(self):
        """古いジョブとノードをクリーンアップするタスク"""
        while self.is_running:
            await self._cleanup_old_jobs()
            await self._cleanup_unhealthy_nodes()
            await asyncio.sleep(self.config.cleanup_interval)
    
    async def _cleanup_old_jobs(self):
        """完了または失敗したジョブをクリーンアップ"""
        current_time = time.time()
        retention_period = 86400  # 24時間（秒）
        
        for job_id, job in list(self.jobs.items()):
            if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                if job.completed_at and current_time - job.completed_at > retention_period:
                    logger.debug(f"Cleaning up old job {job_id}")
                    self.jobs.pop(job_id, None)
    
    async def _cleanup_unhealthy_nodes(self):
        """長時間不健全なノードをクリーンアップ"""
        current_time = time.time()
        unhealthy_threshold = 3600  # 1時間（秒）
        
        for node_id, node in list(self.nodes.items()):
            if node.status == NodeStatus.UNHEALTHY:
                if current_time - node.last_heartbeat > unhealthy_threshold:
                    logger.info(f"Removing unhealthy node {node_id} that has been down for too long")
                    self.nodes.pop(node_id, None)
    
    # gRPCサービスメソッド（実際の実装時にはphotoshop_pb2_grpcから生成されたクラスを継承）
    
    # async def RegisterNode(self, request, context):
    #     """
    #     ノード登録RPC
    #     """
    #     node_id = request.node_id or str(uuid.uuid4())
    #     
    #     # 既存のノードの場合は更新
    #     if node_id in self.nodes:
    #         logger.info(f"Updating existing node {node_id}")
    #         node = self.nodes[node_id]
    #         node.host = request.host
    #         node.port = request.port
    #         node.capabilities = list(request.capabilities)
    #         node.max_concurrent_jobs = request.max_concurrent_jobs
    #         node.last_heartbeat = time.time()
    #         node.status = NodeStatus.HEALTHY
    #     else:
    #         # 新規ノードの登録
    #         logger.info(f"Registering new node {node_id}")
    #         node = Node(
    #             node_id=node_id,
    #             host=request.host,
    #             port=request.port,
    #             capabilities=list(request.capabilities),
    #             max_concurrent_jobs=request.max_concurrent_jobs,
    #             status=NodeStatus.HEALTHY,
    #             last_heartbeat=time.time()
    #         )
    #         self.nodes[node_id] = node
    #     
    #     return photoshop_pb2.RegisterNodeResponse(
    #         success=True,
    #         cluster_id=self.config.cluster_id
    #     )
    # 
    # async def UnregisterNode(self, request, context):
    #     """
    #     ノード登録解除RPC
    #     """
    #     node_id = request.node_id
    #     
    #     if node_id in self.nodes:
    #         # ノードに割り当てられたジョブを再キューイング
    #         await self._requeue_node_jobs(node_id)
    #         
    #         # ノードの削除
    #         self.nodes.pop(node_id)
    #         logger.info(f"Node {node_id} unregistered")
    #         
    #         return photoshop_pb2.UnregisterNodeResponse(success=True)
    #     else:
    #         logger.warning(f"Attempted to unregister unknown node {node_id}")
    #         return photoshop_pb2.UnregisterNodeResponse(
    #             success=False,
    #             error_message=f"Node {node_id} not found"
    #         )
    # 
    # async def GetNodeStatus(self, request, context):
    #     """
    #     ノードステータス取得RPC
    #     """
    #     node_id = request.node_id
    #     
    #     if node_id in self.nodes:
    #         node = self.nodes[node_id]
    #         return photoshop_pb2.NodeStatusResponse(
    #             node_id=node.node_id,
    #             status=photoshop_pb2.HealthCheckResponse.Status.Value(node.status.name),
    #             active_jobs=node.active_jobs,
    #             completed_jobs=node.completed_jobs,
    #             failed_jobs=node.failed_jobs,
    #             uptime=time.time() - self.start_time,
    #             version="1.0.0",
    #             active_job_ids=list(node.current_jobs)
    #         )
    #     else:
    #         context.set_code(grpc.StatusCode.NOT_FOUND)
    #         context.set_details(f"Node {node_id} not found")
    #         return photoshop_pb2.NodeStatusResponse()
    # 
    # async def DispatchJob(self, request, context):
    #     """
    #     ジョブディスパッチRPC
    #     """
    #     job_id = request.job_id or str(uuid.uuid4())
    #     
    #     # ジョブの作成
    #     job = Job(
    #         job_id=job_id,
    #         job_type=request.job_type,
    #         payload=request.payload,
    #         priority=request.priority,
    #         callback_url=request.callback_url
    #     )
    #     self.jobs[job_id] = job
    #     
    #     # キューに追加
    #     heapq.heappush(self.job_queue, (-job.priority, job.created_at, job.job_id))
    #     
    #     logger.info(f"Job {job_id} of type {request.job_type} added to queue with priority {request.priority}")
    #     
    #     # 利用可能なノードを取得
    #     available_nodes = [node for node in self.nodes.values() if node.is_available]
    #     
    #     # 推定完了時間の計算（単純な実装）
    #     estimated_completion_time = 0
    #     if available_nodes:
    #         # 平均ジョブ実行時間を3秒と仮定
    #         estimated_completion_time = int(time.time() + 3)
    #     
    #     return photoshop_pb2.DispatchJobResponse(
    #         accepted=True,
    #         job_id=job_id,
    #         estimated_completion_time=estimated_completion_time
    #     )
    # 
    # async def GetJobStatus(self, request, context):
    #     """
    #     ジョブステータス取得RPC
    #     """
    #     job_id = request.job_id
    #     
    #     if job_id in self.jobs:
    #         job = self.jobs[job_id]
    #         
    #         status_map = {
    #             JobStatus.QUEUED: photoshop_pb2.JobStatusResponse.JobStatus.QUEUED,
    #             JobStatus.ASSIGNED: photoshop_pb2.JobStatusResponse.JobStatus.QUEUED,
    #             JobStatus.RUNNING: photoshop_pb2.JobStatusResponse.JobStatus.RUNNING,
    #             JobStatus.COMPLETED: photoshop_pb2.JobStatusResponse.JobStatus.COMPLETED,
    #             JobStatus.FAILED: photoshop_pb2.JobStatusResponse.JobStatus.FAILED,
    #             JobStatus.CANCELLED: photoshop_pb2.JobStatusResponse.JobStatus.CANCELLED
    #         }
    #         
    #         return photoshop_pb2.JobStatusResponse(
    #             job_id=job.job_id,
    #             status=status_map[job.status],
    #             node_id=job.assigned_node_id or "",
    #             progress=job.progress,
    #             result=job.result or "",
    #             error_message=job.error_message or "",
    #             start_time=int(job.started_at or 0),
    #             end_time=int(job.completed_at or 0)
    #         )
    #     else:
    #         context.set_code(grpc.StatusCode.NOT_FOUND)
    #         context.set_details(f"Job {job_id} not found")
    #         return photoshop_pb2.JobStatusResponse()
    # 
    # async def GetClusterStatus(self, request, context):
    #     """
    #     クラスターステータス取得RPC
    #     """
    #     # ジョブ統計の集計
    #     total_jobs = len(self.jobs)
    #     active_jobs = sum(1 for job in self.jobs.values() if job.status in [JobStatus.QUEUED, JobStatus.ASSIGNED, JobStatus.RUNNING])
    #     queued_jobs = sum(1 for job in self.jobs.values() if job.status == JobStatus.QUEUED)
    #     completed_jobs = sum(1 for job in self.jobs.values() if job.status == JobStatus.COMPLETED)
    #     failed_jobs = sum(1 for job in self.jobs.values() if job.status == JobStatus.FAILED)
    #     
    #     # ノード統計の集計
    #     total_nodes = len(self.nodes)
    #     active_nodes = sum(1 for node in self.nodes.values() if node.status in [NodeStatus.HEALTHY, NodeStatus.DEGRADED])
    #     
    #     response = photoshop_pb2.ClusterStatusResponse(
    #         cluster_id=self.config.cluster_id,
    #         total_nodes=total_nodes,
    #         active_nodes=active_nodes,
    #         total_jobs=total_jobs,
    #         active_jobs=active_jobs,
    #         queued_jobs=queued_jobs,
    #         completed_jobs=completed_jobs,
    #         failed_jobs=failed_jobs
    #     )
    #     
    #     # ノード詳細の追加（オプション）
    #     if request.include_node_details:
    #         for node in self.nodes.values():
    #             node_status = photoshop_pb2.NodeStatusResponse(
    #                 node_id=node.node_id,
    #                 status=photoshop_pb2.HealthCheckResponse.Status.Value(node.status.name),
    #                 active_jobs=node.active_jobs,
    #                 completed_jobs=node.completed_jobs,
    #                 failed_jobs=node.failed_jobs,
    #                 uptime=time.time() - self.start_time,
    #                 version="1.0.0",
    #                 active_job_ids=list(node.current_jobs)
    #             )
    #             response.nodes.append(node_status)
    #     
    #     return response
        
        # ノードの状態を更新
        node.active_jobs += 1
        node.current_jobs.add(job.job_id)
        
        logger.info(f"Job {job.job_id} assigned to node {node.node_id}")
        
        try:
            # ノードにジョブを送信（実際の実装ではgRPCリクエストを送信）
            # channel = grpc.aio.insecure_channel(node.address)
            # 
            # if job.job_type == "execute_command":
            #     stub = photoshop_pb2_grpc.PhotoshopServiceStub(channel)
            #     command_request = photoshop_pb2.CommandRequest()
            #     command_request.ParseFromString(job.payload)
            #     command_request.job_id = job.job_id
            #     asyncio.create_task(self._execute_command(stub, command_request, job, node))
            # 
            # elif job.job_type == "get_document_info":
            #     stub = photoshop_pb2_grpc.PhotoshopServiceStub(channel)
            #     doc_info_request = photoshop_pb2.DocumentInfoRequest()
            #     doc_info_request.ParseFromString(job.payload)
            #     asyncio.create_task(self._get_document_info(stub, doc_info_request, job, node))
            # 
            # elif job.job_type == "export_document":
            #     stub = photoshop_pb2_grpc.PhotoshopServiceStub(channel)
            #     export_request = photoshop_pb2.ExportRequest()
            #     export_request.ParseFromString(job.payload)
            #     asyncio.create_task(self._export_document(stub, export_request, job, node))
            
            # 仮実装（gRPCコード生成前）
            # ジョブの実行をシミュレート
            asyncio.create_task(self._simulate_job_execution(job, node))
        
        except Exception as e:
            logger.error(f"Failed to send job {job.job_id} to node {node.node_id}: {e}")
            
            # ジョブを再キューイング
            job.status = JobStatus.QUEUED
            job.assigned_node_id = None
            job.assigned_at = None
            
            # ノードの状態を更新
            node.active_jobs = max(0, node.active_jobs - 1)
            node.current_jobs.remove(job.job_id)
            
            # キューに追加
            heapq.heappush(self.job_queue, (-job.priority, job.created_at, job.job_id))
    
    async def _simulate_job_execution(self, job: Job, node: Node):
        """
        ジョブ実行のシミュレーション（仮実装）
        
        Args:
            job: 実行するジョブ
            node: 実行先のノード
        """
        # ジョブの開始
        job.status = JobStatus.RUNNING
        job.started_at = time.time()
        
        # 実行時間をシミュレート（1〜5秒）
        execution_time = random.uniform(1.0, 5.0)
        await asyncio.sleep(execution_time)
        
        # 成功確率（90%）
        if random.random() < 0.9:
            # ジョブ成功
            job.status = JobStatus.COMPLETED
            job.completed_at = time.time()
            job.progress = 100
            job.result = json.dumps({"success": True, "execution_time": execution_time})
            
            # 統計情報の更新
            self.total_jobs_processed += 1
            node.completed_jobs += 1
        else:
            # ジョブ失敗
            job.status = JobStatus.FAILED
            job.completed_at = time.time()
            job.error_message = "Simulated failure"
            
            # 統計情報の更新
            self.total_jobs_failed += 1
            node.failed_jobs += 1
        
        # ノードの状態を更新
        node.active_jobs = max(0, node.active_jobs - 1)
        node.current_jobs.remove(job.job_id)
        
        logger.info(f"Job {job.job_id} {job.status.value} on node {node.node_id}")
    
    async def _cleanup_task(self):
        """古いジョブとノードをクリーンアップするタスク"""
        while self.is_running:
            await self._cleanup_old_jobs()
            await self._cleanup_unhealthy_nodes()
            await asyncio.sleep(self.config.cleanup_interval)
    
    async def _cleanup_old_jobs(self):
        """完了または失敗したジョブをクリーンアップ"""
        current_time = time.time()
        retention_period = 86400  # 24時間（秒）
        
        for job_id, job in list(self.jobs.items()):
            if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                if job.completed_at and current_time - job.completed_at > retention_period:
                    logger.debug(f"Cleaning up old job {job_id}")
                    self.jobs.pop(job_id, None)
    
    async def _cleanup_unhealthy_nodes(self):
        """長時間不健全なノードをクリーンアップ"""
        current_time = time.time()
        unhealthy_threshold = 3600  # 1時間（秒）
        
        for node_id, node in list(self.nodes.items()):
            if node.status == NodeStatus.UNHEALTHY:
                if current_time - node.last_heartbeat > unhealthy_threshold:
                    logger.info(f"Removing unhealthy node {node_id} that has been down for too long")
                    self.nodes.pop(node_id, None)
    
    # gRPCサービスメソッド（実際の実装時にはphotoshop_pb2_grpcから生成されたクラスを継承）
    
    # async def RegisterNode(self, request, context):
    #     """
    #     ノード登録RPC
    #     """
    #     node_id = request.node_id or str(uuid.uuid4())
    #     
    #     # 既存のノードの場合は更新
    #     if node_id in self.nodes:
    #         logger.info(f"Updating existing node {node_id}")
    #         node = self.nodes[node_id]
    #         node.host = request.host
    #         node.port = request.port
    #         node.capabilities = list(request.capabilities)
    #         node.max_concurrent_jobs = request.max_concurrent_jobs
    #         node.last_heartbeat = time.time()
    #         node.status = NodeStatus.HEALTHY
    #     else:
    #         # 新規ノードの登録
    #         logger.info(f"Registering new node {node_id}")
    #         node = Node(
    #             node_id=node_id,
    #             host=request.host,
    #             port=request.port,
    #             capabilities=list(request.capabilities),
    #             max_concurrent_jobs=request.max_concurrent_jobs,
    #             status=NodeStatus.HEALTHY,
    #             last_heartbeat=time.time()
    #         )
    #         self.nodes[node_id] = node
    #     
    #     return photoshop_pb2.RegisterNodeResponse(
    #         success=True,
    #         cluster_id=self.config.cluster_id
    #     )
    # 
    # async def UnregisterNode(self, request, context):
    #     """
    #     ノード登録解除RPC
    #     """
    #     node_id = request.node_id
    #     
    #     if node_id in self.nodes:
    #         # ノードに割り当てられたジョブを再キューイング
    #         await self._requeue_node_jobs(node_id)
    #         
    #         # ノードの削除
    #         self.nodes.pop(node_id)
    #         logger.info(f"Node {node_id} unregistered")
    #         
    #         return photoshop_pb2.UnregisterNodeResponse(success=True)
    #     else:
    #         logger.warning(f"Attempted to unregister unknown node {node_id}")
    #         return photoshop_pb2.UnregisterNodeResponse(
    #             success=False,
    #             error_message=f"Node {node_id} not found"
    #         )
    # 
    # async def GetNodeStatus(self, request, context):
    #     """
    #     ノードステータス取得RPC
    #     """
    #     node_id = request.node_id
    #     
    #     if node_id in self.nodes:
    #         node = self.nodes[node_id]
    #         return photoshop_pb2.NodeStatusResponse(
    #             node_id=node.node_id,
    #             status=photoshop_pb2.HealthCheckResponse.Status.Value(node.status.name),
    #             active_jobs=node.active_jobs,
    #             completed_jobs=node.completed_jobs,
    #             failed_jobs=node.failed_jobs,
    #             uptime=time.time() - self.start_time,
    #             version="1.0.0",
    #             active_job_ids=list(node.current_jobs)
    #         )
    #     else:
    #         context.set_code(grpc.StatusCode.NOT_FOUND)
    #         context.set_details(f"Node {node_id} not found")
    #         return photoshop_pb2.NodeStatusResponse()
    # 
    # async def DispatchJob(self, request, context):
    #     """
    #     ジョブディスパッチRPC
    #     """
    #     job_id = request.job_id or str(uuid.uuid4())
    #     
    #     # ジョブの作成
    #     job = Job(
    #         job_id=job_id,
    #         job_type=request.job_type,
    #         payload=request.payload,
    #         priority=request.priority,
    #         callback_url=request.callback_url
    #     )
    #     self.jobs[job_id] = job
    #     
    #     # キューに追加
    #     heapq.heappush(self.job_queue, (-job.priority, job.created_at, job.job_id))
    #     
    #     logger.info(f"Job {job_id} of type {request.job_type} added to queue with priority {request.priority}")
    #     
    #     # 利用可能なノードを取得
    #     available_nodes = [node for node in self.nodes.values() if node.is_available]
    #     
    #     # 推定完了時間の計算（単純な実装）
    #     estimated_completion_time = 0
    #     if available_nodes:
    #         # 平均ジョブ実行時間を3秒と仮定
    #         estimated_completion_time = int(time.time() + 3)
    #     
    #     return photoshop_pb2.DispatchJobResponse(
    #         accepted=True,
    #         job_id=job_id,
    #         estimated_completion_time=estimated_completion_time
    #     )
    # 
    # async def GetJobStatus(self, request, context):
    #     """
    #     ジョブステータス取得RPC
    #     """
    #     job_id = request.job_id
    #     
    #     if job_id in self.jobs:
    #         job = self.jobs[job_id]
    #         
    #         status_map = {
    #             JobStatus.QUEUED: photoshop_pb2.JobStatusResponse.JobStatus.QUEUED,
    #             JobStatus.ASSIGNED: photoshop_pb2.JobStatusResponse.JobStatus.QUEUED,
    #             JobStatus.RUNNING: photoshop_pb2.JobStatusResponse.JobStatus.RUNNING,
    #             JobStatus.COMPLETED: photoshop_pb2.JobStatusResponse.JobStatus.COMPLETED,
    #             JobStatus.FAILED: photoshop_pb2.JobStatusResponse.JobStatus.FAILED,
    #             JobStatus.CANCELLED: photoshop_pb2.JobStatusResponse.JobStatus.CANCELLED
    #         }
    #         
    #         return photoshop_pb2.JobStatusResponse(
    #             job_id=job.job_id,
    #             status=status_map[job.status],
    #             node_id=job.assigned_node_id or "",
    #             progress=job.progress,
    #             result=job.result or "",
    #             error_message=job.error_message or "",
    #             start_time=int(job.started_at or 0),
    #             end_time=int(job.completed_at or 0)
    #         )
    #     else:
    #         context.set_code(grpc.StatusCode.NOT_FOUND)
    #         context.set_details(f"Job {job_id} not found")
    #         return photoshop_pb2.JobStatusResponse()
    # 
    # async def GetClusterStatus(self, request, context):
    #     """
    #     クラスターステータス取得RPC
    #     """
    #     # ジョブ統計の集計
    #     total_jobs = len(self.jobs)
    #     active_jobs = sum(1 for job in self.jobs.values() if job.status in [JobStatus.QUEUED, JobStatus.ASSIGNED, JobStatus.RUNNING])
    #     queued_jobs = sum(1 for job in self.jobs.values() if job.status == JobStatus.QUEUED)
    #     completed_jobs = sum(1 for job in self.jobs.values() if job.status == JobStatus.COMPLETED)
    #     failed_jobs = sum(1 for job in self.jobs.values() if job.status == JobStatus.FAILED)
    #     
    #     # ノード統計の集計
    #     total_nodes = len(self.nodes)
    #     active_nodes = sum(1 for node in self.nodes.values() if node.status in [NodeStatus.HEALTHY, NodeStatus.DEGRADED])
    #     
    #     response = photoshop_pb2.ClusterStatusResponse(
    #         cluster_id=self.config.cluster_id,
    #         total_nodes=total_nodes,
    #         active_nodes=active_nodes,
    #         total_jobs=total_jobs,
    #         active_jobs=active_jobs,
    #         queued_jobs=queued_jobs,
    #         completed_jobs=completed_jobs,
    #         failed_jobs=failed_jobs
    #     )
    #     
    #     # ノード詳細の追加（オプション）
    #     if request.include_node_details:
    #         for node in self.nodes.values():
    #             node_status = photoshop_pb2.NodeStatusResponse(
    #                 node_id=node.node_id,
    #                 status=photoshop_pb2.HealthCheckResponse.Status.Value(node.status.name),
    #                 active_jobs=node.active_jobs,
    #                 completed_jobs=node.completed_jobs,
    #                 failed_jobs=node.failed_jobs,
    #                 uptime=time.time() - self.start_time,
    #                 version="1.0.0",
    #                 active_job_ids=list(node.current_jobs)
    #             )
    #             response.nodes.append(node_status)
    #     
    #     return response
                
                # ノードの現在のジョブから削除
                node.current_jobs.remove(job_id)
                node.active_jobs = max(0, node.active_jobs - 1)
    
    async def _job_dispatcher_task(self):
        """ジョブをノードに割り当てるタスク"""
        while self.is_running:
            if not self.job_queue:
                await asyncio.sleep(0.1)
                continue
            
            # 利用可能なノードを取得
            available_nodes = [node for node in self.nodes.values() if node.is_available]
            if not available_nodes:
                await asyncio.sleep(0.1)
                continue
            
            # キューからジョブを取得
            _, _, job_id = heapq.heappop(self.job_queue)
            job = self.jobs.get(job_id)
            
            if not job or job.status != JobStatus.QUEUED:
                continue
            
            # ルーティング戦略に基づいてノードを選択
            selected_node = self._select_node(job, available_nodes)
            if not selected_node:
                # 適切なノードが見つからない場合は再キューイング
                heapq.heappush(self.job_queue, (-job.priority, job.created_at, job.job_id))
                await asyncio.sleep(0.1)
                continue
            
            # ジョブをノードに割り当て
            await self._assign_job_to_node(job, selected_node)
            
            await asyncio.sleep(0.01)  # 短い待機で他のタスクに制御を渡す