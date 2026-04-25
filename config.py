"""
配置文件 - 定义支持的文件类型和应用程序配置
"""

# Office文档扩展名
OFFICE_EXTENSIONS = {
    '.doc': 'Word文档',
    '.docx': 'Word文档',
    '.docm': 'Word宏文档',
    '.dot': 'Word模板',
    '.dotx': 'Word模板',
    '.pdf': 'PDF文档',
    '.wps': 'WPS文档',
    '.wpt': 'WPS模板',
    '.et': 'WPS表格',
    '.ett': 'WPS表格模板',
    '.xls': 'Excel表格',
    '.xlsx': 'Excel表格',
    '.xlsm': 'Excel宏表格',
    '.xlsb': 'Excel二进制表格',
    '.xlt': 'Excel模板',
    '.xltx': 'Excel模板',
    '.csv': 'CSV文件',
}

# 图片扩展名
IMAGE_EXTENSIONS = {
    '.jpg': '图片',
    '.jpeg': '图片',
    '.png': '图片',
    '.gif': '图片',
    '.bmp': '图片',
    '.tiff': '图片',
    '.tif': '图片',
    '.webp': '图片',
    '.ico': '图片',
    '.svg': '图片',
    '.raw': '图片',
    '.cr2': '图片',
    '.nef': '图片',
    '.arw': '图片',
    '.dng': '图片',
    '.orf': '图片',
    '.rw2': '图片',
    '.pef': '图片',
    '.x3f': '图片',
    '.heic': '图片',
    '.heif': '图片',
}

# 视频扩展名
VIDEO_EXTENSIONS = {
    '.mp4': '视频',
    '.avi': '视频',
    '.mkv': '视频',
    '.mov': '视频',
    '.wmv': '视频',
    '.flv': '视频',
    '.f4v': '视频',
    '.m4v': '视频',
    '.mpg': '视频',
    '.mpeg': '视频',
    '.3gp': '视频',
    '.ts': '视频',
    '.webm': '视频',
    '.m2ts': '视频',
    '.mts': '视频',
    '.vob': '视频',
    '.ogv': '视频',
    '.divx': '视频',
    '.rm': '视频',
    '.rmvb': '视频',
}

# 所有支持的文件扩展名（合并）
SUPPORTED_EXTENSIONS = {**OFFICE_EXTENSIONS, **IMAGE_EXTENSIONS, **VIDEO_EXTENSIONS}

# 文件类型分组
FILE_TYPE_GROUPS = {
    'Word文档': ['.doc', '.docx', '.docm', '.dot', '.dotx'],
    'PDF文档': ['.pdf'],
    'WPS文档': ['.wps', '.wpt', '.et', '.ett'],
    'Excel表格': ['.xls', '.xlsx', '.xlsm', '.xlsb', '.xlt', '.xltx', '.csv'],
    '图片': list(IMAGE_EXTENSIONS.keys()),
    '视频': list(VIDEO_EXTENSIONS.keys()),
}

# 文件大类分组（用于扫描筛选）
CATEGORY_GROUPS = {
    'office': ('Office文档', list(OFFICE_EXTENSIONS.keys())),
    'image': ('图片', list(IMAGE_EXTENSIONS.keys())),
    'video': ('视频', list(VIDEO_EXTENSIONS.keys())),
}

# 应用程序配置
APP_CONFIG = {
    'name': '文件月整理工具',
    'version': '1.4.0',
    'author': 'AI Assistant',
    'description': '自动搜索并按月整理Office文档/图片/视频文件，支持关键词搜索和任务撤销',
}

# 搜索配置
SEARCH_CONFIG = {
    'default_match_mode': 'OR',           # 默认匹配模式: AND / OR
    'default_match_scope': 'ALL',          # 默认匹配范围: FILENAME / FULLNAME / EXTENSION / PATH / ALL
    'case_sensitive': False,               # 默认大小写敏感
    'use_regex': False,                    # 默认不使用正则
    'max_history': 20,                     # 搜索历史最大数量
    'delimiter': 'auto',                   # 关键词分隔符: auto / space / comma
}
