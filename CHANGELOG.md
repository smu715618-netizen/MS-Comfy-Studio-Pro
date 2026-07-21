# 变更日志

本文档记录 MS Comfy Studio Pro 的所有重要变更。

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

---

## [0.1.0] - 2026-07-21

### 新增
- 项目初始化
- 模块化架构设计
- 配置管理系统（default.yaml + xpu.yaml + local.yaml 覆盖链）
- 日志系统（彩色控制台 + 文件轮转）
- 国际化框架（中文/英文，JSON 翻译文件）
- 模型管理框架（8 种模型类型，SHA256 验证）
- 节点管理框架（内置/社区/自定义）
- 工作流管理框架（模板/导入/导出）
- 插件管理框架（GitHub/PyPI 安装）
- 启动器框架（ComfyUI 进程管理）
- 自动更新框架（应用/模型/节点三层更新）
- GPU 检测模块（Intel Arc XPU 优先）
- 虚拟环境管理（自动创建/依赖安装）
- 健康检查系统（GPU/Python/磁盘/网络/依赖）
- PyQt6 启动器面板（Catppuccin Mocha 主题）
- Windows 安装脚本（setup.bat/ps1）
- 完整测试套件（6 个测试模块）

### 技术栈
- Python 3.11.x
- PyQt6（启动器 UI）
- ComfyUI（原生 Web）
- PyTorch DirectML/XPU
- PyYAML（配置管理）
- requests（网络请求）

### 修复
- 修复 i18n 模块路径计算错误（../.. → ../）
- 修复 ConfigManager 路径计算错误
- 修复所有 logger.method("module", msg) 调用
- 修复多处多余括号导致的语法错误
- 添加 get_config() 全局配置单例函数
