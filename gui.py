"""
GUI界面模块 - 英汉双语版 (v2.3)
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from datetime import datetime
from typing import Optional, List

from config import APP_CONFIG, FILE_TYPE_GROUPS, SEARCH_CONFIG, CATEGORY_GROUPS
from scanner import FileScanner, FileInfo
from organizer import FileOrganizer, OperationMode
from searcher import KeywordSearcher, MatchMode, MatchScope, SearchHistory
from undo_manager import UndoManager, create_record_from_organizer
from deduplicator import FileDeduplicator, KeepStrategy
from utils import format_file_size, is_valid_source_dir, is_valid_target_dir
from i18n import I18n, get_current, set_language, UN_LANGUAGES, get_font_for_lang


# ========== 薄荷绿配色 ==========
class T:
    BG_DARK = "#ECFDF5"
    BG_CARD = "#F0FDF4"
    BG_CARD_HOVER = "#DCFCE7"
    BG_INPUT = "#FFFFFF"
    BG_SIDEBAR = "#D1FAE5"
    ACCENT = "#059669"
    ACCENT_HOVER = "#047857"
    ACCENT_LIGHT = "#10B981"
    SUCCESS = "#059669"
    SUCCESS_HOVER = "#047857"
    WARNING = "#D97706"
    WARNING_HOVER = "#B45309"
    DANGER = "#DC2626"
    DANGER_HOVER = "#B91C1C"
    INFO = "#6366F1"
    INFO_HOVER = "#4F46E5"
    TEXT_PRIMARY = "#064E3B"
    TEXT_SECONDARY = "#065F46"
    TEXT_MUTED = "#6B7280"
    TEXT_ACCENT = "#059669"
    BORDER = "#A7F3D0"
    BORDER_FOCUS = "#059669"
    TREE_BG = "#F0FDF4"
    TREE_SELECTED = "#059669"
    TREE_HEADING_BG = "#DCFCE7"
    PROGRESS_BG = "#A7F3D0"
    PROGRESS_FILL = "#059669"


class Fonts:
    """字体配置 - Segoe UI 为基底，兼容拉丁/西里尔/阿拉伯字符
    语言切换时通过 _update_all_fonts() 批量更新 widget 字体"""
    _CURRENT_FAMILY = "Segoe UI"

    # 中文优先使用微软雅黑
    CJK_FAMILY = "Microsoft YaHei UI"
    ARABIC_FAMILY = "Segoe UI"
    FALLBACK = "Arial"

    @classmethod
    def refresh(cls):
        """根据当前语言刷新字体族"""
        from i18n import get_current
        lang = get_current().lang
        if lang == "zh":
            cls._CURRENT_FAMILY = cls.CJK_FAMILY
        elif lang == "ar":
            cls._CURRENT_FAMILY = cls.ARABIC_FAMILY
        else:
            cls._CURRENT_FAMILY = "Segoe UI"
        cls._refresh_constants()

    @classmethod
    def _refresh_constants(cls):
        f = cls._CURRENT_FAMILY
        cls.FAMILY = f
        cls.TITLE = (f, 22, "bold")
        cls.SUBTITLE = (f, 14, "bold")
        cls.HEADING = (f, 12, "bold")
        cls.BODY = (f, 11)
        cls.BODY_LARGE = (f, 12)
        cls.SMALL = (f, 10)
        cls.BUTTON = (f, 12, "bold")
        cls.BUTTON_LARGE = (f, 13, "bold")
        cls.MONO = ("Consolas", 10)


# 初始化
Fonts.refresh()


class FileOrganizerApp:
    """文件整理器主应用 - 英汉双语"""

    def __init__(self, root: tk.Tk):
        self.root = root
        self._ = get_current()
        self._setup_window()
        self._init_modules()
        self._init_vars()
        self._build_ui()

    def _str(self, key: str, **kwargs) -> str:
        """获取当前语言文本"""
        return self._.get(key, **kwargs)

    def _setup_window(self):
        self.root.title(self._str("app_title"))
        self.root.geometry("1100x850")
        self.root.minsize(950, 700)
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass

    def _init_modules(self):
        self.scanner = FileScanner()
        self.organizer = FileOrganizer()
        self.searcher = KeywordSearcher()
        self.search_history = SearchHistory(SEARCH_CONFIG['max_history'])
        self.undo_manager = UndoManager()
        self.deduplicator = FileDeduplicator()

    def _init_vars(self):
        self.all_files: List[FileInfo] = []
        self.displayed_files: List[FileInfo] = []
        self.is_filtered = False
        self.dup_groups = []

        self.source_path = tk.StringVar()
        self.target_path = tk.StringVar()
        self.operation_mode = tk.StringVar(value="copy")
        self.recursive_scan = tk.BooleanVar(value=True)
        self.skip_existing = tk.BooleanVar(value=True)
        self.folder_format = tk.StringVar(value=self._str("fmt_ym", year="", month="").replace("-", "{year}-{month}").replace("_", "{year}_{month}"))
        # 重新设为正确默认值
        self.folder_format.set("{year}年{month}月" if self._.lang == "zh" else "{year}-{month}")
        self.search_keywords = tk.StringVar()
        self.search_mode = tk.StringVar(value="OR")
        self.search_scope = tk.StringVar(value="ALL")
        self.search_case_sensitive = tk.BooleanVar(value=False)
        self.search_use_regex = tk.BooleanVar(value=False)
        self.search_only_organized = tk.BooleanVar(value=False)
        self.scan_office = tk.BooleanVar(value=True)
        self.scan_image = tk.BooleanVar(value=True)
        self.scan_video = tk.BooleanVar(value=True)
        self.dedup_strategy = tk.StringVar(value="newest")

    # ===== 控件工厂 =====
    def _btn(self, parent, text_key, cmd, c, h, fg="white", font=None, padx=20, pady=8, width=None, **fmt):
        text = self._str(text_key, **fmt) if text_key else ""
        if font is None:
            font = Fonts.BUTTON
        btn = tk.Label(parent, text=text, bg=getattr(T, c), fg=fg,
                       font=font, cursor="hand2", padx=padx, pady=pady,
                       relief=tk.FLAT, width=width)
        btn.bind("<Button-1>", lambda e: cmd())
        btn.bind("<Enter>", lambda e: btn.config(bg=getattr(T, h)))
        btn.bind("<Leave>", lambda e: btn.config(bg=getattr(T, c)))
        return btn

    def _entry(self, parent, var, **kw):
        d = {
            'font': Fonts.BODY_LARGE, 'bg': T.BG_INPUT, 'fg': T.TEXT_PRIMARY,
            'relief': tk.FLAT, 'highlightbackground': T.BORDER,
            'highlightthickness': 1, 'insertbackground': T.TEXT_PRIMARY
        }
        d.update(kw)
        e = tk.Entry(parent, textvariable=var, **d)
        e.bind("<FocusIn>", lambda ev, ent=e: ent.config(highlightbackground=T.BORDER_FOCUS))
        e.bind("<FocusOut>", lambda ev, ent=e: ent.config(highlightbackground=T.BORDER))
        return e

    def _card(self, parent, title_key=None, **fmt):
        card = tk.Frame(parent, bg=T.BG_CARD,
                        highlightbackground=T.BORDER,
                        highlightthickness=1, relief=tk.FLAT)
        if title_key:
            hdr = tk.Frame(card, bg=T.BG_CARD)
            hdr.pack(fill=tk.X, padx=16, pady=(12, 0))
            bar = tk.Frame(hdr, bg=T.ACCENT, width=4, height=18)
            bar.pack(side=tk.LEFT, padx=(0, 8))
            tk.Label(hdr, text=self._str(title_key, **fmt),
                     bg=T.BG_CARD, fg=T.TEXT_PRIMARY,
                     font=Fonts.SUBTITLE).pack(side=tk.LEFT)
        return card

    # ===== 语言切换 =====
    def _switch_lang(self, lang: str):
        if not set_language(lang):
            return
        self._ = get_current()
        Fonts.refresh()  # 刷新字体配置
        # 保存状态
        state = self._save_ui_state()
        # 重建 UI
        for w in self.root.winfo_children():
            w.destroy()
        self._setup_window()
        self._init_vars()
        self._build_ui()
        self._restore_ui_state(state)
        self._log(self._str("lang_switched", lang=lang.upper()))

    def _save_ui_state(self):
        tab_idx = 0
        if hasattr(self, 'notebook') and self.notebook.winfo_exists():
            try:
                tab_idx = self.notebook.index(self.notebook.select())
            except:
                pass
        return {
            'source': self.source_path.get(),
            'target': self.target_path.get(),
            'operation': self.operation_mode.get(),
            'recursive': self.recursive_scan.get(),
            'skip': self.skip_existing.get(),
            'folder_fmt': self.folder_format.get(),
            'search_kw': self.search_keywords.get(),
            'search_mode': self.search_mode.get(),
            'search_scope': self.search_scope.get(),
            'case': self.search_case_sensitive.get(),
            'regex': self.search_use_regex.get(),
            'only_results': self.search_only_organized.get(),
            'office': self.scan_office.get(),
            'image': self.scan_image.get(),
            'video': self.scan_video.get(),
            'dedup_strat': self.dedup_strategy.get(),
            'tab_idx': tab_idx,
            'log': self.log_text.get(1.0, tk.END) if hasattr(self, 'log_text') else "",
            'all_files': self.all_files,
            'displayed_files': self.displayed_files,
            'is_filtered': self.is_filtered,
            'dup_groups': self.dup_groups,
            'filter_showing': self.filter_frame.winfo_ismapped() if hasattr(self, 'filter_frame') else False,
            'filter_text': self.filter_label.cget('text') if hasattr(self, 'filter_label') else "",
        }

    def _restore_ui_state(self, state):
        self.source_path.set(state['source'])
        self.target_path.set(state['target'])
        self.operation_mode.set(state['operation'])
        self.recursive_scan.set(state['recursive'])
        self.skip_existing.set(state['skip'])
        self.folder_format.set(state['folder_fmt'])
        self.search_keywords.set(state['search_kw'])
        self.search_mode.set(state['search_mode'])
        self.search_scope.set(state['search_scope'])
        self.search_case_sensitive.set(state['case'])
        self.search_use_regex.set(state['regex'])
        self.search_only_organized.set(state['only_results'])
        self.scan_office.set(state['office'])
        self.scan_image.set(state['image'])
        self.scan_video.set(state['video'])
        self.dedup_strategy.set(state['dedup_strat'])

        self.all_files = state['all_files']
        self.displayed_files = state['displayed_files']
        self.is_filtered = state['is_filtered']
        self.dup_groups = state['dup_groups']

        if self.all_files:
            self._refresh_file_list(self.displayed_files)
            self._update_stats(self.scanner.get_statistics())
        if self.dup_groups:
            self._refresh_dup_tree()

        if state['log']:
            self.log_text.insert(tk.END, state['log'])

        if state['filter_showing'] and hasattr(self, 'filter_label'):
            self.filter_label.config(text=state['filter_text'])
            self.filter_frame.pack(fill=tk.X, pady=(0, 12))

        if hasattr(self, 'notebook'):
            try:
                self.notebook.select(state['tab_idx'])
            except:
                pass

    # ===== 构建 UI =====
    def _build_ui(self):
        self.root.configure(bg=T.BG_DARK)
        main = tk.Frame(self.root, bg=T.BG_DARK)
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)

        self._build_header(main)

        path_card = self._card(main, "card_path")
        path_card.pack(fill=tk.X, pady=(0, 12))
        self._build_path_section(path_card)

        search_card = self._card(main, "card_search")
        search_card.pack(fill=tk.X, pady=(0, 12))
        self._build_search_section(search_card)

        opts_card = self._card(main, "card_options")
        opts_card.pack(fill=tk.X, pady=(0, 12))
        self._build_options_section(opts_card)

        self._build_action_buttons(main)
        self._build_progress(main)
        self._build_status_bar(main)
        self._build_filter_bar(main)

        self.notebook = ttk.Notebook(main, style="TNotebook")
        self._style_notebook()
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self._build_file_list_tab()
        self._build_stats_tab()
        self._build_dedup_tab()
        self._build_history_tab()
        self._build_log_tab()

    def _style_notebook(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.layout('TNotebook', style.layout('TNotebook'))
        style.layout('TNotebook.Tab', style.layout('TNotebook.Tab'))
        style.configure("TNotebook", background=T.BG_DARK, tabmargins=[2, 5, 2, 0])
        style.configure("TNotebook.Tab", font=Fonts.HEADING,
                        background=T.BG_CARD, foreground=T.TEXT_SECONDARY,
                        padding=[16, 8], borderwidth=0, focuscolor=T.ACCENT)
        style.map("TNotebook.Tab",
                  background=[("selected", T.ACCENT), ("active", T.BG_CARD_HOVER)],
                  foreground=[("selected", "white"), ("active", T.TEXT_PRIMARY)],
                  expand=[("selected", [1, 1, 1, 0])])

    def _build_header(self, parent):
        f = tk.Frame(parent, bg=T.BG_DARK)
        f.pack(fill=tk.X, pady=(0, 16))

        left = tk.Frame(f, bg=T.BG_DARK)
        left.pack(side=tk.LEFT)

        tk.Label(left, text=self._str("app_title"), bg=T.BG_DARK,
                 fg=T.TEXT_PRIMARY, font=Fonts.TITLE).pack(anchor=tk.W)
        tk.Label(left, text=self._str("app_desc"), bg=T.BG_DARK,
                 fg=T.TEXT_MUTED, font=Fonts.BODY).pack(anchor=tk.W, pady=(4, 0))

        # 语言下拉框 + 版本
        right = tk.Frame(f, bg=T.BG_DARK)
        right.pack(side=tk.RIGHT, pady=(8, 0))

        # 语言选择下拉框（联合国6种官方语言）
        lang_frame = tk.Frame(right, bg=T.BG_DARK)
        lang_frame.pack(side=tk.LEFT, padx=(0, 12))

        tk.Label(lang_frame, text=self._str("lang_label") + ":",
                 bg=T.BG_DARK, fg=T.TEXT_MUTED,
                 font=Fonts.SMALL).pack(side=tk.LEFT, padx=(0, 6))

        # 下拉框显示语言本地名称
        lang_names = []
        lang_codes = []
        for code in ["zh", "en", "fr", "es", "ru", "ar"]:
            info = UN_LANGUAGES[code]
            # 使用本地名称 + 英文名称
            display = f"{info['name_local']}  {info['name_en']}"
            lang_names.append(display)
            lang_codes.append(code)

        self._lang_var = tk.StringVar()
        current_display = None
        for code, name in zip(lang_codes, lang_names):
            if code == self._.lang:
                current_display = name
                break
        self._lang_var.set(current_display or lang_names[0])

        lang_combo = ttk.Combobox(lang_frame, textvariable=self._lang_var,
                                   values=lang_names, state="readonly",
                                   width=22, font=Fonts.SMALL)
        lang_combo.pack(side=tk.LEFT)

        def _on_lang_select(event):
            selected = self._lang_var.get()
            idx = lang_names.index(selected)
            new_lang = lang_codes[idx]
            if new_lang != self._.lang:
                self._switch_lang(new_lang)

        lang_combo.bind("<<ComboboxSelected>>", _on_lang_select)

        ver = tk.Label(right, text=self._str("version_label", version=APP_CONFIG['version']),
                       bg=T.ACCENT, fg="white",
                       font=Fonts.SMALL, padx=10, pady=2)
        ver.pack(side=tk.LEFT)

    def _build_path_section(self, parent):
        content = tk.Frame(parent, bg=T.BG_CARD)
        content.pack(fill=tk.X, padx=16, pady=(8, 12))

        pairs = [("label_source", self.source_path), ("label_target", self.target_path)]
        for label_key, var in pairs:
            row = tk.Frame(content, bg=T.BG_CARD)
            row.pack(fill=tk.X, pady=6)

            tk.Label(row, text=f"{self._str(label_key)}:", bg=T.BG_CARD,
                     fg=T.TEXT_SECONDARY, font=Fonts.HEADING,
                     width=12, anchor="e").pack(side=tk.LEFT, padx=(0, 8))

            self._entry(row, var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8), ipady=5)
            self._btn(row, "btn_browse", lambda v=var: self._browse_folder(v),
                      "ACCENT", "ACCENT_HOVER", padx=16, pady=5).pack(side=tk.LEFT)

    def _build_search_section(self, parent):
        content = tk.Frame(parent, bg=T.BG_CARD)
        content.pack(fill=tk.X, padx=16, pady=(8, 12))

        row1 = tk.Frame(content, bg=T.BG_CARD)
        row1.pack(fill=tk.X, pady=4)

        tk.Label(row1, text=f"{self._str('label_keywords')}:", bg=T.BG_CARD,
                 fg=T.TEXT_SECONDARY, font=Fonts.HEADING).pack(side=tk.LEFT, padx=(0, 8))

        self.search_entry = self._entry(row1, self.search_keywords)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8), ipady=5)
        self.search_entry.bind('<Return>', lambda e: self._start_search())

        self._btn(row1, "btn_search", self._start_search,
                  "INFO", "INFO_HOVER", padx=18, pady=5).pack(side=tk.LEFT, padx=(0, 6))
        self._btn(row1, "btn_clear", self._clear_search,
                  "BG_CARD_HOVER", "BORDER", fg=T.TEXT_SECONDARY, padx=18, pady=5).pack(side=tk.LEFT)

        row2 = tk.Frame(content, bg=T.BG_CARD)
        row2.pack(fill=tk.X, pady=8)

        mode_f = tk.LabelFrame(row2, text=f" {self._str('match_logic')} ", bg=T.BG_CARD,
                               fg=T.TEXT_MUTED, font=Fonts.SMALL,
                               relief=tk.FLAT, highlightbackground=T.BORDER,
                               highlightthickness=1)
        mode_f.pack(side=tk.LEFT, padx=(0, 10))

        for text_key, value in [("match_any", "OR"), ("match_all", "AND")]:
            tk.Radiobutton(mode_f, text=self._str(text_key), variable=self.search_mode,
                           value=value, bg=T.BG_CARD,
                           fg=T.TEXT_SECONDARY, selectcolor=T.BG_INPUT,
                           activebackground=T.BG_CARD,
                           activeforeground=T.TEXT_PRIMARY,
                           font=Fonts.SMALL).pack(side=tk.LEFT, padx=6)

        scope_f = tk.LabelFrame(row2, text=f" {self._str('search_scope')} ", bg=T.BG_CARD,
                                fg=T.TEXT_MUTED, font=Fonts.SMALL,
                                relief=tk.FLAT, highlightbackground=T.BORDER,
                                highlightthickness=1)
        scope_f.pack(side=tk.LEFT, padx=(0, 10))

        scope_cb = ttk.Combobox(scope_f, textvariable=self.search_scope,
                                values=["ALL", "FILENAME", "FULLNAME", "EXTENSION", "PATH"],
                                width=14, state="readonly", font=Fonts.SMALL)
        scope_cb.set("ALL")
        scope_cb.pack(side=tk.LEFT, padx=5)

        adv = tk.Frame(row2, bg=T.BG_CARD)
        adv.pack(side=tk.LEFT)
        for text, var in [("Aa", self.search_case_sensitive), (".*", self.search_use_regex)]:
            tk.Checkbutton(adv, text=text, variable=var, bg=T.BG_CARD,
                           fg=T.TEXT_SECONDARY, selectcolor=T.BG_INPUT,
                           activebackground=T.BG_CARD, font=Fonts.SMALL).pack(side=tk.LEFT, padx=5)

        chk = tk.Frame(content, bg=T.BG_CARD)
        chk.pack(fill=tk.X, pady=(4, 0))
        tk.Checkbutton(chk,
                       text=self._str("search_only_results"),
                       variable=self.search_only_organized,
                       bg=T.BG_CARD, fg=T.ACCENT,
                       selectcolor=T.BG_INPUT,
                       activebackground=T.BG_CARD,
                       activeforeground=T.ACCENT,
                       font=Fonts.BODY).pack(side=tk.LEFT)

    def _build_options_section(self, parent):
        content = tk.Frame(parent, bg=T.BG_CARD)
        content.pack(fill=tk.X, padx=16, pady=(8, 12))

        type_f = tk.LabelFrame(content, text=f" {self._str('scan_type')} ", bg=T.BG_CARD,
                               fg=T.TEXT_MUTED, font=Fonts.SMALL,
                               relief=tk.FLAT, highlightbackground=T.BORDER,
                               highlightthickness=1)
        type_f.pack(side=tk.LEFT, padx=(0, 10))

        for text_key, var in [("type_office", self.scan_office),
                              ("type_image", self.scan_image),
                              ("type_video", self.scan_video)]:
            tk.Checkbutton(type_f, text=self._str(text_key), variable=var,
                           bg=T.BG_CARD, fg=T.TEXT_PRIMARY,
                           selectcolor=T.BG_INPUT,
                           activebackground=T.BG_CARD,
                           font=Fonts.BODY).pack(side=tk.LEFT, padx=8)

        mode_f = tk.LabelFrame(content, text=f" {self._str('op_mode')} ", bg=T.BG_CARD,
                               fg=T.TEXT_MUTED, font=Fonts.SMALL,
                               relief=tk.FLAT, highlightbackground=T.BORDER,
                               highlightthickness=1)
        mode_f.pack(side=tk.LEFT, padx=(0, 10))

        for text_key, value in [("op_copy", "copy"), ("op_move", "move"), ("op_preview", "preview")]:
            tk.Radiobutton(mode_f, text=self._str(text_key), variable=self.operation_mode,
                           value=value, bg=T.BG_CARD,
                           fg=T.TEXT_SECONDARY, selectcolor=T.BG_INPUT,
                           activebackground=T.BG_CARD,
                           font=Fonts.BODY).pack(side=tk.LEFT, padx=6)

        check_f = tk.LabelFrame(content, text=f" {self._str('option_recursive')[:4]}选项 ", bg=T.BG_CARD,
                                fg=T.TEXT_MUTED, font=Fonts.SMALL,
                                relief=tk.FLAT, highlightbackground=T.BORDER,
                                highlightthickness=1)
        # 修复：使用固定文本
        check_f = tk.LabelFrame(content, text=f" {self._str('label_options')} ", bg=T.BG_CARD,
                                fg=T.TEXT_MUTED, font=Fonts.SMALL,
                                relief=tk.FLAT, highlightbackground=T.BORDER,
                                highlightthickness=1)
        check_f.pack(side=tk.LEFT, padx=(0, 10))

        for text_key, var in [("option_recursive", self.recursive_scan), ("option_skip", self.skip_existing)]:
            tk.Checkbutton(check_f, text=self._str(text_key), variable=var,
                           bg=T.BG_CARD, fg=T.TEXT_SECONDARY,
                           selectcolor=T.BG_INPUT,
                           activebackground=T.BG_CARD,
                           font=Fonts.SMALL).pack(side=tk.LEFT, padx=6)

        fmt_f = tk.LabelFrame(content, text=f" {self._str('folder_format')} ", bg=T.BG_CARD,
                              fg=T.TEXT_MUTED, font=Fonts.SMALL,
                              relief=tk.FLAT, highlightbackground=T.BORDER,
                              highlightthickness=1)
        fmt_f.pack(side=tk.LEFT)

        fmt_values = [
            self._str("fmt_ym", year="YYYY", month="MM"),
            self._str("fmt_y_m", year="YYYY", month="MM"),
            self._str("fmt_slash", year="YYYY", month="MM"),
            self._str("fmt_underscore", year="YYYY", month="MM"),
        ]
        # 过滤掉重复项（英文中fmt_y_m和fmt_underscore可能相同）
        seen = set()
        unique_fmt = []
        for v in fmt_values:
            if v not in seen:
                seen.add(v)
                unique_fmt.append(v)
        fmt_cb = ttk.Combobox(fmt_f, textvariable=self.folder_format,
                              values=unique_fmt,
                              width=16, state="readonly", font=Fonts.SMALL)
        fmt_cb.pack(side=tk.LEFT, padx=5)

    def _build_action_buttons(self, parent):
        f = tk.Frame(parent, bg=T.BG_DARK)
        f.pack(fill=tk.X, pady=(0, 12))

        row = tk.Frame(f, bg=T.BG_DARK)
        row.pack(fill=tk.X)

        buttons = [
            ("btn_scan", self._start_scan, "ACCENT", "ACCENT_HOVER"),
            ("btn_organize", self._start_organize, "SUCCESS", "SUCCESS_HOVER"),
            ("btn_dedup", self._start_dedup, "INFO", "INFO_HOVER"),
            ("btn_undo", self._undo_last_task, "DANGER", "DANGER_HOVER"),
            ("btn_report", self._save_report, "WARNING", "WARNING_HOVER"),
        ]

        for text_key, cmd, c, h in buttons:
            self._btn(row, text_key, cmd, c, h,
                      font=Fonts.BUTTON_LARGE, padx=28, pady=12).pack(side=tk.LEFT, padx=(0, 8))

    def _build_progress(self, parent):
        self.progress_frame = tk.Frame(parent, bg=T.BG_DARK)
        self.progress_var = tk.DoubleVar()

        style = ttk.Style()
        style.configure("Custom.Horizontal.TProgressbar",
                        troughcolor=T.PROGRESS_BG, background=T.PROGRESS_FILL,
                        thickness=8, borderwidth=0)

        self.progress_bar = ttk.Progressbar(self.progress_frame,
                                            variable=self.progress_var,
                                            maximum=100, mode='determinate',
                                            style="Custom.Horizontal.TProgressbar")
        self.progress_bar.pack(fill=tk.X, side=tk.LEFT, expand=True)

        self.progress_label = tk.Label(self.progress_frame, text="",
                                       font=Fonts.BODY,
                                       bg=T.BG_DARK, fg=T.TEXT_SECONDARY)
        self.progress_label.pack(side=tk.RIGHT, padx=(12, 0))

    def _build_status_bar(self, parent):
        self.status_var = tk.StringVar(value=self._str("status_ready"))
        bar = tk.Frame(parent, bg=T.BG_SIDEBAR,
                       highlightbackground=T.BORDER, highlightthickness=1)
        bar.pack(fill=tk.X, pady=(0, 12), ipady=6)
        tk.Label(bar, textvariable=self.status_var,
                 bg=T.BG_SIDEBAR, fg=T.TEXT_SECONDARY,
                 font=Fonts.BODY).pack(side=tk.LEFT, padx=16)

    def _build_filter_bar(self, parent):
        self.filter_frame = tk.Frame(parent, bg=T.BG_CARD,
                                     highlightbackground=T.ACCENT,
                                     highlightthickness=1)
        self.filter_label = tk.Label(self.filter_frame, text="",
                                     bg=T.BG_CARD, fg=T.TEXT_ACCENT,
                                     font=Fonts.BODY_LARGE)
        self.filter_label.pack(padx=12, pady=6)
        self.filter_frame.pack_forget()

    def _build_file_list_tab(self):
        f = tk.Frame(self.notebook, bg=T.BG_CARD)
        self.notebook.add(f, text=f"  {self._str('tab_files')}  ")

        cols = ('name', 'type', 'size', 'modified', 'month', 'path')
        self.file_tree = ttk.Treeview(f, columns=cols, show='headings', height=15,
                                      style="Custom.Treeview")

        col_defs = [
            ('name', 'col_name', 200, 'w'), ('type', 'col_type', 80, 'center'),
            ('size', 'col_size', 80, 'center'), ('modified', 'col_date', 180, 'center'),
            ('month', 'col_month', 80, 'center'), ('path', 'col_path', 330, 'w')
        ]
        for col, title_key, w, a in col_defs:
            self.file_tree.heading(col, text=self._str(title_key))
            self.file_tree.column(col, width=w, anchor=a)

        style = ttk.Style()
        style.configure("Custom.Treeview", background=T.TREE_BG,
                        foreground=T.TEXT_PRIMARY, fieldbackground=T.TREE_BG,
                        rowheight=28, font=Fonts.BODY)
        style.configure("Custom.Treeview.Heading", background=T.TREE_HEADING_BG,
                        foreground=T.TEXT_PRIMARY, font=Fonts.HEADING, relief=tk.FLAT)
        style.map("Custom.Treeview",
                  background=[("selected", T.TREE_SELECTED)],
                  foreground=[("selected", "white")])

        vsb = ttk.Scrollbar(f, orient="vertical", command=self.file_tree.yview)
        hsb = ttk.Scrollbar(f, orient="horizontal", command=self.file_tree.xview)
        self.file_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.file_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        f.grid_rowconfigure(0, weight=1)
        f.grid_columnconfigure(0, weight=1)

        self.file_tree.bind('<Double-1>', self._on_file_double_click)

    def _build_stats_tab(self):
        f = tk.Frame(self.notebook, bg=T.BG_CARD)
        self.notebook.add(f, text=f"  {self._str('tab_stats')}  ")

        self.stats_text = scrolledtext.ScrolledText(
            f, wrap=tk.WORD, font=Fonts.BODY,
            bg=T.BG_CARD, fg=T.TEXT_PRIMARY,
            relief=tk.FLAT, padx=16, pady=16, highlightthickness=0)
        self.stats_text.pack(fill=tk.BOTH, expand=True)
        welcome = self._str("stats_welcome", app=self._str("app_title"))
        self.stats_text.insert(tk.END, welcome)
        self.stats_text.config(state=tk.DISABLED)

    def _build_dedup_tab(self):
        f = tk.Frame(self.notebook, bg=T.BG_CARD)
        self.notebook.add(f, text=f"  {self._str('tab_dedup')}  ")

        toolbar = tk.Frame(f, bg=T.BG_CARD)
        toolbar.pack(fill=tk.X, padx=16, pady=(12, 8))

        tk.Label(toolbar, text=self._str("dedup_title"), bg=T.BG_CARD,
                 fg=T.TEXT_PRIMARY, font=Fonts.SUBTITLE).pack(side=tk.LEFT)

        st_f = tk.LabelFrame(toolbar, text=f" {self._str('keep_strategy')} ", bg=T.BG_CARD,
                             fg=T.TEXT_MUTED, font=Fonts.SMALL,
                             relief=tk.FLAT, highlightbackground=T.BORDER,
                             highlightthickness=1)
        st_f.pack(side=tk.LEFT, padx=(20, 0))

        for text_key, value in [("keep_newest", "newest"), ("keep_oldest", "oldest"), ("keep_short", "short")]:
            tk.Radiobutton(st_f, text=self._str(text_key), variable=self.dedup_strategy,
                           value=value, bg=T.BG_CARD,
                           fg=T.TEXT_SECONDARY, selectcolor=T.BG_INPUT,
                           activebackground=T.BG_CARD,
                           font=Fonts.SMALL).pack(side=tk.LEFT, padx=5)

        self._btn(toolbar, "btn_find_dup", self._start_dedup,
                  "ACCENT", "ACCENT_HOVER", padx=16, pady=5).pack(side=tk.LEFT, padx=(15, 5))
        self._btn(toolbar, "btn_preview_delete", lambda: self._delete_duplicates(True),
                  "WARNING", "WARNING_HOVER", padx=16, pady=5).pack(side=tk.LEFT, padx=5)
        self._btn(toolbar, "btn_exec_delete", lambda: self._delete_duplicates(False),
                  "DANGER", "DANGER_HOVER", padx=16, pady=5).pack(side=tk.LEFT, padx=5)
        self._btn(toolbar, "btn_dedup_report", self._save_dedup_report,
                  "INFO", "INFO_HOVER", font=Fonts.SMALL, padx=12, pady=5).pack(side=tk.RIGHT)

        self.dedup_summary_var = tk.StringVar(value=self._str("dedup_wait"))
        tk.Label(f, textvariable=self.dedup_summary_var,
                 bg=T.BG_CARD, fg=T.TEXT_SECONDARY,
                 font=Fonts.BODY).pack(anchor=tk.W, padx=16, pady=(0, 8))

        dup_cols = ('group', 'hash', 'size', 'count', 'keep', 'delete', 'paths')
        self.dup_tree = ttk.Treeview(f, columns=dup_cols, show='headings', height=12,
                                     style="Dup.Treeview")

        dup_col_defs = [
            ('group', 'col_group', 40, 'center'), ('hash', 'col_hash', 150, 'center'),
            ('size', 'col_size', 80, 'center'), ('count', 'col_count', 60, 'center'),
            ('keep', 'col_keep', 200, 'w'), ('delete', 'col_delete', 60, 'center'),
            ('paths', 'col_path', 350, 'w')
        ]
        for col, title_key, w, a in dup_col_defs:
            self.dup_tree.heading(col, text=self._str(title_key))
            self.dup_tree.column(col, width=w, anchor=a)

        style = ttk.Style()
        style.configure("Dup.Treeview", background=T.TREE_BG,
                        foreground=T.TEXT_PRIMARY, fieldbackground=T.TREE_BG,
                        rowheight=28, font=Fonts.BODY)
        style.configure("Dup.Treeview.Heading", background=T.TREE_HEADING_BG,
                        foreground=T.TEXT_PRIMARY, font=Fonts.HEADING, relief=tk.FLAT)
        style.map("Dup.Treeview",
                  background=[("selected", T.TREE_SELECTED)],
                  foreground=[("selected", "white")])

        vsb = ttk.Scrollbar(f, orient="vertical", command=self.dup_tree.yview)
        self.dup_tree.configure(yscrollcommand=vsb.set)
        self.dup_tree.pack(fill=tk.BOTH, expand=True, padx=16, pady=5)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        tk.Label(f,
                 text=self._str("dedup_hint"),
                 bg=T.BG_CARD, fg=T.TEXT_MUTED,
                 font=Fonts.SMALL).pack(anchor=tk.W, padx=16, pady=(0, 10))

    def _build_history_tab(self):
        f = tk.Frame(self.notebook, bg=T.BG_CARD)
        self.notebook.add(f, text=f"  {self._str('tab_history')}  ")

        toolbar = tk.Frame(f, bg=T.BG_CARD)
        toolbar.pack(fill=tk.X, padx=16, pady=(12, 8))

        tk.Label(toolbar, text=self._str("history_title"), bg=T.BG_CARD,
                 fg=T.TEXT_PRIMARY, font=Fonts.SUBTITLE).pack(side=tk.LEFT)

        self._btn(toolbar, "btn_refresh", self._refresh_history_tab,
                  "ACCENT", "ACCENT_HOVER", font=Fonts.SMALL, padx=14, pady=4).pack(side=tk.RIGHT, padx=(8, 0))
        self._btn(toolbar, "btn_clear_history", self._clear_history,
                  "BG_CARD_HOVER", "BORDER", fg=T.TEXT_SECONDARY,
                  font=Fonts.SMALL, padx=14, pady=4).pack(side=tk.RIGHT)

        self.history_text = scrolledtext.ScrolledText(
            f, wrap=tk.WORD, font=Fonts.BODY,
            bg=T.BG_CARD, fg=T.TEXT_PRIMARY,
            relief=tk.FLAT, padx=16, pady=16, highlightthickness=0)
        self.history_text.pack(fill=tk.BOTH, expand=True)
        self.history_text.config(state=tk.DISABLED)
        self._refresh_history_tab()

    def _build_log_tab(self):
        f = tk.Frame(self.notebook, bg=T.BG_CARD)
        self.notebook.add(f, text=f"  {self._str('tab_log')}  ")

        self.log_text = scrolledtext.ScrolledText(
            f, wrap=tk.WORD, font=Fonts.MONO,
            bg=T.BG_CARD, fg=T.TEXT_PRIMARY,
            relief=tk.FLAT, padx=12, pady=12, highlightthickness=0)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        self._btn(f, "btn_clear_log", self._clear_log,
                  "BG_CARD_HOVER", "BORDER", fg=T.TEXT_SECONDARY,
                  font=Fonts.SMALL, padx=12, pady=4).pack(anchor=tk.E, padx=12, pady=6)

    # ===== 通用行为 =====
    def _browse_folder(self, var: tk.StringVar):
        folder = filedialog.askdirectory()
        if folder:
            var.set(folder)
            self._log(self._str("log_folder_selected", path=folder))

    def _log(self, message: str):
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)

    def _clear_log(self):
        self.log_text.delete(1.0, tk.END)

    def _show_progress(self, show: bool = True):
        if show:
            self.progress_frame.pack(fill=tk.X, pady=(0, 12))
        else:
            self.progress_frame.pack_forget()

    def _update_progress(self, current: int, total: int, message: str = ""):
        if total > 0:
            pct = (current / total) * 100
            self.progress_var.set(pct)
            self.progress_label.config(text=f"{current}/{total} ({pct:.1f}%)")
        self.status_var.set(message)
        self.root.update_idletasks()

    def _show_filter_status(self, matched: int, total: int, keywords: str):
        if matched < total:
            self.filter_label.config(
                text=f"  {self._str('search_keywords')}: 「{keywords}」 {self._str('search_match_count')} {matched} / {total}  ")
            self.filter_frame.pack(fill=tk.X, pady=(0, 12))
            self.is_filtered = True
        else:
            self._hide_filter_status()

    def _hide_filter_status(self):
        self.filter_frame.pack_forget()
        self.is_filtered = False

    def _refresh_file_list(self, files: List[FileInfo]):
        self.file_tree.delete(*self.file_tree.get_children())
        for fi in files:
            # 媒体文件显示拍摄时间，Office显示修改时间
            time_str = fi.capture_time_readable if fi.capture_time else fi.modified_time_readable
            # 添加时间来源标签 (EXIF/媒体创建/文件创建/修改)
            source_key = f"time_source_{fi.time_source}"
            source_label = self._str(source_key)
            time_display = f"{time_str}  ({source_label})"
            self.file_tree.insert('', tk.END, values=(
                fi.name, fi.file_type, fi.size_readable,
                time_display, fi.year_month, fi.path))
        self.displayed_files = files

    def _on_file_double_click(self, event):
        sel = self.file_tree.selection()
        if sel:
            path = self.file_tree.item(sel[0])['values'][5]
            if path and os.path.exists(path):
                os.startfile(os.path.dirname(path))

    # ===== 扫描 =====
    def _start_scan(self):
        src = self.source_path.get().strip()
        if not src or not is_valid_source_dir(src):
            messagebox.showwarning(self._str("msg_info"), self._str("msg_select_source"))
            return

        self.file_tree.delete(*self.file_tree.get_children())
        self.all_files = []
        self.displayed_files = []
        self._hide_filter_status()
        self._show_progress(True)
        self.status_var.set(self._str("status_scanning"))

        threading.Thread(target=self._scan_thread, args=(src,), daemon=True).start()

    def _scan_thread(self, src: str):
        try:
            cats = set()
            if self.scan_office.get(): cats.add('office')
            if self.scan_image.get(): cats.add('image')
            if self.scan_video.get(): cats.add('video')
            if not cats: cats = {'office', 'image', 'video'}

            files = self.scanner.scan_directory(
                src, recursive=self.recursive_scan.get(),
                progress_callback=lambda c, p: self.root.after(
                    0, lambda: self._update_progress(0, 0, self._str("status_scanning"))),
                category_filter=cats)

            self.all_files = files
            self.displayed_files = files
            self.root.after(0, self._scan_complete)
        except Exception as e:
            self.root.after(0, lambda: self._scan_error(str(e)))

    def _scan_complete(self):
        self._show_progress(False)
        s = self.scanner.get_statistics()
        self._log(self._str("log_scan_complete", count=s['total_files'], size=s['size_readable']))
        
        # 显示时间来源统计
        ts = s.get('time_stats', {})
        if ts:
            for key in ['EXIF', 'media_create', 'file_create', 'modified']:
                count = ts.get(key, 0)
                if count > 0:
                    log_key = f"log_time_{key.lower()}"
                    self._log(self._str(log_key, count=count))
        
        # 如果图片EXIF未启用且有图片被扫描，提示安装 Pillow
        if not self.scanner.is_pillow_available() and self.scan_image.get():
            img_count = sum(1 for f in self.all_files if f.category == 'image')
            if img_count > 0:
                self._log(self._str("msg_pillow_missing"))
        
        self._refresh_file_list(self.all_files)
        self._update_stats(s)
        self.status_var.set(self._str("status_scan_complete", count=s['total_files'], size=s['size_readable']))
        messagebox.showinfo(self._str("msg_scan_complete_title"),
                            self._str("msg_scan_complete", count=s['total_files'], size=s['size_readable']))

    def _scan_error(self, msg: str):
        self._show_progress(False)
        self.status_var.set(f"Scan failed: {msg}")
        self._log(f"Scan error: {msg}")
        messagebox.showerror(self._str("msg_error"), f"{self._str('msg_error')}:\n{msg}")

    # ===== 搜索 =====
    def _start_search(self):
        if not self.all_files:
            messagebox.showwarning(self._str("msg_info"), self._str("msg_scan_first"))
            return
        kw = self.search_keywords.get().strip()
        if not kw:
            messagebox.showwarning(self._str("msg_info"), self._str("msg_input_keyword"))
            return

        mode = MatchMode.AND if self.search_mode.get() == "AND" else MatchMode.OR
        scope_map = {"ALL": MatchScope.ALL, "FILENAME": MatchScope.FILENAME,
                     "FULLNAME": MatchScope.FULLNAME, "EXTENSION": MatchScope.EXTENSION,
                     "PATH": MatchScope.PATH}
        scope = scope_map.get(self.search_scope.get(), MatchScope.ALL)

        self.searcher.set_keywords(kw)
        self.searcher.configure(match_mode=mode, match_scope=scope,
                                case_sensitive=self.search_case_sensitive.get(),
                                use_regex=self.search_use_regex.get())

        matched = self.searcher.search(self.all_files)
        self._refresh_file_list(matched)
        self._show_filter_status(len(matched), len(self.all_files), kw)
        self.status_var.set(self._str("log_search_complete", match=len(matched), total=len(self.all_files)))
        self._update_search_stats(matched, kw, mode.name, scope.name)
        if matched:
            self.notebook.select(0)

    def _clear_search(self):
        if self.all_files:
            self.search_keywords.set("")
            self._refresh_file_list(self.all_files)
            self._hide_filter_status()
            self.status_var.set(self._str("status_scan_complete", count=len(self.all_files), size=""))
            self._update_stats(self.scanner.get_statistics())

    # ===== 整理 =====
    def _start_organize(self):
        if not self.all_files:
            messagebox.showwarning(self._str("msg_info"), self._str("msg_scan_first"))
            return
        target = self.target_path.get().strip()
        if not target or not is_valid_target_dir(target):
            messagebox.showerror(self._str("msg_error"), self._str("msg_select_target"))
            return

        use_f = self.search_only_organized.get() and self.is_filtered
        files = self.displayed_files if use_f else self.all_files
        if not files:
            messagebox.showwarning(self._str("msg_info"), self._str("msg_no_files"))
            return

        mode = self.operation_mode.get()
        mode_text = {"copy": self._str("op_copy"), "move": self._str("op_move"), "preview": self._str("op_preview")}[mode]

        kw_sub = ""
        if use_f:
            kw_sub = self._sanitize_folder_name(self.search_keywords.get().strip())

        target_display = target
        if kw_sub:
            target_display = f"{target}\n  - {kw_sub}/"

        extra_lines = ""
        if kw_sub:
            extra_lines += f"\n{self._str('msg_keyword_folder', folder=kw_sub)}\n"
        if mode == "move":
            extra_lines += f"\n{self._str('msg_move_warning')}\n"

        msg = self._str("msg_organize_confirm", mode=mode_text, count=len(files), target=target_display, extra=extra_lines)

        if not messagebox.askyesno(self._str("msg_organize_confirm_title"), msg):
            return

        self._show_progress(True)
        self.status_var.set(self._str("status_organizing"))

        op = OperationMode(mode)
        fmt = self.folder_format.get()
        plans = self.organizer.create_plan(
            files, target, op, fmt,
            source_root=self.source_path.get().strip(),
            keyword_subfolder=kw_sub)

        self._log(self._str("status_organizing") + f" ({mode_text})")
        threading.Thread(target=self._organize_thread, args=(plans,), daemon=True).start()

    def _organize_thread(self, plans):
        try:
            self.organizer.execute_plan(
                plans, skip_existing=self.skip_existing.get(),
                progress_callback=lambda c, t, m:
                    self.root.after(0, lambda: self._update_progress(c, t, m)))
            self.root.after(0, self._organize_complete)
        except Exception as e:
            self.root.after(0, lambda: self._organize_error(str(e)))

    def _organize_complete(self):
        self._show_progress(False)
        s = self.organizer.get_summary()
        mode = self.operation_mode.get()
        mode_text = {"copy": self._str("op_copy"), "move": self._str("op_move"), "preview": self._str("op_preview")}[mode]
        self._log(self._str("log_organize_complete", mode=mode_text, success=s['success'], failed=s['failed']))

        if mode != "preview" and self.organizer.results:
            try:
                record = create_record_from_organizer(
                    self.organizer.results,
                    source_root=self.organizer.last_source_root,
                    target_root=self.organizer.last_target_root,
                    operation_mode=self.organizer.last_operation_mode,
                    folder_format=self.organizer.last_folder_format,
                    keyword_subfolder=self.organizer.last_keyword_subfolder)
                self.undo_manager.add_record(record)
                self._refresh_history_tab()
            except Exception as e:
                self._log(f"Record failed: {e}")

        self.status_var.set(self._str("status_organize_complete", mode=mode_text, success=s['success'], failed=s['failed'], skipped=s['skipped']))
        messagebox.showinfo(self._str("msg_organize_complete_title"),
                            self._str("msg_organize_result", total=s['total'], success=s['success'], failed=s['failed'], skipped=s['skipped']))

    def _organize_error(self, msg: str):
        self._show_progress(False)
        self.status_var.set(f"Organize failed: {msg}")
        self._log(f"Organize error: {msg}")
        messagebox.showerror(self._str("msg_error"), f"{self._str('msg_error')}:\n{msg}")

    # ===== 去重 =====
    def _start_dedup(self):
        if not self.all_files:
            messagebox.showwarning(self._str("msg_info"), self._str("msg_scan_first"))
            return
        sm = {'newest': KeepStrategy.KEEP_NEWEST, 'oldest': KeepStrategy.KEEP_OLDEST,
              'short': KeepStrategy.KEEP_SHORTEST_PATH}
        strategy = sm.get(self.dedup_strategy.get(), KeepStrategy.KEEP_NEWEST)
        self._show_progress(True)
        self.status_var.set(self._str("status_deduping"))
        self.dedup_summary_var.set(self._str("status_dedup_wait"))
        threading.Thread(target=self._dedup_thread, args=(strategy,), daemon=True).start()

    def _dedup_thread(self, strategy: KeepStrategy):
        try:
            files = self.displayed_files if self.is_filtered else self.all_files
            groups = self.deduplicator.find_duplicates(
                files, strategy=strategy,
                progress_callback=lambda c, t, m:
                    self.root.after(0, lambda: self._update_progress(c, t, m)),
                quick_mode=False)
            self.dup_groups = groups
            self.root.after(0, self._dedup_complete)
        except Exception as e:
            self.root.after(0, lambda: self._dedup_error(str(e)))

    def _dedup_complete(self):
        self._show_progress(False)
        s = self.deduplicator.get_summary()
        if not self.dup_groups:
            self.dedup_summary_var.set(self._str("dedup_no_dup"))
            messagebox.showinfo(self._str("msg_no_dup_title"), self._str("msg_no_dup_body"))
        else:
            self.dedup_summary_var.set(
                self._str("dedup_found", groups=s['total_groups'], dup=s['total_duplicates'], space=s['waste_readable']))
            self._refresh_dup_tree()
            messagebox.showinfo(self._str("msg_dedup_complete_title"),
                                self._str("msg_dedup_result", groups=s['total_groups'], dup=s['total_duplicates'], space=s['waste_readable']))

    def _dedup_error(self, msg: str):
        self._show_progress(False)
        self.dedup_summary_var.set(f"Dedup failed: {msg}")
        self._log(f"Dedup error: {msg}")

    def _delete_duplicates(self, preview: bool = False):
        if not self.dup_groups:
            messagebox.showwarning(self._str("msg_info"), self._str("msg_no_dup"))
            return
        total = sum(g.duplicate_count for g in self.dup_groups)
        if not preview:
            if not messagebox.askyesno(self._str("msg_delete_confirm_title"),
                                       self._str("msg_delete_confirm", count=total)):
                return
        self._show_progress(True)
        _, summary = self.deduplicator.delete_duplicates(
            self.dup_groups, preview=preview,
            progress_callback=lambda c, t, m:
                self.root.after(0, lambda: self._update_progress(c, t, m)))
        self._show_progress(False)
        if preview:
            self.status_var.set(self._str("status_preview_complete", count=summary.deleted_count, space=summary.freed_readable))
            messagebox.showinfo(self._str("msg_preview_title"),
                                self._str("msg_preview_result", count=summary.deleted_count, space=summary.freed_readable))
        else:
            self.status_var.set(self._str("status_delete_complete", count=summary.deleted_count, space=summary.freed_readable))
            self._refresh_dup_tree()
            self.dup_groups = []
            messagebox.showinfo(self._str("msg_delete_complete_title"),
                                self._str("msg_delete_result", count=summary.deleted_count, space=summary.freed_readable))

    def _refresh_dup_tree(self):
        self.dup_tree.delete(*self.dup_tree.get_children())
        for i, g in enumerate(self.dup_groups, 1):
            keep = os.path.basename(g.files[g.keep_index].path)
            parts = [f"{'★' if j == g.keep_index else ' '} {os.path.basename(f.path)}"
                     for j, f in enumerate(g.files)]
            paths = " | ".join(parts[:3])
            if len(g.files) > 3:
                paths += f" ... +{len(g.files)-3}"
            self.dup_tree.insert('', tk.END, values=(
                i, g.hash_value[:16] + "...", g.size_readable,
                f"{len(g.files)}", keep, f"{g.duplicate_count}", paths))

    # ===== 撤销 =====
    def _undo_last_task(self):
        if not self.undo_manager.can_undo():
            messagebox.showwarning(self._str("msg_info"), self._str("msg_no_undo"))
            return
        r = self.undo_manager.get_last_record()
        mode = {'copy': self._str("op_copy"), 'move': self._str("op_move"), 'preview': self._str("op_preview")}.get(r.operation_mode, r.operation_mode)
        extra = ""
        if r.keyword_subfolder:
            extra = f"{self._str('msg_keyword_folder', folder=r.keyword_subfolder)}\n"
        msg = self._str("msg_undo_confirm", mode=mode, time=r.timestamp, count=r.total_files, extra=extra)
        if not messagebox.askyesno(self._str("msg_undo_confirm_title"), msg):
            return
        self._show_progress(True)
        self.status_var.set(self._str("status_undoing"))
        threading.Thread(target=self._undo_thread, daemon=True).start()

    def _undo_thread(self):
        try:
            result = self.undo_manager.undo_last_task(
                progress_callback=lambda c, t, m:
                    self.root.after(0, lambda: self._update_progress(c, t, m)))
            self.root.after(0, lambda: self._undo_complete(result))
        except Exception as e:
            self.root.after(0, lambda err=str(e): self._undo_error(err))

    def _undo_complete(self, result: dict):
        self._show_progress(False)
        restored = result.get('restored', 0)
        failed = result.get('failed', 0)
        self._log(self._str("log_undo_complete", count=restored, failed=failed))
        self.status_var.set(self._str("status_undo_complete", count=restored))
        self._refresh_history_tab()

    def _undo_error(self, msg: str):
        self._show_progress(False)
        self.status_var.set(f"Undo failed: {msg}")
        self._log(f"Undo error: {msg}")

    # ===== 统计与报告 =====
    def _update_stats(self, stats: dict):
        self.stats_text.config(state=tk.NORMAL)
        self.stats_text.delete(1.0, tk.END)
        lines = ["=" * 50, self._str("report_title"), "=" * 50, "",
                 f"{self._str('report_total')}: {stats['total_files']}",
                 f"{self._str('report_size')}:   {stats['size_readable']}", ""]
        if stats.get('by_category'):
            lines.append(f"【{self._str('report_by_category')}】")
            for cat, cnt in sorted(stats['by_category'].items(), key=lambda x: -x[1]):
                name = {'office': self._str('report_office'),
                        'image': self._str('report_image'),
                        'video': self._str('report_video')}.get(cat, cat)
                lines.append(f"  {name}: {cnt}")
            lines.append("")
        if stats.get('by_type'):
            lines.append(f"【{self._str('report_by_type')}】")
            for t, c in stats['by_type'].items():
                lines.append(f"  {t}: {c}")
            lines.append("")
        if stats.get('by_month'):
            lines.append(f"【{self._str('report_by_month')}】")
            for m, c in stats['by_month'].items():
                lines.append(f"  {m}: {c}")
            lines.append("")
        
        # 时间来源统计（新增）
        if stats.get('time_stats'):
            ts = stats['time_stats']
            has_media = ts.get('EXIF', 0) + ts.get('media_create', 0) + ts.get('file_create', 0)
            if has_media > 0:
                lines.append(f"【Time Source】")
                source_map = {
                    'EXIF': self._str('time_source_exif'),
                    'media_create': self._str('time_source_media'),
                    'file_create': self._str('time_source_file_create'),
                    'modified': self._str('time_source_modified'),
                }
                for key in ['EXIF', 'media_create', 'file_create', 'modified']:
                    count = ts.get(key, 0)
                    if count > 0:
                        lines.append(f"  {source_map[key]}: {count}")
                lines.append("")
        
        lines.append("=" * 50)
        self.stats_text.insert(tk.END, "\n".join(lines))
        self.stats_text.config(state=tk.DISABLED)

    def _update_search_stats(self, matched, kw, mode, scope):
        self.stats_text.config(state=tk.NORMAL)
        self.stats_text.delete(1.0, tk.END)
        ratio = 0
        if self.all_files:
            ratio = len(matched)/len(self.all_files)*100
        lines = ["=" * 50, self._str("search_report_title"), "=" * 50,
                 f"{self._str('search_keywords')}: 「{kw}」",
                 f"{self._str('search_match_mode')}: {mode}",
                 f"{self._str('search_scope_label')}: {scope}", "",
                 f"{self._str('search_match_count')}: {len(matched)} / {len(self.all_files)}"]
        if self.all_files:
            lines.append(f"{self._str('search_ratio')}: {ratio:.1f}%")
        lines.append("=" * 50)
        self.stats_text.insert(tk.END, "\n".join(lines))
        self.stats_text.config(state=tk.DISABLED)

    def _refresh_history_tab(self):
        self.history_text.config(state=tk.NORMAL)
        self.history_text.delete(1.0, tk.END)
        self.history_text.insert(tk.END, self.undo_manager.get_summary_text())
        self.history_text.config(state=tk.DISABLED)

    def _clear_history(self):
        if not self.undo_manager.records:
            messagebox.showinfo(self._str("msg_info"), self._str("undo_no_history"))
            return
        if messagebox.askyesno(self._str("msg_confirm"), self._str("msg_clear_confirm")):
            self.undo_manager.clear_history()
            self._refresh_history_tab()
            self._log(self._str("log_history_cleared"))

    def _save_report(self):
        if not self.organizer.results:
            messagebox.showwarning(self._str("msg_info"), self._str("msg_no_report"))
            return
        fp = filedialog.asksaveasfilename(
            defaultextension=".txt", filetypes=[("Text", "*.txt"), ("All", "*.*")],
            initialfile=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        if fp:
            self.organizer.save_report(fp)
            self._log(self._str("log_report_saved", path=fp))

    def _save_dedup_report(self):
        if not self.dup_groups:
            messagebox.showwarning(self._str("msg_info"), self._str("msg_no_dup"))
            return
        fp = filedialog.asksaveasfilename(
            defaultextension=".txt", filetypes=[("Text", "*.txt"), ("All", "*.*")],
            initialfile=f"dedup_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        if fp:
            self.deduplicator.save_report(fp)
            self._log(self._str("log_report_saved", path=fp))

    @staticmethod
    def _sanitize_folder_name(keywords: str) -> str:
        import re
        s = re.sub(r'[<>":/\\|?*]', ' ', keywords).strip()
        s = re.sub(r'\s+', '_', s)
        s = re.sub(r'_+', '_', s)
        return s[:50] if s else "search_results"


def main():
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
    FileOrganizerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
