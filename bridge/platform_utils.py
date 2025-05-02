"""
プラットフォーム検出と条件分岐のユーティリティ
"""
import os
import platform
import tempfile
import functools
from typing import Callable, Dict, Any, Optional, TypeVar, cast

# 型変数
T = TypeVar('T')

# プラットフォーム定数
PLATFORM_WINDOWS = "Windows"
PLATFORM_MACOS = "Darwin"
PLATFORM_LINUX = "Linux"

def get_platform() -> str:
    """現在のプラットフォームを取得する"""
    return platform.system()

def is_windows() -> bool:
    """Windowsかどうかを判定する"""
    return get_platform() == PLATFORM_WINDOWS

def is_macos() -> bool:
    """macOSかどうかを判定する"""
    return get_platform() == PLATFORM_MACOS

def is_linux() -> bool:
    """Linuxかどうかを判定する"""
    return get_platform() == PLATFORM_LINUX

def get_platform_config() -> Dict[str, Any]:
    """プラットフォームに応じた設定値を取得する"""
    config = {
        "temp_dir": tempfile.gettempdir(),
        "path_separator": os.path.sep,
    }
    
    if is_windows():
        config.update({
            "script_extension": ".ps1",
            "script_executor": "powershell.exe",
            "script_executor_args": ["-ExecutionPolicy", "Bypass", "-File"],
        })
    elif is_macos():
        config.update({
            "script_extension": ".scpt",
            "script_executor": "/usr/bin/osascript",
            "script_executor_args": [],
        })
    else:
        config.update({
            "script_extension": ".sh",
            "script_executor": "/bin/sh",
            "script_executor_args": [],
        })
    
    return config

def get_temp_file(prefix: str = "", suffix: str = "") -> str:
    """プラットフォームに応じた一時ファイルのパスを取得する"""
    config = get_platform_config()
    if not suffix:
        suffix = config["script_extension"]
    
    fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=config["temp_dir"])
    os.close(fd)
    return path

def platform_specific(
    windows_func: Optional[Callable[..., T]] = None,
    macos_func: Optional[Callable[..., T]] = None,
    linux_func: Optional[Callable[..., T]] = None,
    default_func: Optional[Callable[..., T]] = None
) -> Callable[..., T]:
    """プラットフォームに応じた関数を実行するデコレータ"""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            platform_name = get_platform()
            
            if platform_name == PLATFORM_WINDOWS and windows_func is not None:
                return windows_func(*args, **kwargs)
            elif platform_name == PLATFORM_MACOS and macos_func is not None:
                return macos_func(*args, **kwargs)
            elif platform_name == PLATFORM_LINUX and linux_func is not None:
                return linux_func(*args, **kwargs)
            elif default_func is not None:
                return default_func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        
        return wrapper
    
    return decorator