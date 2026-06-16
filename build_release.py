"""
弥娅 (MIYA) v8.0 - 发布构建脚本
将 Miya 编译为可分发的 .exe，保留可编辑的配置和可查看的数据文件。

用法:
  python build_release.py --clean                      # 独立后端
  python build_release.py --clean --desktop             # 完整桌面应用
  python build_release.py --desktop                     # 桌面应用（含重编译）
  python build_release.py --skip-compile --desktop      # 桌面应用（跳过编译，复用 release/Miya/）
  python build_release.py --skip-compile --desktop --no-electron-build  # 仅同步后端，不打包

输出目录: release/Miya/
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

# 编译前禁止 PaddleX 联网检查，避免 PyInstaller 扫描时触发
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

PROJECT_ROOT = Path(__file__).parent
RELEASE_DIR = PROJECT_ROOT / "release" / "Miya"
SPEC_FILE = PROJECT_ROOT / "Miya.spec"

# ════════════════════════════════════════════════════════════════
# Step 1: Clean
# ════════════════════════════════════════════════════════════════


def clean():
    """清理旧的构建产物"""
    dirs_to_clean = [
        PROJECT_ROOT / "build",
        PROJECT_ROOT / "dist",
        RELEASE_DIR,
    ]
    for d in dirs_to_clean:
        if d.exists():
            print(f"  清理: {d}")
            shutil.rmtree(d, ignore_errors=True)


# ════════════════════════════════════════════════════════════════
# Step 2: PyInstaller 编译
# ════════════════════════════════════════════════════════════════


def run_pyinstaller():
    """运行 PyInstaller 编译"""
    print("\n" + "=" * 60)
    print("  PyInstaller 编译中...")
    print("=" * 60 + "\n")

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        str(SPEC_FILE),
        "--noconfirm",
        "--clean",
        "--distpath",
        str(PROJECT_ROOT / "dist"),
        "--workpath",
        str(PROJECT_ROOT / "build"),
    ]

    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))

    if result.returncode != 0:
        print("\n[ERROR] PyInstaller 编译失败!")
        sys.exit(result.returncode)

    print("\n[OK] 编译完成\n")


# ════════════════════════════════════════════════════════════════
# Step 3: 组装发布文件夹
# ════════════════════════════════════════════════════════════════


def assemble_release():
    """将 dist/Miya 复制到 release/Miya 并添加便捷文件"""
    dist_dir = PROJECT_ROOT / "dist" / "Miya"

    if not dist_dir.exists():
        print("[ERROR] dist/Miya 不存在，请先编译!")
        sys.exit(1)

    print("=" * 60)
    print("  组装发布文件夹...")
    print("=" * 60 + "\n")

    # 安全清理: 从编译产物中删除可能泄露的 .env
    dist_env = dist_dir / "_internal" / "config" / ".env"
    if dist_env.exists():
        dist_env.unlink()
        print(f"  安全清理: 已删除 {dist_env}")

    # 复制到 release/
    if RELEASE_DIR.exists():
        shutil.rmtree(RELEASE_DIR, ignore_errors=True)

    shutil.copytree(dist_dir, RELEASE_DIR)

    # 确保 data/ 和 logs/ 目录存在
    for sub in ["data", "logs"]:
        internal_path = RELEASE_DIR / "_internal" / sub
        internal_path.mkdir(exist_ok=True)
        print(f"  创建目录: _internal/{sub}/")

    # 复制 .env 模板 (始终从 .env.example 创建，防止真实 .env 泄露)
    env_example = RELEASE_DIR / "_internal" / "config" / ".env.example"
    env_target = RELEASE_DIR / "_internal" / "config" / ".env"

    if env_example.exists():
        # 始终覆盖 .env，确保不会泄露 API 密钥
        shutil.copy(env_example, env_target)
        print(f"  从模板创建: .env ← .env.example (旧 .env 已覆盖)")

    # 清理 config 中的敏感模板文件（仅保留可分发的内容）
    _clean_config_for_release()

    # 创建外层 config/data/logs 真实目录，_internal/ 下创建 junction 指向外层
    _create_access_dirs()

    # 创建启动脚本
    _create_launcher_bat()
    _create_readme()

    print(f"\n[OK] 发布文件夹已就绪: {RELEASE_DIR}\n")


# ════════════════════════════════════════════════════════════════


def _clean_config_for_release():
    """清理配置目录，移除开发/调试文件"""
    config_dir = RELEASE_DIR / "_internal" / "config"
    if not config_dir.exists():
        return

    remove_patterns = ["__pycache__"]
    for pattern in remove_patterns:
        p = config_dir / pattern
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)


def _create_access_dirs():
    """创建外层 config/ data/ logs/ 真实目录，并在 _internal/ 下创建目录联结（junction）指向外层

    编译后结构：
      release/Miya/
      ├── Miya.exe               主程序
      ├── 启动弥娅.bat             启动脚本
      ├── config/                 ← 真实目录（用户可编辑）
      ├── data/                   ← 真实目录（运行时数据）
      ├── logs/                   ← 真实目录（日志）
      ├── models/                 ← 真实目录（本地模型）
      └── _internal/
          ├── config  → ../config   (junction → 外层)
          ├── data    → ../data     (junction → 外层)
          ├── logs    → ../logs     (junction → 外层)
          └── models  → ../models   (junction → 外层)

    注意：目录联结（junction）仅适用于本地构建。若需 zip 分发，请使用
    --portable-zip 参数回退到复制模式。
    """
    directories = ["config", "data", "logs", "models"]
    for dir_name in directories:
        internal_path = RELEASE_DIR / "_internal" / dir_name
        outer_path = RELEASE_DIR / dir_name

        # 1. 确保外层目录存在
        outer_path.mkdir(exist_ok=True)

        # 2. 若 _internal 下有该目录且有内容，先迁移到外层
        if internal_path.exists():
            _migrate_directory(internal_path, outer_path)
            # 删除 _internal 下的原始目录
            shutil.rmtree(internal_path, ignore_errors=True)

        # 3. 创建 junction: _internal/{dir} → 外层 {dir}
        _create_junction(
            link=internal_path,
            target=outer_path,
        )


def _migrate_directory(src: Path, dst: Path):
    """将 src 目录下所有内容移动到 dst，保留文件时间戳"""
    for item in src.iterdir():
        src_item = src / item.name
        dst_item = dst / item.name
        if src_item.is_dir() and not src_item.is_symlink():
            if dst_item.exists():
                shutil.rmtree(dst_item, ignore_errors=True)
            shutil.copytree(src_item, dst_item)
        elif src_item.is_file():
            shutil.copy2(src_item, dst_item)
        # 跳过 junction/symlink


def _create_junction(link: Path, target: Path):
    """在 Windows 上创建目录联结（junction）

    使用绝对路径确保 mklink /J 可靠创建。
    注意：junction 存储绝对路径，移动 release/ 文件夹后需重新构建。
    """
    link_abs = str(link.resolve())
    target_abs = str(target.resolve())
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", link_abs, target_abs],
        capture_output=True,
        text=True,
    )
    name = link.name
    if result.returncode == 0:
        print(f"  联结: _internal/{name}/ → ../{name}/")
    else:
        err = result.stderr.strip()
        print(f"  [WARN] 联结创建失败 _internal/{name}/: {err}")
        print(f"         回退: 复制目录 _internal/{name}/ ← {name}/")
        if target.exists():
            shutil.copytree(target, link, dirs_exist_ok=True)


def _create_launcher_bat():
    """创建启动批处理文件"""
    launcher = RELEASE_DIR / "启动弥娅.bat"
    launcher.write_text(
        """@echo off
chcp 65001 >nul
title MiYA v8.0 - Daemon

:: Switch working directory to _internal for correct path resolution
:: config/ data/ logs/ 位于外层，通过 _internal/ 下的目录联结透明访问
cd /d "%~dp0_internal"

echo.
echo ================================================================================
echo   MiYA v8.0 - Daemon
echo ================================================================================
echo.
echo   Config:  config\\   (edit .env, personality, TTS, etc.)
echo   Data:    data\\     (view memory, conversations, lifebook)
echo   Logs:    logs\\     (runtime logs)
echo.
echo   API will be at: http://localhost:9800
echo   Press Ctrl+C to exit
echo ================================================================================
echo.

"%~dp0Miya.exe"

echo.
echo ================================================================================
echo   MiYA stopped
echo ================================================================================
pause
""",
        encoding="utf-8",
    )

    readme = RELEASE_DIR / "使用说明.txt"
    readme.write_text(
        """================================================================================
   弥娅 (MIYA) v8.0 - 使用说明
================================================================================

一、启动方式
---------------
  双击「启动弥娅.bat」启动守护进程。
  启动后 API 位于: http://localhost:9800

二、配置文件
---------------
  配置文件位于程序目录下的 config\\ 文件夹中（与 Miya.exe 同级）。
  
  重要文件：
  - .env               环境变量 (API密钥、数据库等)，从 .env.example 复制并编辑
  - personality_config.json   人格配置
  - memory_config.json        记忆系统配置
  - tts_config.json           TTS 语音配置
  
  编辑方式：用任意文本编辑器打开 config\\ 下的文件即可修改，重启后生效。

三、数据 & 记忆文件
---------------
  数据文件位于程序目录下的 data\\ 文件夹中（与 Miya.exe 同级）。
  
  重要目录/文件：
  - memory\\              记忆数据库 (miya_memory.db)
  - conversations\\       对话历史 (JSON 文件)
  - lifebook\\            生活记录
  - tts_audio\\           生成的语音文件

四、日志
---------------
  运行日志位于程序目录下的 logs\\ 文件夹中（与 Miya.exe 同级）。

五、目录结构
---------------
  Miya/
  ├── Miya.exe                 主程序
  ├── 启动弥娅.bat               启动脚本
  ├── config\\                   配置文件（可直接编辑）
  ├── data\\                     数据文件（可直接查看）
  ├── logs\\                     日志文件
  └── _internal\\                运行时库（请勿手动修改）

================================================================================
   弥娅 (MIYA) - AI 虚拟化身  v8.0
================================================================================
""",
        encoding="utf-8",
    )


def _create_readme():
    pass  # 已合并到 _create_launcher_bat 中


# ════════════════════════════════════════════════════════════════
# Step 4: 验证
# ════════════════════════════════════════════════════════════════


def verify_release():
    """验证发布文件夹完整性"""
    print("=" * 60)
    print("  验证发布文件夹...")
    print("=" * 60 + "\n")

    checks = [
        (RELEASE_DIR / "Miya.exe", "主程序"),
        (RELEASE_DIR / "_internal", "运行库"),
        (RELEASE_DIR / "_internal" / "config", "配置目录 (junction)"),
        (RELEASE_DIR / "_internal" / "config" / ".env.example", "配置模板"),
        (RELEASE_DIR / "config", "配置目录 (外层)"),
        (RELEASE_DIR / "data", "数据目录 (外层)"),
        (RELEASE_DIR / "logs", "日志目录 (外层)"),
        (RELEASE_DIR / "启动弥娅.bat", "启动脚本"),
    ]

    all_ok = True
    for path, desc in checks:
        if path.exists():
            size_str = ""
            if path.is_file():
                size = path.stat().st_size
                size_str = f" ({_format_size(size)})"
            print(f"  [OK] {desc}: {path.name}{size_str}")
        else:
            print(f"  [MISS] {desc}: MISSING!")
            all_ok = False

    # 统计大小
    total_size = sum(f.stat().st_size for f in RELEASE_DIR.rglob("*") if f.is_file())
    print(f"\n  总大小: {_format_size(total_size)}\n")

    if all_ok:
        print("[OK] 验证通过!\n")
    else:
        print("[WARN] 部分文件缺失，请检查\n")


def _ensure_local_models():
    """确保 models/ 目录下有 PaddleOCR 模型（从 PaddleX 缓存同步）"""
    from pathlib import Path as _Path

    paddlex_cache = _Path.home() / ".paddlex" / "official_models"
    local_models = PROJECT_ROOT / "models" / "paddle_ocr" / "official_models"

    if not paddlex_cache.exists():
        print(f"  [WARN] PaddleX 缓存不存在: {paddlex_cache}，跳过模型同步")
        return

    expected_dirs = [
        "PP-LCNet_x1_0_doc_ori",
        "PP-LCNet_x1_0_textline_ori",
        "PP-OCRv5_server_det",
        "PP-OCRv5_server_rec",
        "UVDoc",
    ]

    local_models.mkdir(parents=True, exist_ok=True)

    for d in expected_dirs:
        src = paddlex_cache / d
        dst = local_models / d
        if src.exists() and not dst.exists():
            print(f"  模型同步: {d} ...")
            shutil.copytree(src, dst)
        elif not src.exists():
            print(f"  [WARN] PaddleX 缓存缺少: {d}")

    print(f"  [OK] 本地模型已就绪: {local_models}\n")


def _format_size(size_bytes: int) -> str:
    size = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


# ════════════════════════════════════════════════════════════════
# Step 4: 桌面应用 (可选)
# ════════════════════════════════════════════════════════════════

ELECTRON_RESOURCES = PROJECT_ROOT / "miya_frontend" / "resources" / "backend"


def sync_to_electron_resources(source_dir=None):
    """将 PyInstaller 编译产物同步到 Electron 前端资源目录

    Args:
        source_dir: 源目录，默认为 dist/Miya。--skip-compile 时使用 release/Miya。
    """
    if source_dir is None:
        source_dir = PROJECT_ROOT / "dist" / "Miya"
    if not source_dir.exists():
        print(f"[ERROR] {source_dir} 不存在，请先编译!")
        return False

    print("=" * 60)
    print("  同步后端到 Electron 资源目录...")
    print("=" * 60 + "\n")

    # 清理旧的后端资源
    if ELECTRON_RESOURCES.exists():
        shutil.rmtree(ELECTRON_RESOURCES, ignore_errors=True)

    ELECTRON_RESOURCES.mkdir(parents=True)

    # 复制 _internal/ (Python 运行时依赖)
    internal_src = source_dir / "_internal"
    internal_dst = ELECTRON_RESOURCES / "_internal"
    if internal_src.exists():
        shutil.copytree(internal_src, internal_dst)
        print(
            f"  复制: _internal/ ({_format_size(sum(f.stat().st_size for f in internal_dst.rglob('*') if f.is_file()))})"
        )

    # 重命名 Miya.exe → miya-backend.exe (Electron 期望的名称)
    exe_src = source_dir / "Miya.exe"
    exe_dst = ELECTRON_RESOURCES / "miya-backend.exe"
    if exe_src.exists():
        shutil.copy2(exe_src, exe_dst)
        print(f"  复制: miya-backend.exe ({_format_size(exe_dst.stat().st_size)})")

    # 安全清理: 删除可能泄露的 .env
    for env_path in [
        ELECTRON_RESOURCES / "_internal" / "config" / ".env",
        ELECTRON_RESOURCES / "_internal" / "config" / ".env.bak",
        ELECTRON_RESOURCES / "_internal" / "config" / ".env.backup",
    ]:
        if env_path.exists():
            env_path.unlink()
            print(f"  安全清理: 已删除 {env_path.name}")

    # 从模板创建 .env
    env_example = ELECTRON_RESOURCES / "_internal" / "config" / ".env.example"
    env_target = ELECTRON_RESOURCES / "_internal" / "config" / ".env"
    if env_example.exists():
        shutil.copy(env_example, env_target)
        print(f"  从模板创建: .env ← .env.example")

    # 确保 logs/ 目录存在
    log_dir = ELECTRON_RESOURCES / "logs"
    log_dir.mkdir(exist_ok=True)

    print(f"\n[OK] 后端已同步到: {ELECTRON_RESOURCES}\n")
    return True


def build_electron_app():
    """构建 Electron 桌面应用安装包"""
    frontend_dir = PROJECT_ROOT / "miya_frontend"

    print("=" * 60)
    print("  构建 Electron 桌面应用...")
    print("=" * 60 + "\n")

    # 1. 准备 Claude Code Engine 依赖 (ws 需要跟随 dist 一起)
    print("[0/3] 准备 Claude Code Engine...")
    cce_dist = frontend_dir / "resources" / "claude-code-engine" / "dist"
    cce_nm = cce_dist / "node_modules"
    cce_nm.mkdir(parents=True, exist_ok=True)
    cce_src = PROJECT_ROOT / "claude-code-engine"
    # 复制 ws 模块到 dist/node_modules/ 以便 Node.js 就近解析
    ws_src = cce_src / "node_modules" / "ws"
    ws_dst = cce_nm / "ws"
    if ws_src.exists() and not ws_dst.exists():
        shutil.copytree(ws_src, ws_dst)
        print(f"  ws 依赖已就绪")
    # 同步 dist 文件
    import distutils.dir_util

    distutils.dir_util.copy_tree(str(cce_src / "dist"), str(cce_dist))
    print(f"  Claude Code Engine 文件已同步\n")

    # 2. 构建前端 (Vite build)
    print("[1/3] 前端构建 (Vite)...")
    result = subprocess.run(
        ["npm", "run", "build"],
        cwd=str(frontend_dir),
        shell=True,
    )
    if result.returncode != 0:
        print("\n[ERROR] 前端构建失败!")
        return False

    # 3. Electron-builder 打包 (zip 目标，避免 2GB+ NSIS mmap 失败)
    print("\n[2/3] Electron 打包 (zip)...")
    result = subprocess.run(
        ["npx", "electron-builder", "--win", "zip"],
        cwd=str(frontend_dir),
        shell=True,
    )
    if result.returncode != 0:
        print("\n[ERROR] Electron 打包失败!")
        return False

    # 显示输出
    release_dir = frontend_dir / "release"
    for f in release_dir.glob("*.exe"):
        print(f"\n  桌面安装包: {f} ({_format_size(f.stat().st_size)})")

    print(f"\n[OK] 桌面应用构建完成! 输出: {release_dir}\n")
    return True


# ════════════════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════════════════


def main():
    do_clean = "--clean" in sys.argv
    do_desktop = "--desktop" in sys.argv
    no_electron = "--no-electron-build" in sys.argv
    skip_compile = "--skip-compile" in sys.argv

    print()
    print("=" * 60)
    print("  弥娅 (MIYA) v8.0 - 发布构建")
    print("=" * 60)

    if do_clean and not skip_compile:
        print("\n[0/4] 清理旧构建...")
        clean()

    if skip_compile:
        print("\n  跳过编译，使用已有 release/Miya/")
    else:
        print("\n[1/4] 编译...")
        print("\n  → 同步本地模型...")
        _ensure_local_models()
        run_pyinstaller()

        print("\n[2/4] 组装发布...")
        assemble_release()

    # 桌面应用: 同步后端到 Electron 资源目录
    if do_desktop:
        print("\n[3/4] 同步后端到 Electron...")
        source = RELEASE_DIR if skip_compile else None
        if not sync_to_electron_resources(source):
            sys.exit(1)

        if not no_electron:
            print("\n[4/4] 构建桌面应用...")
            if not build_electron_app():
                sys.exit(1)
        else:
            print("\n[4/4] 跳过 Electron 打包 (--no-electron-build)")
    elif not skip_compile:
        print("\n[3/4] 验证...")
        verify_release()
        print("\n  提示: 使用 --desktop 构建桌面应用安装包")

    # 清理 PyInstaller 中间产物
    if not skip_compile:
        _clean_intermediates()

    print("=" * 60)
    print(f"  构建完成! 输出目录: {RELEASE_DIR}")
    if do_desktop and not no_electron:
        print(f"  桌面安装包: {PROJECT_ROOT / 'miya_frontend' / 'release'}")
    print("=" * 60)
    print()


def _clean_intermediates():
    """清理 PyInstaller 编译产生的中间产物 (dist/ 和 build/)"""
    for d in [PROJECT_ROOT / "dist", PROJECT_ROOT / "build"]:
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)
            print(f"  清理: {d}")


if __name__ == "__main__":
    main()
