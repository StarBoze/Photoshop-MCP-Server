"""
パフォーマンス最適化ユーティリティ

このモジュールは、Photoshop MCP Serverのパフォーマンスを最適化するための
ユーティリティ関数を提供します。
"""

import os
import time
import functools
import threading
import concurrent.futures
from typing import Dict, Any, Callable, List, TypeVar, Optional
import logging
import psutil

# 型変数
T = TypeVar('T')
R = TypeVar('R')

# ロガーの設定
logger = logging.getLogger(__name__)

# キャッシュ設定
DEFAULT_CACHE_SIZE = 100
DEFAULT_CACHE_TTL = 3600  # 1時間

class ScriptCache:
    """
    スクリプト実行結果のキャッシュを管理するクラス
    """
    def __init__(self, max_size: int = DEFAULT_CACHE_SIZE, ttl: int = DEFAULT_CACHE_TTL):
        """
        キャッシュを初期化
        
        Args:
            max_size: キャッシュの最大サイズ
            ttl: キャッシュエントリの有効期間（秒）
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size
        self.ttl = ttl
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """
        キャッシュからデータを取得
        
        Args:
            key: キャッシュキー
            
        Returns:
            キャッシュされたデータ、または存在しない場合はNone
        """
        with self.lock:
            if key not in self.cache:
                return None
            
            entry = self.cache[key]
            if time.time() - entry['timestamp'] > self.ttl:
                # TTL切れの場合はキャッシュから削除
                del self.cache[key]
                return None
            
            return entry['data']
    
    def set(self, key: str, data: Any) -> None:
        """
        データをキャッシュに保存
        
        Args:
            key: キャッシュキー
            data: 保存するデータ
        """
        with self.lock:
            # キャッシュサイズが上限に達した場合、最も古いエントリを削除
            if len(self.cache) >= self.max_size:
                oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k]['timestamp'])
                del self.cache[oldest_key]
            
            self.cache[key] = {
                'data': data,
                'timestamp': time.time()
            }
    
    def clear(self) -> None:
        """キャッシュをクリア"""
        with self.lock:
            self.cache.clear()
    
    def remove_expired(self) -> int:
        """
        期限切れのキャッシュエントリを削除
        
        Returns:
            削除されたエントリの数
        """
        with self.lock:
            current_time = time.time()
            expired_keys = [
                key for key, entry in self.cache.items()
                if current_time - entry['timestamp'] > self.ttl
            ]
            
            for key in expired_keys:
                del self.cache[key]
            
            return len(expired_keys)

# グローバルキャッシュインスタンス
script_cache = ScriptCache()

def cached_execution(func: Callable[..., T]) -> Callable[..., T]:
    """
    関数の実行結果をキャッシュするデコレータ
    
    Args:
        func: キャッシュする関数
        
    Returns:
        キャッシュ機能を持つ関数
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        # キャッシュキーの生成
        key_parts = [func.__name__]
        key_parts.extend([str(arg) for arg in args])
        key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
        cache_key = ":".join(key_parts)
        
        # キャッシュからデータを取得
        cached_result = script_cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Cache hit for {func.__name__}")
            return cached_result
        
        # キャッシュにない場合は関数を実行
        logger.debug(f"Cache miss for {func.__name__}")
        result = func(*args, **kwargs)
        
        # 結果をキャッシュに保存
        script_cache.set(cache_key, result)
        
        return result
    
    return wrapper

def parallel_map(func: Callable[[T], R], items: List[T], max_workers: Optional[int] = None) -> List[R]:
    """
    リストの各要素に関数を並列適用
    
    Args:
        func: 適用する関数
        items: 入力リスト
        max_workers: 最大ワーカー数（Noneの場合はCPUコア数×2）
        
    Returns:
        関数適用結果のリスト
    """
    if max_workers is None:
        max_workers = os.cpu_count() * 2 or 4
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(func, items))
    
    return results

def memory_optimized(max_memory_percent: float = 80.0) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    メモリ使用量を監視し、最適化するデコレータ
    
    Args:
        max_memory_percent: 最大メモリ使用率（%）
        
    Returns:
        メモリ最適化機能を持つ関数
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # 現在のメモリ使用量を取得
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / (1024 * 1024)  # MB単位
            
            # 関数を実行
            result = func(*args, **kwargs)
            
            # 実行後のメモリ使用量を取得
            current_memory = process.memory_info().rss / (1024 * 1024)  # MB単位
            memory_increase = current_memory - initial_memory
            
            # メモリ使用量が閾値を超えた場合、ガベージコレクションを強制実行
            if psutil.virtual_memory().percent > max_memory_percent:
                import gc
                gc.collect()
                logger.info(f"Forced garbage collection after {func.__name__}. "
                           f"Memory increase: {memory_increase:.2f} MB")
            
            return result
        
        return wrapper
    
    return decorator

def timed_execution(func: Callable[..., T]) -> Callable[..., T]:
    """
    関数の実行時間を計測するデコレータ
    
    Args:
        func: 計測する関数
        
    Returns:
        時間計測機能を持つ関数
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        execution_time = end_time - start_time
        logger.info(f"{func.__name__} executed in {execution_time:.4f} seconds")
        
        return result
    
    return wrapper

def with_timeout(timeout_seconds: float) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    タイムアウト機能を追加するデコレータ
    
    Args:
        timeout_seconds: タイムアウト秒数
        
    Returns:
        タイムアウト機能を持つ関数
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            result = [None]
            exception = [None]
            
            def target():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    exception[0] = e
            
            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()
            thread.join(timeout_seconds)
            
            if thread.is_alive():
                raise TimeoutError(f"{func.__name__} timed out after {timeout_seconds} seconds")
            
            if exception[0] is not None:
                raise exception[0]
            
            return result[0]
        
        return wrapper
    
    return decorator

def cleanup_temp_files(directory: Optional[str] = None, max_age_hours: int = 24) -> int:
    """
    一時ファイルを自動クリーンアップ
    
    Args:
        directory: クリーンアップするディレクトリ（Noneの場合はデフォルトの一時ディレクトリ）
        max_age_hours: 削除する最大ファイル経過時間（時間単位）
        
    Returns:
        削除されたファイルの数
    """
    if directory is None:
        directory = os.path.join(os.path.expanduser("~"), ".photoshop_mcp_server", "temp")
    
    if not os.path.exists(directory):
        return 0
    
    max_age_seconds = max_age_hours * 3600
    current_time = time.time()
    deleted_count = 0
    
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        
        # ファイルの最終更新時刻を取得
        file_age = current_time - os.path.getmtime(file_path)
        
        # 指定した経過時間より古いファイルを削除
        if file_age > max_age_seconds:
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    deleted_count += 1
            except Exception as e:
                logger.error(f"Error deleting {file_path}: {e}")
    
    return deleted_count