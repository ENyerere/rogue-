import os
import subprocess
import sys

# 指定Python虚拟环境路径
VENV_PYTHON = "D:/Github/oj_master_api/.venv/Scripts/python.exe"

def install_requirements():
    """安装所需的依赖"""
    print("正在安装所需依赖...")
    try:
        subprocess.check_call([VENV_PYTHON, "-m", "pip", "install", "rich", "pyinstaller"])
        print("依赖安装完成！")
    except subprocess.CalledProcessError as e:
        print(f"\n安装依赖失败: {str(e)}")
        sys.exit(1)

def build_exe():
    """使用PyInstaller打包程序"""
    print("正在打包游戏...")
    
    # 创建spec文件
    spec_content = """
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['rogue.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['rich', 'rich.console', 'rich.table', 'rich.panel', 
                   'rich.progress', 'rich.text', 'rich.layout'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='rogue',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
"""
    
    with open('rogue.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    # 使用spec文件进行打包
    pyinstaller_path = os.path.dirname(VENV_PYTHON) + "/pyinstaller.exe"
    subprocess.check_call([pyinstaller_path, "rogue.spec"])
    
    print("打包完成！")
    print("\n游戏文件已生成在 dist/rogue.exe")

if __name__ == "__main__":
    try:
        install_requirements()
        build_exe()
    except Exception as e:
        print(f"Error: {str(e)}")
        input("按Enter键退出...")
