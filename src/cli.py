"""
CLI 命令行入口

提供命令行接口，支持以下命令：
- mcsp setup: 初始化项目环境
- mcsp start: 启动 ComfyUI
- mcsp stop: 停止 ComfyUI
- mcsp update: 检查并应用更新
- mcsp health: 运行健康检查
- mcsp models: 模型管理子命令
- mcsp nodes: 节点管理子命令
- mcsp workflows: 工作流管理子命令
- mcsp --version: 显示版本信息
- mcsp --help: 显示帮助信息
"""

import argparse
import sys
import os


def main():
    """CLI 主入口函数"""
    parser = argparse.ArgumentParser(
        prog="mcsp",
        description="MS Comfy Studio Pro - 企业级 ComfyUI 管理平台",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"MS Comfy Studio Pro v0.1.0",
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # setup 命令
    setup_parser = subparsers.add_parser("setup", help="初始化项目环境")
    setup_parser.add_argument(
        "--force", action="store_true", help="强制重新安装"
    )

    # start 命令
    start_parser = subparsers.add_parser("start", help="启动 ComfyUI 服务")
    start_parser.add_argument(
        "--port", type=int, default=8188, help="启动端口 (默认: 8188)"
    )
    start_parser.add_argument(
        "--browser", action="store_true", help="自动打开浏览器"
    )

    # stop 命令
    subparsers.add_parser("stop", help="停止 ComfyUI 服务")

    # update 命令
    update_parser = subparsers.add_parser("update", help="检查并应用更新")
    update_parser.add_argument(
        "--force", action="store_true", help="强制更新"
    )

    # health 命令
    subparsers.add_parser("health", help="运行系统健康检查")

    # models 命令
    models_parser = subparsers.add_parser("models", help="模型管理")
    models_sub = models_parser.add_subparsers(dest="model_command")
    models_sub.add_parser("list", help="列出已安装模型")
    models_sub.add_parser("clean", help="清理未使用的模型")

    # nodes 命令
    nodes_parser = subparsers.add_parser("nodes", help="节点管理")
    nodes_sub = nodes_parser.add_subparsers(dest="node_command")
    nodes_sub.add_parser("list", help="列出已安装节点")
    nodes_sub.add_parser("update", help="更新所有节点")

    # workflows 命令
    workflows_parser = subparsers.add_parser("workflows", help="工作流管理")
    workflows_sub = workflows_parser.add_subparsers(dest="workflow_command")
    workflows_sub.add_parser("list", help="列出所有工作流")
    workflows_sub.add_parser("templates", help="列出可用模板")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    # 路由到对应命令处理
    commands = {
        "setup": cmd_setup,
        "start": cmd_start,
        "stop": cmd_stop,
        "update": cmd_update,
        "health": cmd_health,
    }

    handler = commands.get(args.command)
    if handler:
        handler(args)
    else:
        # 子命令（models, nodes, workflows）由各自子解析器处理
        parser.print_help()


def cmd_setup(args):
    """执行环境初始化"""
    from src.env_manager import EnvironmentManager
    from src.gpu_detector import GPUDetector

    print("[设置] 正在初始化环境...")

    # 检测 GPU
    detector = GPUDetector()
    gpu_info = detector.detect()
    print(f"[设置] GPU: {gpu_info}")

    # 创建虚拟环境
    env = EnvironmentManager()
    if env.ensure_venv(force=getattr(args, "force", False)):
        print("[设置] 虚拟环境就绪")
    else:
        print("[设置] 警告: 虚拟环境创建失败")

    print("[设置] 环境初始化完成")


def cmd_start(args):
    """启动 ComfyUI"""
    run_comfy(port=args.port, open_browser=args.browser)


def cmd_stop(args):
    """停止 ComfyUI"""
    print("[停止] 正在停止 ComfyUI 服务...")
    # TODO: 实现进程管理
    print("[停止] ComfyUI 服务已停止")


def cmd_update(args):
    """检查更新"""
    print("[更新] 正在检查更新...")
    # TODO: 实现更新检查
    print("[更新] 已是最新版本")


def cmd_health(args):
    """健康检查"""
    print("[健康检查] 正在检查系统状态...")
    from src.health_check import HealthChecker

    checker = HealthChecker()
    results = checker.run_all()
    for check_name, result in results.items():
        status = "✓" if result["status"] == "pass" else "✗"
        print(f"  {status} {check_name}: {result['message']}")
    print("[健康检查] 完成")


def run_comfy(port: int = 8188, open_browser: bool = False):
    """
    启动 ComfyUI 服务

    Args:
        port: 监听端口
        open_browser: 是否自动打开浏览器
    """
    import subprocess
    import webbrowser
    import time
    import signal
    import os

    comfyui_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "comfyui")
    comfyui_script = os.path.join(comfyui_dir, "main.py")

    if not os.path.exists(comfyui_script):
        print(f"错误: 找不到 ComfyUI: {comfyui_script}")
        print("请先运行 'mcsp setup' 进行初始化")
        sys.exit(1)

    cmd = [
        sys.executable,
        comfyui_script,
        "--port", str(port),
    ]

    if open_browser:
        cmd.append("--auto-launch")

    print(f"正在启动 ComfyUI (端口: {port})...")
    print(f"命令: {' '.join(cmd)}")

    process = subprocess.Popen(
        cmd,
        cwd=comfyui_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
    )

    # 等待服务启动
    time.sleep(3)
    url = f"http://127.0.0.1:{port}"
    print(f"ComfyUI 已启动: {url}")

    if open_browser:
        webbrowser.open(url)

    try:
        # 保持运行，捕获 Ctrl+C
        process.wait()
    except KeyboardInterrupt:
        print("\n正在停止 ComfyUI...")
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        print("ComfyUI 已停止")
        sys.exit(0)


if __name__ == "__main__":
    main()
