"""
文件扫描器模块 - 负责搜索指定目录下的Office文档/图片/视频
"""

import os
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Callable, Set
from dataclasses import dataclass

from config import SUPPORTED_EXTENSIONS, FILE_TYPE_GROUPS, CATEGORY_GROUPS


@dataclass
class FileInfo:
    """文件信息数据类"""
    path: str              # 完整路径
    name: str              # 文件名
    extension: str         # 扩展名（小写）
    size: int              # 文件大小（字节）
    modified_time: float   # 修改时间戳
    modified_date: str     # 修改日期字符串 YYYY-MM
    year_month: str        # 年月格式 YYYY-MM
    file_type: str         # 文件类型分类（如：Word文档、图片、视频）
    category: str          # 文件大类（office / image / video / other）
    
    @property
    def size_readable(self) -> str:
        """返回可读的文件大小"""
        size = self.size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    @property
    def modified_time_readable(self) -> str:
        """返回可读的修改时间"""
        return datetime.fromtimestamp(self.modified_time).strftime('%Y-%m-%d %H:%M:%S')


class FileScanner:
    """文件扫描器类"""
    
    def __init__(self):
        self.files: List[FileInfo] = []
        self.scanned_count = 0
        self.matched_count = 0
        self._stop_flag = False
    
    def stop(self):
        """停止扫描"""
        self._stop_flag = True
    
    def reset(self):
        """重置扫描器状态"""
        self.files = []
        self.scanned_count = 0
        self.matched_count = 0
        self._stop_flag = False
    
    def scan_directory(
        self,
        root_path: str,
        recursive: bool = True,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        category_filter: Optional[Set[str]] = None
    ) -> List[FileInfo]:
        """
        扫描目录下的所有支持的文件
        
        Args:
            root_path: 根目录路径
            recursive: 是否递归扫描子目录
            progress_callback: 进度回调函数(已扫描数, 当前文件路径)
            category_filter: 大类筛选集合，如 {'office', 'image'} 表示只扫描Office文档和图片
        
        Returns:
            匹配的文件列表
        """
        self.reset()
        root = Path(root_path)
        
        if not root.exists():
            raise FileNotFoundError(f"目录不存在: {root_path}")
        
        if not root.is_dir():
            raise NotADirectoryError(f"不是目录: {root_path}")
        
        # 选择遍历方式
        if recursive:
            self._scan_recursive(root, progress_callback, category_filter)
        else:
            self._scan_flat(root, progress_callback, category_filter)
        
        # 按修改时间排序
        self.files.sort(key=lambda x: x.modified_time, reverse=True)
        
        return self.files
    
    def _scan_recursive(
        self,
        root: Path,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        category_filter: Optional[Set[str]] = None
    ):
        """递归扫描"""
        for item in root.rglob('*'):
            if self._stop_flag:
                break
            
            self.scanned_count += 1
            
            if item.is_file():
                ext = item.suffix.lower()
                if ext in SUPPORTED_EXTENSIONS:
                    self._add_file(item, category_filter)
            
            # 每100个文件报告一次进度
            if self.scanned_count % 100 == 0 and progress_callback:
                progress_callback(self.scanned_count, str(item))
    
    def _scan_flat(
        self,
        root: Path,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        category_filter: Optional[Set[str]] = None
    ):
        """仅扫描当前目录"""
        for item in root.iterdir():
            if self._stop_flag:
                break
            
            self.scanned_count += 1
            
            if item.is_file():
                ext = item.suffix.lower()
                if ext in SUPPORTED_EXTENSIONS:
                    self._add_file(item, category_filter)
            
            if self.scanned_count % 100 == 0 and progress_callback:
                progress_callback(self.scanned_count, str(item))
    
    def _add_file(self, file_path: Path, category_filter: Optional[Set[str]] = None):
        """添加文件到列表"""
        try:
            stat = file_path.stat()
            ext = file_path.suffix.lower()
            
            # 获取年月
            modified_time = stat.st_mtime
            dt = datetime.fromtimestamp(modified_time)
            year_month = dt.strftime('%Y-%m')
            
            # 确定文件类型和大类
            file_type = '其他'
            category = 'other'
            for type_name, extensions in FILE_TYPE_GROUPS.items():
                if ext in extensions:
                    file_type = type_name
                    # 根据类型名称确定大类
                    if type_name in ('图片',):
                        category = 'image'
                    elif type_name in ('视频',):
                        category = 'video'
                    else:
                        category = 'office'
                    break
            
            # 如果指定了大类筛选，不匹配则跳过
            if category_filter and category not in category_filter:
                return
            
            file_info = FileInfo(
                path=str(file_path),
                name=file_path.name,
                extension=ext,
                size=stat.st_size,
                modified_time=modified_time,
                modified_date=dt.strftime('%Y-%m-%d'),
                year_month=year_month,
                file_type=file_type,
                category=category
            )
            
            self.files.append(file_info)
            self.matched_count += 1
            
        except (OSError, PermissionError):
            # 忽略无法访问的文件
            pass
    
    def get_statistics(self) -> Dict:
        """获取扫描统计信息"""
        if not self.files:
            return {
                'total_files': 0,
                'total_size': 0,
                'by_type': {},
                'by_month': {},
                'by_category': {},
                'size_readable': '0 B'
            }
        
        total_size = sum(f.size for f in self.files)
        
        # 按类型统计
        by_type = {}
        for f in self.files:
            by_type[f.file_type] = by_type.get(f.file_type, 0) + 1
        
        # 按月统计
        by_month = {}
        for f in self.files:
            by_month[f.year_month] = by_month.get(f.year_month, 0) + 1
        
        # 按大类统计
        by_category = {}
        for f in self.files:
            by_category[f.category] = by_category.get(f.category, 0) + 1
        
        # 格式化总大小
        size = total_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                size_str = f"{size:.1f} {unit}"
                break
            size /= 1024.0
        else:
            size_str = f"{size:.1f} TB"
        
        return {
            'total_files': len(self.files),
            'total_size': total_size,
            'size_readable': size_str,
            'by_type': by_type,
            'by_month': dict(sorted(by_month.items())),
            'by_category': by_category,
        }
