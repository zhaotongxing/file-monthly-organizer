"""
文件扫描器模块 - 负责搜索指定目录下的Office文档/图片/视频
v1.5 核心修正:
  - 图片使用EXIF拍摄时间(DateTimeOriginal)进行整理
  - 视频使用媒体创建时间(MP4 moov.mvhd / 文件系统创建时间)进行整理
  - 添加 time_source 字段追踪每个文件使用的时间来源
  - FileInfo 字段顺序向后兼容
  - 详细的扫描日志显示时间提取统计
"""

import os
import struct
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional, Callable, Set
from dataclasses import dataclass

from config import SUPPORTED_EXTENSIONS, FILE_TYPE_GROUPS, CATEGORY_GROUPS

# 尝试导入 PIL 用于读取图片 EXIF
try:
    from PIL import Image
    from PIL.ExifTags import TAGS
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False


# EXIF 标签 ID（PIL 1.x 使用数字索引）
_EXIF_DateTimeOriginal = 0x9003   # 36867
_EXIF_DateTimeDigitized = 0x9004  # 36868
_EXIF_DateTime = 0x0132           # 306


def _parse_exif_datetime(dt_str) -> Optional[float]:
    """
    解析 EXIF 日期字符串为 Unix 时间戳
    支持格式: "2023:08:15 14:32:05" 等
    """
    if not dt_str:
        return None
    if isinstance(dt_str, bytes):
        dt_str = dt_str.decode('utf-8', errors='ignore').strip()
    else:
        dt_str = str(dt_str).strip()
    
    for fmt in ('%Y:%m:%d %H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S'):
        try:
            dt = datetime.strptime(dt_str, fmt)
            return dt.timestamp()
        except ValueError:
            continue
    return None


def _extract_exif_datetime(path: str) -> Optional[float]:
    """
    从图片 EXIF 读取拍摄时间 DateTimeOriginal
    返回 Unix 时间戳，失败返回 None
    """
    if not _PIL_AVAILABLE:
        return None
    try:
        with Image.open(path) as img:
            # 尝试多种方式读取 EXIF
            exif = None
            if hasattr(img, '_getexif') and callable(getattr(img, '_getexif')):
                exif = img._getexif()
            if exif is None and hasattr(img, 'getexif') and callable(getattr(img, 'getexif')):
                exif = img.getexif()
            
            if not exif:
                return None
            
            # 优先顺序: DateTimeOriginal > DateTimeDigitized > DateTime
            dt_str = None
            for tag_id in (_EXIF_DateTimeOriginal, _EXIF_DateTimeDigitized, _EXIF_DateTime):
                if tag_id in exif:
                    dt_str = exif[tag_id]
                    if dt_str:
                        break
            
            return _parse_exif_datetime(dt_str)
    except Exception:
        return None


def _extract_mp4_creation_time(path: str) -> Optional[float]:
    """
    从 MP4/MOV 文件读取媒体创建时间 (moov.mvhd creation_time)
    Macintosh epoch 起点: 1904-01-01 UTC
    返回 Unix 时间戳，失败返回 None
    """
    try:
        with open(path, 'rb') as f:
            file_size = os.path.getsize(path)
            while f.tell() < file_size:
                header = f.read(8)
                if len(header) < 8:
                    return None
                
                size = struct.unpack('>I', header[:4])[0]
                box_type = header[4:8]
                
                if size == 0:
                    break
                if size == 1:
                    ext_size = f.read(8)
                    if len(ext_size) < 8:
                        return None
                    size = struct.unpack('>Q', ext_size)[0]
                    size -= 8  # 扣除已读取的扩展 size 部分
                
                if box_type == b'moov':
                    # 读取 moov box 内容（限制最大 2MB）
                    moov_size = min(size - 8, 2 * 1024 * 1024)
                    if moov_size <= 0:
                        return None
                    moov_data = f.read(moov_size)
                    
                    # 在 moov 中查找 mvhd
                    mvhd_idx = moov_data.find(b'mvhd')
                    if mvhd_idx < 0:
                        return None
                    
                    mvhd_start = mvhd_idx + 8  # 跳过 size(4) + 'mvhd'(4)
                    if mvhd_start >= len(moov_data):
                        return None
                    
                    version = moov_data[mvhd_start]
                    
                    if version == 0:
                        ct_offset = mvhd_start + 4  # version(1) + flags(3)
                        if ct_offset + 4 > len(moov_data):
                            return None
                        creation_seconds = struct.unpack('>I', moov_data[ct_offset:ct_offset + 4])[0]
                    elif version == 1:
                        ct_offset = mvhd_start + 4
                        if ct_offset + 8 > len(moov_data):
                            return None
                        creation_seconds = struct.unpack('>Q', moov_data[ct_offset:ct_offset + 8])[0]
                    else:
                        return None
                    
                    # 转换为 Unix 时间戳
                    mac_epoch = datetime(1904, 1, 1, tzinfo=timezone.utc).timestamp()
                    unix_ts = mac_epoch + creation_seconds
                    
                    # 过滤异常值：早于 1990 年或晚于当前时间+1年视为无效
                    now = time.time()
                    if unix_ts < 631152000 or unix_ts > now + 31536000:
                        return None
                    return unix_ts
                else:
                    # 跳过当前 box
                    skip_size = size - 8
                    if skip_size < 0:
                        return None
                    f.seek(skip_size, 1)
    except Exception:
        return None


def _get_file_creation_time(path: str) -> Optional[float]:
    """
    获取文件系统创建时间
    Windows: st_ctime 是创建时间
    Linux: 尝试 st_birthtime (部分文件系统支持)
    """
    try:
        stat = os.stat(path)
        # Windows 上 st_ctime 是创建时间; Linux 上部分文件系统有 st_birthtime
        if hasattr(stat, 'st_birthtime'):
            return stat.st_birthtime
        return stat.st_ctime
    except Exception:
        return None


def _get_best_time_for_media(path: str, category: str) -> tuple:
    """
    获取媒体文件最佳时间（用于整理）
    
    返回: (timestamp, source_label)
    source_label 值: "EXIF", "media_create", "file_create", "modified"
    
    优先级:
      图片: EXIF DateTimeOriginal → 文件创建时间 → 修改时间
      视频: MP4 媒体创建时间 → 文件创建时间 → 修改时间
    """
    if category == 'image':
        # 尝试 EXIF
        ts = _extract_exif_datetime(path)
        if ts:
            return (ts, "EXIF")
        # 回退到文件创建时间
        ts = _get_file_creation_time(path)
        if ts:
            return (ts, "file_create")
        return (None, "modified")
    
    elif category == 'video':
        # 尝试 MP4 媒体创建时间
        ts = _extract_mp4_creation_time(path)
        if ts:
            return (ts, "media_create")
        # 回退到文件创建时间
        ts = _get_file_creation_time(path)
        if ts:
            return (ts, "file_create")
        return (None, "modified")
    
    return (None, "modified")


# ========== 数据类 ==========

@dataclass
class FileInfo:
    """文件信息数据类
    
    字段顺序保持与 v1.3 兼容（无默认值的字段在前）
    """
    path: str              # 完整路径
    name: str              # 文件名
    extension: str         # 扩展名（小写）
    size: int              # 文件大小（字节）
    modified_time: float   # 文件修改时间戳
    modified_date: str     # 修改日期字符串 YYYY-MM-DD
    year_month: str        # 用于整理的年月格式 YYYY-MM（媒体文件基于拍摄/创建时间）
    file_type: str         # 文件类型分类（如：Word文档、图片、视频）
    category: str = ""     # 文件大类（office / image / video / other）
    capture_time: Optional[float] = None  # 拍摄/媒体创建时间（Unix时间戳）
    time_source: str = "modified"  # 时间来源: EXIF/media_create/file_create/modified

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

    @property
    def capture_time_readable(self) -> str:
        """返回可读的拍摄/创建时间（如果没有则返回修改时间）"""
        if self.capture_time:
            return datetime.fromtimestamp(self.capture_time).strftime('%Y-%m-%d %H:%M:%S')
        return self.modified_time_readable

    @property
    def display_time(self) -> float:
        """返回用于显示和排序的时间（媒体文件优先 capture_time）"""
        return self.capture_time if self.capture_time else self.modified_time


# ========== 扫描器 ==========

class FileScanner:
    """文件扫描器类"""

    def __init__(self):
        self.files: List[FileInfo] = []
        self.scanned_count = 0
        self.matched_count = 0
        self._stop_flag = False
        self._time_stats = {
            'EXIF': 0,
            'media_create': 0,
            'file_create': 0,
            'modified': 0,
        }
        self._pillow_warned = False

    def stop(self):
        """停止扫描"""
        self._stop_flag = True

    def reset(self):
        """重置扫描器状态"""
        self.files = []
        self.scanned_count = 0
        self.matched_count = 0
        self._stop_flag = False
        self._time_stats = {
            'EXIF': 0,
            'media_create': 0,
            'file_create': 0,
            'modified': 0,
        }
        self._pillow_warned = False

    def is_pillow_available(self) -> bool:
        """Pillow 是否可用（用于图片 EXIF 读取）"""
        return _PIL_AVAILABLE

    def get_time_stats(self) -> Dict:
        """获取时间来源统计"""
        return dict(self._time_stats)

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
            匹配的文件列表（按拍摄/创建时间倒序排列）
        """
        self.reset()
        root = Path(root_path)

        if not root.exists():
            raise FileNotFoundError(f"目录不存在: {root_path}")

        if not root.is_dir():
            raise NotADirectoryError(f"不是目录: {root_path}")

        if recursive:
            self._scan_recursive(root, progress_callback, category_filter)
        else:
            self._scan_flat(root, progress_callback, category_filter)

        # 按拍摄/创建时间排序（最新的在前）
        self.files.sort(key=lambda x: x.display_time, reverse=True)

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
            modified_time = stat.st_mtime
            modified_dt = datetime.fromtimestamp(modified_time)

            # 确定文件类型和大类
            file_type = '其他'
            category = 'other'
            for type_name, extensions in FILE_TYPE_GROUPS.items():
                if ext in extensions:
                    file_type = type_name
                    if type_name == '图片':
                        category = 'image'
                    elif type_name == '视频':
                        category = 'video'
                    else:
                        category = 'office'
                    break

            # 如果指定了大类筛选，不匹配则跳过
            if category_filter and category not in category_filter:
                return

            # 获取最佳时间（用于整理的年月）
            if category in ('image', 'video'):
                capture_time, time_source = _get_best_time_for_media(str(file_path), category)
                # 计数
                self._time_stats[time_source] = self._time_stats.get(time_source, 0) + 1
            else:
                capture_time = None
                time_source = "modified"

            # 决定用于整理的年月
            if capture_time:
                sort_dt = datetime.fromtimestamp(capture_time)
            else:
                sort_dt = modified_dt
            year_month = sort_dt.strftime('%Y-%m')

            # 构造 FileInfo
            file_info = FileInfo(
                path=str(file_path),
                name=file_path.name,
                extension=ext,
                size=stat.st_size,
                modified_time=modified_time,
                modified_date=modified_dt.strftime('%Y-%m-%d'),
                year_month=year_month,
                file_type=file_type,
                category=category,
                capture_time=capture_time,
                time_source=time_source,
            )

            self.files.append(file_info)
            self.matched_count += 1

        except (OSError, PermissionError):
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
                'size_readable': '0 B',
                'time_stats': {}
            }

        total_size = sum(f.size for f in self.files)

        by_type = {}
        for f in self.files:
            by_type[f.file_type] = by_type.get(f.file_type, 0) + 1

        by_month = {}
        for f in self.files:
            by_month[f.year_month] = by_month.get(f.year_month, 0) + 1

        by_category = {}
        for f in self.files:
            by_category[f.category] = by_category.get(f.category, 0) + 1

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
            'time_stats': self.get_time_stats(),
        }
