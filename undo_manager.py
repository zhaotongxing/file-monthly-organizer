"""
撤销管理模块 - 记录整理任务历史并支持撤销操作

功能:
    - 记录每次整理任务的完整操作日志
    - 持久化存储到 JSON 文件
    - 支持撤销最近一次任务:
        * 移动操作 → 将文件移回源位置
        * 复制操作 → 删除目标位置的副本
    - 支持查看任务历史摘要
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict, field
from enum import Enum
from i18n import I18n, get_current


class TaskStatus(Enum):
    """任务状态"""
    SUCCESS = "success"
    PARTIAL = "partial"    # 部分成功
    FAILED = "failed"
    UNDONE = "undone"      # 已被撤销


@dataclass
class TaskItem:
    """任务中的单个文件操作记录"""
    source: str            # 源文件路径
    destination: str       # 目标文件路径
    operation: str         # 操作类型: copy / move / preview
    success: bool          # 是否成功
    error: Optional[str] = None
    undone: bool = False   # 是否已被撤销
    undo_error: Optional[str] = None


@dataclass
class TaskRecord:
    """整理任务记录"""
    task_id: str                    # 唯一任务ID
    timestamp: str                  # 执行时间
    source_root: str                # 源根目录
    target_root: str                # 目标根目录
    operation_mode: str             # 操作模式
    folder_format: str              # 文件夹命名格式
    total_files: int                # 总文件数
    success_count: int                # 成功数
    failed_count: int                 # 失败数
    skipped_count: int                # 跳过数
    keyword_subfolder: str = ""       # 关键词子文件夹名称（v1.2+）
    status: str = TaskStatus.SUCCESS.value
    items: List[TaskItem] = field(default_factory=list)
    undone: bool = False              # 整个任务是否已被撤销
    undo_timestamp: Optional[str] = None


class UndoManager:
    """撤销管理器"""
    
    HISTORY_FILE = "organizer_history.json"
    MAX_HISTORY = 50                  # 最多保留50条记录
    
    def __init__(self, history_dir: Optional[str] = None):
        """
        初始化撤销管理器
        
        Args:
            history_dir: 历史文件存储目录，None则使用程序所在目录
        """
        if history_dir is None:
            history_dir = os.path.dirname(os.path.abspath(__file__))
        
        self.history_path = os.path.join(history_dir, self.HISTORY_FILE)
        self.records: List[TaskRecord] = []
        self._load_history()
    
    def _load_history(self):
        """从历史文件加载记录"""
        if os.path.exists(self.history_path):
            try:
                with open(self.history_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.records = [self._dict_to_record(r) for r in data]
            except (json.JSONDecodeError, KeyError, TypeError):
                self.records = []
    
    def _save_history(self):
        """保存历史到文件"""
        try:
            records_data = [self._record_to_dict(r) for r in self.records]
            with open(self.history_path, 'w', encoding='utf-8') as f:
                json.dump(records_data, f, ensure_ascii=False, indent=2)
        except (OSError, PermissionError):
            pass
    
    def _dict_to_record(self, d: dict) -> TaskRecord:
        """字典转任务记录"""
        items = [TaskItem(**item) for item in d.get('items', [])]
        return TaskRecord(
            task_id=d.get('task_id', ''),
            timestamp=d.get('timestamp', ''),
            source_root=d.get('source_root', ''),
            target_root=d.get('target_root', ''),
            operation_mode=d.get('operation_mode', ''),
            folder_format=d.get('folder_format', ''),
            total_files=d.get('total_files', 0),
            success_count=d.get('success_count', 0),
            failed_count=d.get('failed_count', 0),
            skipped_count=d.get('skipped_count', 0),
            keyword_subfolder=d.get('keyword_subfolder', ''),
            status=d.get('status', TaskStatus.SUCCESS.value),
            items=items,
            undone=d.get('undone', False),
            undo_timestamp=d.get('undo_timestamp')
        )
    
    def _record_to_dict(self, r: TaskRecord) -> dict:
        """任务记录转字典"""
        return {
            'task_id': r.task_id,
            'timestamp': r.timestamp,
            'source_root': r.source_root,
            'target_root': r.target_root,
            'operation_mode': r.operation_mode,
            'folder_format': r.folder_format,
            'total_files': r.total_files,
            'success_count': r.success_count,
            'failed_count': r.failed_count,
            'skipped_count': r.skipped_count,
            'keyword_subfolder': r.keyword_subfolder,
            'status': r.status,
            'items': [
                {
                    'source': item.source,
                    'destination': item.destination,
                    'operation': item.operation,
                    'success': item.success,
                    'error': item.error,
                    'undone': item.undone,
                    'undo_error': item.undo_error
                }
                for item in r.items
            ],
            'undone': r.undone,
            'undo_timestamp': r.undo_timestamp
        }
    
    def add_record(self, record: TaskRecord):
        """
        添加任务记录
        
        Args:
            record: 任务记录对象
        """
        self.records.insert(0, record)  # 最新的在前面
        
        # 限制历史数量
        if len(self.records) > self.MAX_HISTORY:
            self.records = self.records[:self.MAX_HISTORY]
        
        self._save_history()
    
    def get_last_record(self) -> Optional[TaskRecord]:
        """获取最近一次成功的、未撤销的任务记录"""
        for record in self.records:
            if not record.undone and record.status != TaskStatus.UNDONE.value:
                return record
        return None
    
    def get_all_records(self) -> List[TaskRecord]:
        """获取所有任务记录"""
        return self.records.copy()
    
    def can_undo(self) -> bool:
        """检查是否可以撤销"""
        last = self.get_last_record()
        if last is None:
            return False
        # 只有实际执行了操作的任务才能撤销（排除纯预览）
        executable_items = [item for item in last.items 
                          if item.operation in ('copy', 'move') and item.success]
        return len(executable_items) > 0
    
    def undo_last_task(self, progress_callback=None) -> dict:
        """
        撤销最近一次任务
        
        Args:
            progress_callback: 进度回调函数(current, total, message)
        
        Returns:
            撤销结果字典
        """
        _ = get_current()
        record = self.get_last_record()
        if record is None:
            return {
                'success': False,
                'error': _.undo_no_task,
                'restored': 0,
                'failed': 0
            }
        
        if record.undone:
            return {
                'success': False,
                'error': _.undo_already_done,
                'restored': 0,
                'failed': 0
            }
        
        restored = 0
        failed = 0
        total = len([item for item in record.items 
                    if item.operation in ('copy', 'move') and item.success])
        
        # 逆向处理（按相反顺序撤销，避免路径依赖问题）
        items_to_undo = [item for item in record.items 
                        if item.operation in ('copy', 'move') and item.success]
        
        for i, item in enumerate(reversed(items_to_undo)):
            if progress_callback:
                progress_callback(i + 1, total, _.undo_progress_name.format(name=os.path.basename(item.source)))
            
            try:
                if item.operation == 'move':
                    # 移动操作的撤销：将文件从目标位置移回源位置
                    undo_result = self._undo_move(item)
                elif item.operation == 'copy':
                    # 复制操作的撤销：删除目标位置的副本
                    undo_result = self._undo_copy(item)
                else:
                    continue
                
                if undo_result:
                    item.undone = True
                    restored += 1
                else:
                    failed += 1
                    
            except Exception as e:
                item.undone = False
                item.undo_error = str(e)
                failed += 1
        
        # 更新任务状态
        if restored > 0:
            record.undone = True
            record.undo_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            record.status = TaskStatus.UNDONE.value
            self._save_history()
        
        return {
            'success': restored > 0,
            'task_id': record.task_id,
            'operation_mode': record.operation_mode,
            'restored': restored,
            'failed': failed,
            'total': total,
            'timestamp': record.timestamp
        }
    
    def _undo_move(self, item: TaskItem) -> bool:
        """
        撤销移动操作：将文件从目标移回源
        
        Returns:
            是否成功
        """
        src = Path(item.destination)   # 当前位置（目标位置）
        dst = Path(item.source)       # 原位置（源位置）
        
        if not src.exists():
            # 文件已不在目标位置，可能已被手动删除或移动
            # 检查是否已经在源位置
            if dst.exists():
                # 文件已在源位置，视为已撤销
                return True
            return False
        
        # 确保源目录存在
        dst.parent.mkdir(parents=True, exist_ok=True)
        
        # 如果源位置已有同名文件，添加后缀避免覆盖
        final_dst = dst
        counter = 1
        _ = get_current()
        suffix_str = _.undo_restored_suffix
        while final_dst.exists() and final_dst != src:
            stem = dst.stem
            suffix = dst.suffix
            final_dst = dst.parent / f"{stem}{suffix_str}{counter}{suffix}"
            counter += 1
        
        # 移动文件
        shutil.move(str(src), str(final_dst))
        return True
    
    def _undo_copy(self, item: TaskItem) -> bool:
        """
        撤销复制操作：删除目标位置的副本
        
        Returns:
            是否成功
        """
        dst = Path(item.destination)
        
        if not dst.exists():
            # 文件已不存在，视为已撤销
            return True
        
        # 删除文件
        dst.unlink()
        
        # 尝试删除空的父文件夹
        try:
            parent = dst.parent
            if parent.exists() and not any(parent.iterdir()):
                parent.rmdir()
        except OSError:
            pass
        
        return True
    
    def clear_history(self):
        """清空所有历史记录"""
        self.records = []
        if os.path.exists(self.history_path):
            try:
                os.remove(self.history_path)
            except OSError:
                pass
    
    def get_summary_text(self) -> str:
        """获取历史摘要文本"""
        _ = get_current()
        if not self.records:
            return _.undo_no_history
        
        lines = []
        lines.append(_.undo_records_total.format(count=len(self.records)))
        lines.append("")
        
        for i, record in enumerate(self.records[:10], 1):  # 只显示最近10条
            status_icon = "✓" if not record.undone else "↩"
            mode_text = {
                'copy': 'copy',
                'move': 'move',
                'preview': 'preview'
            }.get(record.operation_mode, record.operation_mode)
            
            lines.append(f"{status_icon} [{i}] {record.timestamp}")
            
            # 如果有关键词子文件夹，显示出来
            if record.keyword_subfolder:
                lines.append(f"    {_.undo_keyword_label}: 「{record.keyword_subfolder}」")
            
            lines.append(f"    {_.undo_mode_label}: {mode_text} | {_.undo_files_label}: {record.total_files} | "
                        f"{_.undo_success_label}: {record.success_count} | {_.undo_failed_label}: {record.failed_count}")
            
            if record.undone:
                lines.append(f"    {_.undone_at.format(time=record.undo_timestamp)}")
            
            lines.append("")
        
        return "\n".join(lines)


def create_record_from_organizer(
    organizer_results,
    source_root: str,
    target_root: str,
    operation_mode: str,
    folder_format: str,
    keyword_subfolder: str = ""
) -> TaskRecord:
    """
    从Organizer的执行结果创建任务记录
    
    Args:
        organizer_results: organizer.execute_plan() 返回的结果列表
        source_root: 源根目录
        target_root: 目标根目录
        operation_mode: 操作模式
        folder_format: 文件夹命名格式
        keyword_subfolder: 关键词子文件夹名称（v1.2+）
    
    Returns:
        任务记录对象
    """
    from organizer import OperationResult  # 避免循环导入
    
    now = datetime.now()
    
    items = []
    success_count = 0
    failed_count = 0
    skipped_count = 0
    
    for result in organizer_results:
        if result.operation == 'skip':
            skipped_count += 1
            continue
        
        if result.success and result.operation in ('copy', 'move'):
            success_count += 1
        elif not result.success:
            failed_count += 1
        
        items.append(TaskItem(
            source=result.source,
            destination=result.destination or '',
            operation=result.operation,
            success=result.success,
            error=result.error
        ))
    
    # 计算总状态
    if failed_count == 0 and skipped_count == 0:
        status = TaskStatus.SUCCESS.value
    elif success_count > 0:
        status = TaskStatus.PARTIAL.value
    else:
        status = TaskStatus.FAILED.value
    
    return TaskRecord(
        task_id=str(uuid.uuid4())[:8],
        timestamp=now.strftime('%Y-%m-%d %H:%M:%S'),
        source_root=source_root,
        target_root=target_root,
        operation_mode=operation_mode,
        folder_format=folder_format,
        total_files=len(organizer_results),
        success_count=success_count,
        failed_count=failed_count,
        skipped_count=skipped_count,
        keyword_subfolder=keyword_subfolder,
        status=status,
        items=items,
        undone=False
    )
