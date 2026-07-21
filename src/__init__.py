# MS Comfy Studio Pro - 源代码包

"""
MS Comfy Studio Pro 主源代码包

模块化架构：
- core: 核心框架（事件总线、依赖注入、基类）
- gui: 图形界面（PyQt6 启动器）
- models: 模型管理
- nodes: 节点管理
- workflows: 工作流系统
- plugins: 插件系统
- updater: 自动更新
"""

__all__ = [
    "core",
    "gui",
    "models",
    "nodes",
    "workflows",
    "plugins",
    "updater",
]
