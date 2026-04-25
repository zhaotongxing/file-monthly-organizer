"""
主题管理模块 - 多主题配色系统

内置主题:
    - 深邃黑 (dark): 深蓝黑科技风
    - 纯净白 (light): 明亮白色简约风
    - 高级灰 (gray): 灰色商务风
    - 薄荷绿 (green): 清新绿色自然风
    - 珊瑚橙 (orange): 暖橙活力风
"""

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class Theme:
    """主题配色数据类"""
    name: str                    # 主题名称
    key: str                     # 主题标识

    # 主背景
    BG_DARK: str
    BG_CARD: str
    BG_CARD_HOVER: str
    BG_INPUT: str
    BG_SIDEBAR: str

    # 强调色
    ACCENT: str
    ACCENT_HOVER: str
    ACCENT_LIGHT: str

    SUCCESS: str
    SUCCESS_HOVER: str

    WARNING: str
    WARNING_HOVER: str

    DANGER: str
    DANGER_HOVER: str

    INFO: str
    INFO_HOVER: str

    # 文字
    TEXT_PRIMARY: str
    TEXT_SECONDARY: str
    TEXT_MUTED: str
    TEXT_ACCENT: str

    # 边框
    BORDER: str
    BORDER_FOCUS: str

    # 表格
    TREE_BG: str
    TREE_SELECTED: str
    TREE_HEADING_BG: str

    # 进度条
    PROGRESS_BG: str
    PROGRESS_FILL: str

    # 滚动条
    SCROLLBAR_BG: str
    SCROLLBAR_FG: str


# ========== 主题定义 ==========

THEME_DARK = Theme(
    name="深邃黑",
    key="dark",
    BG_DARK="#0F172A",
    BG_CARD="#1E293B",
    BG_CARD_HOVER="#26344D",
    BG_INPUT="#0B1221",
    BG_SIDEBAR="#0B1221",
    ACCENT="#3B82F6",
    ACCENT_HOVER="#2563EB",
    ACCENT_LIGHT="#60A5FA",
    SUCCESS="#10B981",
    SUCCESS_HOVER="#059669",
    WARNING="#F59E0B",
    WARNING_HOVER="#D97706",
    DANGER="#EF4444",
    DANGER_HOVER="#DC2626",
    INFO="#8B5CF6",
    INFO_HOVER="#7C3AED",
    TEXT_PRIMARY="#F1F5F9",
    TEXT_SECONDARY="#94A3B8",
    TEXT_MUTED="#64748B",
    TEXT_ACCENT="#38BDF8",
    BORDER="#334155",
    BORDER_FOCUS="#3B82F6",
    TREE_BG="#1E293B",
    TREE_SELECTED="#3B82F6",
    TREE_HEADING_BG="#26344D",
    PROGRESS_BG="#334155",
    PROGRESS_FILL="#3B82F6",
    SCROLLBAR_BG="#1E293B",
    SCROLLBAR_FG="#475569",
)

THEME_LIGHT = Theme(
    name="纯净白",
    key="light",
    BG_DARK="#F8FAFC",
    BG_CARD="#FFFFFF",
    BG_CARD_HOVER="#F1F5F9",
    BG_INPUT="#F1F5F9",
    BG_SIDEBAR="#F1F5F9",
    ACCENT="#2563EB",
    ACCENT_HOVER="#1D4ED8",
    ACCENT_LIGHT="#3B82F6",
    SUCCESS="#059669",
    SUCCESS_HOVER="#047857",
    WARNING="#D97706",
    WARNING_HOVER="#B45309",
    DANGER="#DC2626",
    DANGER_HOVER="#B91C1C",
    INFO="#7C3AED",
    INFO_HOVER="#6D28D9",
    TEXT_PRIMARY="#0F172A",
    TEXT_SECONDARY="#475569",
    TEXT_MUTED="#94A3B8",
    TEXT_ACCENT="#2563EB",
    BORDER="#E2E8F0",
    BORDER_FOCUS="#3B82F6",
    TREE_BG="#FFFFFF",
    TREE_SELECTED="#2563EB",
    TREE_HEADING_BG="#F1F5F9",
    PROGRESS_BG="#E2E8F0",
    PROGRESS_FILL="#2563EB",
    SCROLLBAR_BG="#F1F5F9",
    SCROLLBAR_FG="#CBD5E1",
)

THEME_GRAY = Theme(
    name="高级灰",
    key="gray",
    BG_DARK="#E8ECEF",
    BG_CARD="#F5F7F9",
    BG_CARD_HOVER="#EDEEF1",
    BG_INPUT="#FFFFFF",
    BG_SIDEBAR="#DEE2E6",
    ACCENT="#495057",
    ACCENT_HOVER="#343A40",
    ACCENT_LIGHT="#6C757D",
    SUCCESS="#2E7D52",
    SUCCESS_HOVER="#1B5E3A",
    WARNING="#C27D16",
    WARNING_HOVER="#9E6410",
    DANGER="#B71C1C",
    DANGER_HOVER="#8E1515",
    INFO="#5C3D8A",
    INFO_HOVER="#4A2F70",
    TEXT_PRIMARY="#212529",
    TEXT_SECONDARY="#495057",
    TEXT_MUTED="#868E96",
    TEXT_ACCENT="#495057",
    BORDER="#CED4DA",
    BORDER_FOCUS="#495057",
    TREE_BG="#F5F7F9",
    TREE_SELECTED="#495057",
    TREE_HEADING_BG="#E8ECEF",
    PROGRESS_BG="#CED4DA",
    PROGRESS_FILL="#495057",
    SCROLLBAR_BG="#E8ECEF",
    SCROLLBAR_FG="#ADB5BD",
)

THEME_GREEN = Theme(
    name="薄荷绿",
    key="green",
    BG_DARK="#ECFDF5",
    BG_CARD="#F0FDF4",
    BG_CARD_HOVER="#DCFCE7",
    BG_INPUT="#FFFFFF",
    BG_SIDEBAR="#D1FAE5",
    ACCENT="#059669",
    ACCENT_HOVER="#047857",
    ACCENT_LIGHT="#10B981",
    SUCCESS="#059669",
    SUCCESS_HOVER="#047857",
    WARNING="#D97706",
    WARNING_HOVER="#B45309",
    DANGER="#DC2626",
    DANGER_HOVER="#B91C1C",
    INFO="#6366F1",
    INFO_HOVER="#4F46E5",
    TEXT_PRIMARY="#064E3B",
    TEXT_SECONDARY="#065F46",
    TEXT_MUTED="#6B7280",
    TEXT_ACCENT="#059669",
    BORDER="#A7F3D0",
    BORDER_FOCUS="#059669",
    TREE_BG="#F0FDF4",
    TREE_SELECTED="#059669",
    TREE_HEADING_BG="#DCFCE7",
    PROGRESS_BG="#A7F3D0",
    PROGRESS_FILL="#059669",
    SCROLLBAR_BG="#D1FAE5",
    SCROLLBAR_FG="#6EE7B7",
)

THEME_ORANGE = Theme(
    name="珊瑚橙",
    key="orange",
    BG_DARK="#FFF7ED",
    BG_CARD="#FFFAF5",
    BG_CARD_HOVER="#FFF1E6",
    BG_INPUT="#FFFFFF",
    BG_SIDEBAR="#FFE8D6",
    ACCENT="#EA580C",
    ACCENT_HOVER="#C2410C",
    ACCENT_LIGHT="#F97316",
    SUCCESS="#15803D",
    SUCCESS_HOVER="#166534",
    WARNING="#CA8A04",
    WARNING_HOVER="#A16207",
    DANGER="#DC2626",
    DANGER_HOVER="#B91C1C",
    INFO="#7C3AED",
    INFO_HOVER="#6D28D9",
    TEXT_PRIMARY="#431407",
    TEXT_SECONDARY="#7C2D12",
    TEXT_MUTED="#9A3412",
    TEXT_ACCENT="#EA580C",
    BORDER="#FED7AA",
    BORDER_FOCUS="#EA580C",
    TREE_BG="#FFFAF5",
    TREE_SELECTED="#EA580C",
    TREE_HEADING_BG="#FFF1E6",
    PROGRESS_BG="#FED7AA",
    PROGRESS_FILL="#EA580C",
    SCROLLBAR_BG="#FFE8D6",
    SCROLLBAR_FG="#FDBA74",
)

# 所有可用主题
ALL_THEMES: Dict[str, Theme] = {
    "dark": THEME_DARK,
    "light": THEME_LIGHT,
    "gray": THEME_GRAY,
    "green": THEME_GREEN,
    "orange": THEME_ORANGE,
}

# 默认主题
DEFAULT_THEME = "dark"


class ThemeManager:
    """主题管理器 - 负责主题的切换和应用"""

    def __init__(self, initial_theme: str = DEFAULT_THEME):
        self._current_key = initial_theme
        self._theme = ALL_THEMES.get(initial_theme, THEME_DARK)
        self._observers = []

    @property
    def theme(self) -> Theme:
        return self._theme

    @property
    def current_key(self) -> str:
        return self._current_key

    def set_theme(self, key: str):
        """切换主题"""
        if key in ALL_THEMES:
            self._current_key = key
            self._theme = ALL_THEMES[key]
            self._notify_observers()

    def get_theme_names(self) -> Dict[str, str]:
        """获取所有主题名称映射 {key: name}"""
        return {key: t.name for key, t in ALL_THEMES.items()}

    def register_observer(self, callback):
        """注册主题变更观察者"""
        self._observers.append(callback)

    def _notify_observers(self):
        """通知所有观察者主题已变更"""
        for cb in self._observers:
            try:
                cb(self._theme)
            except Exception:
                pass


# 全局主题管理器实例
_theme_manager = ThemeManager()


def get_theme_manager() -> ThemeManager:
    """获取全局主题管理器"""
    return _theme_manager
