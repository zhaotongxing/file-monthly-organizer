"""
去重模块 - 查找并删除重复的文件

功能:
    - 基于文件内容 MD5 哈希值检测完全重复的文件
    - 按文件大小预筛选后再计算哈希（优化性能）
    - 逐块读取大文件，避免内存溢出
    - 智能保留策略：按修改时间、路径深度自动推荐保留项
    - 支持预览模式（不实际删除）
    - 支持手动指定每组的保留文件
    - 支持按大类筛选去重范围（Office/图片/视频）
"""

import hashlib
import os
from pathlib import Path
from typing import List, Dict, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from scanner import FileInfo


class KeepStrategy(Enum):
    """保留策略"""
    KEEP_FIRST = "first"          # 保留每组第一个
    KEEP_NEWEST = "newest"        # 保留修改时间最新的
    KEEP_OLDEST = "oldest"        # 保留修改时间最旧的
    KEEP_SHORTEST_PATH = "short"  # 保留路径最短的（通常意味着更接近根目录）
    KEEP_MANUAL = "manual"        # 手动指定（需要用户交互）


@dataclass
class DuplicateGroup:
    """重复文件组"""
    hash_value: str                 # MD5哈希值
    size: int                       # 文件大小（字节）
    size_readable: str              # 可读大小
    files: List[FileInfo] = field(default_factory=list)  # 该哈希对应的所有文件
    keep_index: int = 0             # 建议保留的文件索引
    
    @property
    def duplicate_count(self) -> int:
        """重复数量（不含保留项）"""
        return len(self.files) - 1
    
    @property
    def waste_space(self) -> int:
        """浪费的空间（重复副本的总大小）"""
        return self.size * self.duplicate_count
    
    @property
    def waste_readable(self) -> str:
        """可读格式的浪费空间"""
        return self._format_size(self.waste_space)
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        size = float(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"


@dataclass
class DeleteResult:
    """删除操作结果"""
    success: bool
    file_path: str
    hash_value: str
    error: Optional[str] = None


@dataclass
class DeduplicateSummary:
    """去重操作摘要"""
    total_groups: int
    total_duplicates: int
    total_waste_space: int
    deleted_count: int
    freed_space: int
    failed_count: int
    strategy: str
    
    @property
    def freed_readable(self) -> str:
        size = float(self.freed_space)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"
    
    @property
    def waste_readable(self) -> str:
        size = float(self.total_waste_space)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"


class FileDeduplicator:
    """文件去重器"""
    
    # 大文件阈值：超过此大小才逐块读取
    LARGE_FILE_THRESHOLD = 4 * 1024 * 1024  # 4MB
    # 分块大小
    CHUNK_SIZE = 65536  # 64KB
    
    def __init__(self):
        self.groups: List[DuplicateGroup] = []
        self._stop_flag = False
    
    def stop(self):
        """停止操作"""
        self._stop_flag = True
    
    def reset(self):
        """重置状态"""
        self.groups = []
        self._stop_flag = False
    
    def find_duplicates(
        self,
        files: List[FileInfo],
        strategy: KeepStrategy = KeepStrategy.KEEP_NEWEST,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        quick_mode: bool = False
    ) -> List[DuplicateGroup]:
        """
        查找重复文件
        
        Args:
            files: 文件列表
            strategy: 保留策略
            progress_callback: 进度回调(current, total, message)
            quick_mode: 快速模式，只比较文件名+大小+修改时间，不计算完整哈希
        
        Returns:
            重复文件组列表
        """
        self.reset()
        
        if not files:
            return []
        
        if quick_mode:
            return self._find_by_signature(files, strategy, progress_callback)
        
        # 第一步：按大小分组
        size_map: Dict[int, List[FileInfo]] = {}
        for f in files:
            size_map.setdefault(f.size, []).append(f)
        
        # 只保留有多个相同大小的文件（潜在重复）
        potential_groups = {size: file_list for size, file_list in size_map.items() 
                           if len(file_list) > 1}
        
        total_files = sum(len(v) for v in potential_groups.values())
        processed = 0
        
        # 第二步：对每个潜在重复组计算哈希
        hash_map: Dict[str, List[FileInfo]] = {}
        
        for size, file_list in potential_groups.items():
            for f in file_list:
                if self._stop_flag:
                    return self.groups
                
                processed += 1
                if progress_callback and processed % 10 == 0:
                    progress_callback(processed, total_files, 
                                     f"正在分析: {f.name[:30]}")
                
                hash_value = self._compute_hash(f.path)
                if hash_value:
                    hash_map.setdefault(hash_value, []).append(f)
        
        # 第三步：创建重复组
        for hash_value, file_list in hash_map.items():
            if len(file_list) > 1:  # 只有多于1个才是重复
                size = file_list[0].size
                
                group = DuplicateGroup(
                    hash_value=hash_value,
                    size=size,
                    size_readable=file_list[0].size_readable,
                    files=file_list.copy()
                )
                
                # 应用保留策略
                group.keep_index = self._select_keep_index(group.files, strategy)
                
                self.groups.append(group)
        
        if progress_callback:
            progress_callback(total_files, total_files, "分析完成")
        
        return self.groups
    
    def _find_by_signature(
        self,
        files: List[FileInfo],
        strategy: KeepStrategy,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> List[DuplicateGroup]:
        """
        快速模式：基于文件名+大小+修改时间的签名比对
        注意：这种模式可能误判（不同内容但相同大小和时间），但速度快
        """
        self.reset()
        
        if not files:
            return []
        
        # 按文件名+大小+修改时间分组
        sig_map: Dict[str, List[FileInfo]] = {}
        
        for f in files:
            sig = f"{f.name}|{f.size}|{f.modified_time}"
            sig_map.setdefault(sig, []).append(f)
        
        total = len(files)
        processed = 0
        
        for sig, file_list in sig_map.items():
            processed += len(file_list)
            if len(file_list) > 1:
                size = file_list[0].size
                group = DuplicateGroup(
                    hash_value=sig,  # 使用签名作为"哈希"
                    size=size,
                    size_readable=file_list[0].size_readable,
                    files=file_list.copy()
                )
                group.keep_index = self._select_keep_index(group.files, strategy)
                self.groups.append(group)
            
            if progress_callback and processed % 10 == 0:
                progress_callback(min(processed, total), total, "快速比对中...")
        
        if progress_callback:
            progress_callback(total, total, "快速比对完成")
        
        return self.groups
    
    def _compute_hash(self, file_path: str) -> Optional[str]:
        """计算文件的 MD5 哈希值"""
        try:
            file_size = os.path.getsize(file_path)
            
            md5 = hashlib.md5()
            
            with open(file_path, 'rb') as f:
                if file_size > self.LARGE_FILE_THRESHOLD:
                    # 大文件：逐块读取
                    while True:
                        chunk = f.read(self.CHUNK_SIZE)
                        if not chunk:
                            break
                        md5.update(chunk)
                else:
                    # 小文件：直接读取
                    md5.update(f.read())
            
            return md5.hexdigest()
            
        except (OSError, PermissionError, IOError):
            return None
    
    def _select_keep_index(self, files: List[FileInfo], strategy: KeepStrategy) -> int:
        """根据策略选择保留的文件索引"""
        if not files:
            return 0
        
        if strategy == KeepStrategy.KEEP_FIRST:
            return 0
        
        elif strategy == KeepStrategy.KEEP_NEWEST:
            # 找修改时间最新的
            newest_time = max(f.modified_time for f in files)
            for i, f in enumerate(files):
                if f.modified_time == newest_time:
                    return i
            return 0
        
        elif strategy == KeepStrategy.KEEP_OLDEST:
            # 找修改时间最旧的
            oldest_time = min(f.modified_time for f in files)
            for i, f in enumerate(files):
                if f.modified_time == oldest_time:
                    return i
            return 0
        
        elif strategy == KeepStrategy.KEEP_SHORTEST_PATH:
            # 找路径最短的
            shortest = min(len(f.path) for f in files)
            for i, f in enumerate(files):
                if len(f.path) == shortest:
                    return i
            return 0
        
        elif strategy == KeepStrategy.KEEP_MANUAL:
            # 默认保留第一个，等待用户修改
            return 0
        
        return 0
    
    def delete_duplicates(
        self,
        groups: Optional[List[DuplicateGroup]] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        preview: bool = False
    ) -> Tuple[List[DeleteResult], DeduplicateSummary]:
        """
        删除重复文件（保留每组指定的 keep_index 文件）
        
        Args:
            groups: 要处理的重复组，None则使用 self.groups
            progress_callback: 进度回调
            preview: 预览模式（不实际删除）
        
        Returns:
            (删除结果列表, 操作摘要)
        """
        if groups is None:
            groups = self.groups
        
        results: List[DeleteResult] = []
        deleted_count = 0
        freed_space = 0
        failed_count = 0
        total_duplicates = sum(g.duplicate_count for g in groups)
        processed = 0
        
        for group in groups:
            for i, file_info in enumerate(group.files):
                if i == group.keep_index:
                    # 这是要保留的文件
                    results.append(DeleteResult(
                        success=True,
                        file_path=file_info.path,
                        hash_value=group.hash_value,
                        error="保留"
                    ))
                    continue
                
                # 这是要删除的重复文件
                processed += 1
                if progress_callback:
                    progress_callback(processed, total_duplicates, 
                                     f"正在删除: {file_info.name[:30]}")
                
                if preview:
                    # 预览模式：标记为成功但不实际删除
                    results.append(DeleteResult(
                        success=True,
                        file_path=file_info.path,
                        hash_value=group.hash_value,
                        error="预览模式 - 未实际删除"
                    ))
                    deleted_count += 1
                    freed_space += group.size
                else:
                    # 实际删除
                    try:
                        os.remove(file_info.path)
                        results.append(DeleteResult(
                            success=True,
                            file_path=file_info.path,
                            hash_value=group.hash_value
                        ))
                        deleted_count += 1
                        freed_space += group.size
                    except (OSError, PermissionError) as e:
                        results.append(DeleteResult(
                            success=False,
                            file_path=file_info.path,
                            hash_value=group.hash_value,
                            error=str(e)
                        ))
                        failed_count += 1
        
        if progress_callback:
            progress_callback(total_duplicates, total_duplicates, "处理完成")
        
        summary = DeduplicateSummary(
            total_groups=len(groups),
            total_duplicates=total_duplicates,
            total_waste_space=sum(g.waste_space for g in groups),
            deleted_count=deleted_count,
            freed_space=freed_space,
            failed_count=failed_count,
            strategy="preview" if preview else "delete"
        )
        
        return results, summary
    
    def get_summary(self) -> Dict:
        """获取当前重复组摘要信息"""
        if not self.groups:
            return {
                'total_groups': 0,
                'total_duplicates': 0,
                'total_waste_space': 0,
                'waste_readable': '0 B'
            }
        
        total_duplicates = sum(g.duplicate_count for g in self.groups)
        total_waste = sum(g.waste_space for g in self.groups)
        
        # 格式化浪费空间
        size = float(total_waste)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                size_str = f"{size:.1f} {unit}"
                break
            size /= 1024.0
        else:
            size_str = f"{size:.1f} PB"
        
        return {
            'total_groups': len(self.groups),
            'total_duplicates': total_duplicates,
            'total_waste_space': total_waste,
            'waste_readable': size_str,
        }
    
    def generate_report(self) -> str:
        """生成去重报告"""
        lines = []
        lines.append("=" * 60)
        lines.append("文件去重报告")
        lines.append("=" * 60)
        lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        summary = self.get_summary()
        lines.append("【统计摘要】")
        lines.append(f"  重复组数: {summary['total_groups']}")
        lines.append(f"  重复文件: {summary['total_duplicates']} 个")
        lines.append(f"  浪费空间: {summary['waste_readable']}")
        lines.append("")
        
        if self.groups:
            lines.append("【重复文件详情】")
            for i, group in enumerate(self.groups, 1):
                lines.append(f"\n  [第 {i} 组] 哈希: {group.hash_value[:16]}... 大小: {group.size_readable}")
                if group.files and 0 <= group.keep_index < len(group.files):
                    lines.append(f"  建议保留: {group.files[group.keep_index].name}")
                lines.append(f"  以下 {group.duplicate_count} 个文件可删除:")
                for j, f in enumerate(group.files):
                    if j != group.keep_index:
                        lines.append(f"    - {f.name}")
                        lines.append(f"      路径: {f.path}")
        
        lines.append("")
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def save_report(self, filepath: str):
        """保存报告到文件"""
        report = self.generate_report()
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report)


def quick_dedup_check(files: List[FileInfo]) -> List[DuplicateGroup]:
    """
    快速去重检查（便捷函数）
    使用快速模式（文件名+大小+时间签名）快速找出潜在重复
    
    Args:
        files: 文件列表
    
    Returns:
        重复文件组列表
    """
    dedup = FileDeduplicator()
    return dedup.find_duplicates(files, strategy=KeepStrategy.KEEP_NEWEST, quick_mode=True)
