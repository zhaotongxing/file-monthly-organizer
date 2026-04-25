"""
搜索模块 - 按关键词过滤文件列表

支持功能:
    - 多关键词搜索（空格/逗号分隔）
    - AND / OR 逻辑模式
    - 文件名 / 文件路径 / 扩展名 匹配范围
    - 正则表达式支持（可选）
    - 大小写敏感选项
"""

import re
from typing import List, Optional, Callable
from dataclasses import dataclass
from enum import Enum, auto

from scanner import FileInfo


class MatchMode(Enum):
    """匹配逻辑模式"""
    AND = auto()   # 所有关键词都必须匹配
    OR = auto()    # 任一关键词匹配即可


class MatchScope(Enum):
    """匹配范围"""
    FILENAME = auto()      # 仅匹配文件名（不含扩展名）
    FULLNAME = auto()      # 匹配完整文件名（含扩展名）
    EXTENSION = auto()     # 仅匹配扩展名
    PATH = auto()          # 匹配完整路径
    ALL = auto()           # 匹配文件名和路径


class KeywordSearcher:
    """关键词搜索器"""
    
    def __init__(self):
        self.keywords: List[str] = []
        self.match_mode: MatchMode = MatchMode.OR
        self.match_scope: MatchScope = MatchScope.ALL
        self.case_sensitive: bool = False
        self.use_regex: bool = False
        self.compiled_patterns: List[re.Pattern] = []
    
    def set_keywords(
        self,
        keywords_text: str,
        delimiter: Optional[str] = None
    ) -> List[str]:
        """
        设置关键词列表
        
        Args:
            keywords_text: 关键词文本，如 "合同 2024" 或 "合同,发票,报告"
            delimiter: 分隔符，None则自动检测（空格或逗号）
        
        Returns:
            解析后的关键词列表
        """
        if not keywords_text or not keywords_text.strip():
            self.keywords = []
            return []
        
        text = keywords_text.strip()
        
        # 自动检测分隔符
        if delimiter is None:
            if ',' in text or '，' in text:
                # 使用逗号分隔
                text = text.replace('，', ',')
                parts = text.split(',')
            else:
                # 使用空格分隔
                parts = text.split()
        else:
            parts = text.split(delimiter)
        
        # 清理关键词
        self.keywords = [kw.strip() for kw in parts if kw.strip()]
        
        # 预编译正则表达式
        self._compile_patterns()
        
        return self.keywords
    
    def _compile_patterns(self):
        """预编译正则表达式模式"""
        self.compiled_patterns = []
        for kw in self.keywords:
            try:
                if self.use_regex:
                    flags = 0 if self.case_sensitive else re.IGNORECASE
                    pattern = re.compile(kw, flags)
                else:
                    # 转义特殊字符，作为普通文本匹配
                    escaped = re.escape(kw)
                    flags = 0 if self.case_sensitive else re.IGNORECASE
                    pattern = re.compile(escaped, flags)
                self.compiled_patterns.append(pattern)
            except re.error:
                # 如果正则编译失败，作为普通文本处理
                escaped = re.escape(kw)
                flags = 0 if self.case_sensitive else re.IGNORECASE
                pattern = re.compile(escaped, flags)
                self.compiled_patterns.append(pattern)
    
    def configure(
        self,
        match_mode: MatchMode = MatchMode.OR,
        match_scope: MatchScope = MatchScope.ALL,
        case_sensitive: bool = False,
        use_regex: bool = False
    ):
        """配置搜索选项"""
        self.match_mode = match_mode
        self.match_scope = match_scope
        self.case_sensitive = case_sensitive
        self.use_regex = use_regex
        self._compile_patterns()
    
    def _get_match_text(self, file_info: FileInfo) -> str:
        """根据匹配范围获取要匹配的文本"""
        if self.match_scope == MatchScope.FILENAME:
            # 去除扩展名
            name = file_info.name
            if '.' in name:
                return name.rsplit('.', 1)[0]
            return name
        
        elif self.match_scope == MatchScope.FULLNAME:
            return file_info.name
        
        elif self.match_scope == MatchScope.EXTENSION:
            return file_info.extension
        
        elif self.match_scope == MatchScope.PATH:
            return file_info.path
        
        elif self.match_scope == MatchScope.ALL:
            return f"{file_info.name} {file_info.path}"
        
        return file_info.name
    
    def match(self, file_info: FileInfo) -> bool:
        """
        判断文件是否匹配关键词
        
        Args:
            file_info: 文件信息对象
        
        Returns:
            是否匹配
        """
        if not self.keywords or not self.compiled_patterns:
            return True  # 无关键词时全部匹配
        
        match_text = self._get_match_text(file_info)
        
        if self.match_mode == MatchMode.AND:
            # AND模式：所有关键词都必须匹配
            for pattern in self.compiled_patterns:
                if not pattern.search(match_text):
                    return False
            return True
        
        else:  # MatchMode.OR
            # OR模式：任一关键词匹配即可
            for pattern in self.compiled_patterns:
                if pattern.search(match_text):
                    return True
            return False
    
    def search(self, files: List[FileInfo]) -> List[FileInfo]:
        """
        在文件列表中搜索匹配的文件
        
        Args:
            files: 文件列表
        
        Returns:
            匹配的文件列表
        """
        if not self.keywords:
            return files
        
        return [f for f in files if self.match(f)]
    
    def search_with_highlight(
        self,
        files: List[FileInfo]
    ) -> tuple[List[FileInfo], dict]:
        """
        搜索并返回匹配结果及匹配详情
        
        Args:
            files: 文件列表
        
        Returns:
            (匹配的文件列表, 匹配详情字典)
            匹配详情格式: {file_path: [matched_keyword1, ...]}
        """
        if not self.keywords:
            return files, {f.path: [] for f in files}
        
        matched_files = []
        match_details = {}
        
        for file_info in files:
            match_text = self._get_match_text(file_info)
            matched_keywords = []
            
            for pattern in self.compiled_patterns:
                if pattern.search(match_text):
                    matched_keywords.append(pattern.pattern)
            
            if matched_keywords:
                if self.match_mode == MatchMode.AND:
                    # AND模式需要所有关键词都匹配
                    if len(matched_keywords) == len(self.keywords):
                        matched_files.append(file_info)
                        match_details[file_info.path] = self.keywords.copy()
                else:
                    matched_files.append(file_info)
                    match_details[file_info.path] = matched_keywords
        
        return matched_files, match_details
    
    def get_match_positions(
        self,
        text: str
    ) -> List[tuple]:
        """
        获取关键词在文本中的匹配位置（用于高亮显示）
        
        Args:
            text: 要搜索的文本
        
        Returns:
            匹配位置列表 [(start, end, keyword), ...]
        """
        positions = []
        for pattern in self.compiled_patterns:
            for match in pattern.finditer(text):
                positions.append((match.start(), match.end(), pattern.pattern))
        return positions


class SearchHistory:
    """搜索历史管理"""
    
    def __init__(self, max_history: int = 20):
        self.history: List[str] = []
        self.max_history = max_history
    
    def add(self, keywords_text: str):
        """添加搜索记录"""
        if not keywords_text or not keywords_text.strip():
            return
        
        # 移除重复项
        if keywords_text in self.history:
            self.history.remove(keywords_text)
        
        # 添加到开头
        self.history.insert(0, keywords_text)
        
        # 限制数量
        if len(self.history) > self.max_history:
            self.history = self.history[:self.max_history]
    
    def get_all(self) -> List[str]:
        """获取所有历史记录"""
        return self.history.copy()
    
    def clear(self):
        """清空历史"""
        self.history = []


def quick_search(
    files: List[FileInfo],
    keywords: str,
    scope: MatchScope = MatchScope.ALL,
    mode: MatchMode = MatchMode.OR
) -> List[FileInfo]:
    """
    快速搜索函数（便捷方法）
    
    Args:
        files: 文件列表
        keywords: 关键词文本
        scope: 匹配范围
        mode: 匹配模式
    
    Returns:
        匹配的文件列表
    """
    searcher = KeywordSearcher()
    searcher.set_keywords(keywords)
    searcher.configure(match_mode=mode, match_scope=scope)
    return searcher.search(files)
