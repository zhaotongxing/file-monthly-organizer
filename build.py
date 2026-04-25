"""
打包脚本 - 使用PyInstaller将应用打包为可执行文件

使用方法:
    python build.py

打包结果:
    dist/文件月整理工具.exe

注意:
    - 需要先安装 PyInstaller: pip install pyinstaller
    - 打包完成后，dist 目录下的 exe 可独立运行
"""

import os
import sys
import subprocess
import shutil


def check_pyinstaller():
    """检查是否安装了PyInstaller"""
    try:
        import PyInstaller
        return True
    except ImportError:
        return False


def install_pyinstaller():
    """安装PyInstaller"""
    print("正在安装 PyInstaller...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    print("PyInstaller 安装完成！")


def clean_build():
    """清理旧的构建文件"""
    dirs_to_remove = ['build', '__pycache__']
    for dir_name in dirs_to_remove:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"已清理: {dir_name}")
    
    # 清理旧的 .spec 文件
    for f in os.listdir('.'):
        if f.endswith('.spec'):
            os.remove(f)
            print(f"已清理: {f}")


def build():
    """执行打包"""
    print("=" * 50)
    print("文件月整理工具 - 打包脚本")
    print("=" * 50)
    
    # 检查PyInstaller
    if not check_pyinstaller():
        print("未检测到 PyInstaller，正在安装...")
        install_pyinstaller()
    
    # 清理旧的构建
    print("\n清理旧构建文件...")
    clean_build()
    
    # 要包含的数据文件（使用绝对路径避免目录冲突）
    root_dir = os.path.dirname(os.path.abspath(__file__))
    data_files = [
        'config.py',
        'scanner.py',
        'organizer.py',
        'searcher.py',
        'undo_manager.py',
        'deduplicator.py',
        'utils.py',
        'gui.py',
        'i18n.py',
    ]
    
    # 构建 --add-data 参数（使用绝对路径）
    add_data_args = []
    for f in data_files:
        abs_path = os.path.join(root_dir, f)
        if os.path.exists(abs_path):
            add_data_args.append(f'--add-data={abs_path};.')
        else:
            print(f"警告: 文件不存在 {abs_path}")
    
    # 构建命令
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=文件月整理工具",
        "--onefile",           # 打包为单个文件
        "--windowed",          # Windows GUI模式（不显示控制台）
        "--clean",             # 清理临时文件
        "--noconfirm",         # 不确认覆盖
    ] + add_data_args + [
        "main.py"
    ]
    
    print("\n开始打包...")
    print(f"工作目录: {root_dir}")
    
    try:
        subprocess.check_call(cmd)
        print("\n" + "=" * 50)
        print("打包成功！")
        print("=" * 50)
        dist_path = os.path.join(root_dir, 'dist', '文件月整理工具.exe')
        print(f"可执行文件位置: {dist_path}")
        
        if os.path.exists(dist_path):
            size = os.path.getsize(dist_path)
            print(f"文件大小: {size / (1024*1024):.1f} MB")
        
        print("\n可以直接将该exe文件复制到任意位置使用！")
        
    except subprocess.CalledProcessError as e:
        print(f"\n打包失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n发生错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    build()
