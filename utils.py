"""
工具函数模块
"""

import os
from pathlib import Path


def format_file_size(size_bytes: int) -> str:
    """格式化文件大小为人类可读格式"""
    if size_bytes == 0:
        return "0 B"
    
    size = float(size_bytes)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


def get_folder_size(folder_path: str) -> int:
    """获取文件夹总大小（字节）"""
    total = 0
    path = Path(folder_path)
    if not path.exists():
        return 0
    
    try:
        for item in path.rglob('*'):
            if item.is_file():
                total += item.stat().st_size
    except (OSError, PermissionError):
        pass
    
    return total


def ensure_dir(path: str):
    """确保目录存在"""
    Path(path).mkdir(parents=True, exist_ok=True)


def is_valid_source_dir(path: str) -> bool:
    """检查是否是有效的源目录"""
    p = Path(path)
    return p.exists() and p.is_dir()


def is_valid_target_dir(path: str) -> bool:
    """检查是否是有效的目标目录（不存在则创建）"""
    p = Path(path)
    if not p.exists():
        try:
            p.mkdir(parents=True, exist_ok=True)
            return True
        except OSError:
            return False
    return p.is_dir()


def count_files_in_dir(path: str, recursive: bool = True) -> int:
    """统计目录中的文件数量"""
    p = Path(path)
    if not p.exists() or not p.is_dir():
        return 0
    
    try:
        if recursive:
            return sum(1 for _ in p.rglob('*') if _.is_file())
        else:
            return sum(1 for _ in p.iterdir() if _.is_file())
    except (OSError, PermissionError):
        return 0
