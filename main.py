"""
文件月整理工具 - 主入口

功能说明:
    自动搜索电脑中的 Word/PDF/WPS/Excel 文件，并按照文件的修改时间
    按月整理到相应的文件夹中。
    
    v1.1 新增功能:
    - 关键词搜索: 支持多关键词组合搜索，AND/OR逻辑匹配
    - 搜索范围: 可搜索文件名、路径、扩展名
    - 智能过滤: 搜索结果可直接用于整理，也可整理所有文件
    
    支持的文件格式:
    - Word文档: .doc, .docx, .docm, .dot, .dotx
    - PDF文档: .pdf
    - WPS文档: .wps, .wpt, .et, .ett
    - Excel表格: .xls, .xlsx, .xlsm, .xlsb, .xlt, .xltx, .csv

使用方法:
    1. 直接运行: python main.py
    2. 打包为exe: python build.py
    
    界面操作流程:
    1. 选择源文件夹 -> 开始扫描
    2. （可选）输入关键词 -> 关键词搜索
    3. 选择目标文件夹
    4. 选择操作模式（复制/移动/预览）
    5. 开始整理
"""

import sys
import os

# 确保可以导入同级模块
if __name__ == "__main__":
    from gui import main
    main()
