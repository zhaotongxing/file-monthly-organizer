"""
文件整理器模块 - 负责将文件按月分类并移动到目标文件夹
"""

import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

from scanner import FileInfo
from i18n import get_current


class OperationMode(Enum):
    """操作模式"""
    PREVIEW = "preview"      # 仅预览，不执行任何操作
    COPY = "copy"            # 复制文件
    MOVE = "move"            # 移动文件


@dataclass
class OperationResult:
    """操作结果"""
    success: bool
    source: str
    destination: Optional[str] = None
    error: Optional[str] = None
    operation: str = ""  # 'copy', 'move', 'skip'


@dataclass
class OrganizePlan:
    """整理计划"""
    source_file: FileInfo
    target_folder: str      # 目标月份文件夹
    target_path: str        # 目标完整路径
    operation: str          # 'copy' 或 'move'
    will_overwrite: bool    # 是否会覆盖已有文件
    status: str = "pending" # 'pending', 'success', 'failed', 'skipped'
    result_message: str = ""


class FileOrganizer:
    """文件整理器类"""
    
    def __init__(self):
        self.plans: List[OrganizePlan] = []
        self.results: List[OperationResult] = []
        self._stop_flag = False
        self.current_progress = 0
        self.last_source_root: str = ""        # 最后一次整理的源根目录
        self.last_target_root: str = ""        # 最后一次整理的目标根目录
        self.last_operation_mode: str = ""     # 最后一次操作模式
        self.last_folder_format: str = ""      # 最后一次文件夹格式
        self.last_keyword_subfolder: str = ""  # 最后一次关键词子文件夹
    
    def stop(self):
        """停止操作"""
        self._stop_flag = True
    
    def reset(self):
        """重置状态（保留上次任务参数用于撤销记录）"""
        self.plans = []
        self.results = []
        self._stop_flag = False
        self.current_progress = 0
        # 注意: 不重置 last_source_root 等字段，供撤销使用
    
    def create_plan(
        self,
        files: List[FileInfo],
        target_root: str,
        operation: OperationMode = OperationMode.COPY,
        folder_format: str = "{year_month}",
        source_root: str = "",
        keyword_subfolder: str = ""
    ) -> List[OrganizePlan]:
        """
        创建整理计划（支持任意文件列表，包括搜索结果）
        
        Args:
            files: 要整理的文件列表（可以是全部文件或搜索过滤后的子集）
            target_root: 目标根目录
            operation: 操作模式
            folder_format: 文件夹命名格式，支持 {year}, {month}, {year_month}
            source_root: 源根目录（用于撤销记录）
            keyword_subfolder: 关键词子文件夹名称（仅整理搜索结果时使用）
        
        Returns:
            整理计划列表
        """
        self.reset()
        self.last_source_root = source_root
        self.last_target_root = target_root
        self.last_operation_mode = operation.value if isinstance(operation, OperationMode) else str(operation)
        self.last_folder_format = folder_format
        self.last_keyword_subfolder = keyword_subfolder
        
        target_root_path = Path(target_root)
        
        # 如果指定了关键词子文件夹，先加入路径
        if keyword_subfolder:
            target_root_path = target_root_path / keyword_subfolder
        
        for file_info in files:
            # 解析年月
            year, month = file_info.year_month.split('-')
            
            # 格式化文件夹名称
            folder_name = folder_format.format(
                year=year,
                month=month,
                year_month=file_info.year_month
            )
            
            # 目标文件夹路径
            target_folder = target_root_path / folder_name
            
            # 目标文件路径
            target_path = target_folder / file_info.name
            
            # 检查是否会覆盖
            will_overwrite = target_path.exists()
            
            plan = OrganizePlan(
                source_file=file_info,
                target_folder=str(target_folder),
                target_path=str(target_path),
                operation=operation.value if operation != OperationMode.PREVIEW else "preview",
                will_overwrite=will_overwrite
            )
            
            self.plans.append(plan)
        
        return self.plans
    
    def execute_plan(
        self,
        plans: Optional[List[OrganizePlan]] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        skip_existing: bool = True
    ) -> List[OperationResult]:
        """
        执行整理计划
        
        Args:
            plans: 要执行的计划列表，None则使用已创建的计划
            progress_callback: 进度回调(当前数, 总数, 状态信息)
            skip_existing: 是否跳过已存在的文件
        
        Returns:
            操作结果列表
        """
        if plans is None:
            plans = self.plans
        
        self.results = []
        total = len(plans)
        
        for i, plan in enumerate(plans):
            if self._stop_flag:
                plan.status = "skipped"
                plan.result_message = "用户取消"
                continue
            
            self.current_progress = i + 1
            
            # 报告进度
            if progress_callback:
                progress_callback(i + 1, total, f"正在处理: {plan.source_file.name}")
            
            # 如果是预览模式，仅标记为成功
            if plan.operation == "preview":
                plan.status = "preview"
                plan.result_message = "预览模式 - 未执行"
                self.results.append(OperationResult(
                    success=True,
                    source=plan.source_file.path,
                    destination=plan.target_path,
                    operation="preview"
                ))
                continue
            
            # 创建目标文件夹
            try:
                Path(plan.target_folder).mkdir(parents=True, exist_ok=True)
            except OSError as e:
                plan.status = "failed"
                plan.result_message = f"无法创建文件夹: {e}"
                self.results.append(OperationResult(
                    success=False,
                    source=plan.source_file.path,
                    error=str(e),
                    operation=plan.operation
                ))
                continue
            
            # 检查目标文件是否已存在
            if Path(plan.target_path).exists() and skip_existing:
                plan.status = "skipped"
                _ = get_current()
                plan.result_message = _.organizer_target_exists
                self.results.append(OperationResult(
                    success=True,
                    source=plan.source_file.path,
                    destination=plan.target_path,
                    operation="skip"
                ))
                continue
            
            # 执行文件操作
            try:
                if plan.operation == "copy":
                    shutil.copy2(plan.source_file.path, plan.target_path)
                    plan.status = "success"
                    _ = get_current()
                    plan.result_message = _.organizer_copy_ok
                    self.results.append(OperationResult(
                        success=True,
                        source=plan.source_file.path,
                        destination=plan.target_path,
                        operation="copy"
                    ))
                    
                elif plan.operation == "move":
                    # 如果目标已存在，先删除
                    if Path(plan.target_path).exists():
                        os.remove(plan.target_path)
                    shutil.move(plan.source_file.path, plan.target_path)
                    plan.status = "success"
                    _ = get_current()
                    plan.result_message = _.organizer_move_ok
                    self.results.append(OperationResult(
                        success=True,
                        source=plan.source_file.path,
                        destination=plan.target_path,
                        operation="move"
                    ))
                    
            except (shutil.Error, OSError, PermissionError) as e:
                plan.status = "failed"
                _ = get_current()
                plan.result_message = _.organizer_op_failed.format(error=e)
                self.results.append(OperationResult(
                    success=False,
                    source=plan.source_file.path,
                    error=str(e),
                    operation=plan.operation
                ))
        
        if progress_callback:
            progress_callback(total, total, "处理完成")
        
        return self.results
    
    def get_summary(self) -> Dict:
        """获取执行摘要"""
        if not self.results:
            return {
                'total': 0,
                'success': 0,
                'failed': 0,
                'skipped': 0,
                'preview': 0
            }
        
        success = sum(1 for r in self.results if r.success and r.operation not in ['skip', 'preview'])
        failed = sum(1 for r in self.results if not r.success)
        skipped = sum(1 for r in self.results if r.operation == 'skip')
        preview = sum(1 for r in self.results if r.operation == 'preview')
        
        return {
            'total': len(self.results),
            'success': success,
            'failed': failed,
            'skipped': skipped,
            'preview': preview
        }
    
    def generate_report(self) -> str:
        """生成详细的操作报告"""
        lines = []
        lines.append("=" * 60)
        lines.append("文件整理报告")
        lines.append("=" * 60)
        lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # 统计信息
        summary = self.get_summary()
        lines.append("【统计摘要】")
        lines.append(f"  总计: {summary['total']} 个文件")
        lines.append(f"  成功: {summary['success']} 个")
        lines.append(f"  失败: {summary['failed']} 个")
        lines.append(f"  跳过: {summary['skipped']} 个")
        lines.append(f"  预览: {summary['preview']} 个")
        lines.append("")
        
        # 详细记录
        if self.results:
            lines.append("【详细记录】")
            for i, result in enumerate(self.results, 1):
                status = "成功" if result.success else "失败"
                if result.operation == 'skip':
                    status = "跳过"
                elif result.operation == 'preview':
                    status = "预览"
                
                lines.append(f"\n  [{i}] {status} - {result.operation}")
                lines.append(f"      源: {result.source}")
                if result.destination:
                    lines.append(f"      目标: {result.destination}")
                if result.error:
                    lines.append(f"      错误: {result.error}")
        
        lines.append("")
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def save_report(self, filepath: str):
        """保存报告到文件"""
        report = self.generate_report()
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report)
