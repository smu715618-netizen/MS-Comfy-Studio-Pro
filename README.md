# MS Comfy Studio Pro

> 面向 Intel Arc A750（8GB）的企业级 ComfyUI 整合平台

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Platform: Windows 11](https://img.shields.io/badge/platform-Windows_11-orange.svg)]()
[![GPU: Intel Arc XPU](https://img.shields.io/badge/GPU-Intel_Arc_XPU-purple.svg)]()

## 简介

MS Comfy Studio Pro 是一个面向企业的 ComfyUI 整合分发平台，专为 Intel Arc A750（8GB VRAM）显卡优化。

**目标用户：**
- 商业修图工作室
- 摄影工作室
- 工程行业视觉设计
- AI 辅助设计
- 证件照制作
- 局部重绘与高清修复

**核心特性：**
- Intel Arc XPU 原生加速支持（DirectML）
- 企业级模块化架构
- 模型按需下载与管理
- 工作流模板系统
- 插件热加载
- 自动更新机制
- 中英文国际化
- 可视化启动器面板

## 最低配置要求

| 组件 | 最低配置 |
|------|---------|
| 操作系统 | Windows 11 (22H2+) |
| CPU | Intel Core i5-10400 或同级 |
| 内存 | 16 GB RAM |
| GPU | Intel Arc A750 (8GB) |
| 磁盘 | 50 GB 可用空间 (SSD 推荐) |
| Python | 3.11.x |

## 快速开始

### 一键安装

```bash
# 双击运行
setup.bat

# 或在终端中运行
.\setup.ps1
```

### 启动

```bash
# 启动 ComfyUI 服务
run_comfy.bat

# 启动管理面板
run_launcher.bat
```

## 项目结构

```
MS-Comfy-Studio-Pro/
├── configs/          # 配置文件（集中管理）
│   ├── default.yaml  # 默认配置
│   ├── xpu.yaml      # Intel XPU 配置
│   └── locales/      # 国际化翻译文件
├── src/              # 源代码（模块化）
│   ├── core/         # 核心框架（事件总线、依赖注入）
│   ├── gui/          # 图形界面（PyQt6）
│   ├── models/       # 模型管理
│   ├── nodes/        # 节点管理
│   ├── workflows/    # 工作流系统
│   ├── plugins/      # 插件系统
│   └── updater/      # 更新系统
├── data/             # 数据目录（模型、工作流等）
├── comfyui/          # ComfyUI 运行时（安装时克隆）
├── venv/             # Python 虚拟环境
├── tests/            # 测试套件
└── docs/             # 文档
```

## 模块清单

| 模块 | 文件 | 状态 |
|------|------|------|
| 配置管理 | src/config_manager.py | ✅ |
| 日志系统 | src/logger.py | ✅ |
| 国际化 | src/i18n.py | ✅ |
| GPU 检测 | src/gpu_detector.py | ✅ |
| 环境管理 | src/env_manager.py | ✅ |
| 模型管理 | src/models.py | ✅ |
| 节点管理 | src/nodes.py | ✅ |
| 工作流管理 | src/workflows.py | ✅ |
| 插件管理 | src/plugins.py | ✅ |
| 更新系统 | src/updater.py | ✅ |
| 启动器核心 | src/launcher.py | ✅ |
| 健康检查 | src/health_check.py | ✅ |
| GUI 面板 | src/gui/app.py | ✅ |

## 文档

- [安装指南](INSTALL.md)
- [架构设计](ARCHITECTURE.md)
- [部署说明](DEPLOYMENT.md)
- [开发文档](docs/DEVELOPMENT.md)
- [变更日志](CHANGELOG.md)
- [TODO](TODO.md)

## 许可证

[MIT License](LICENSE)

## 技术支持

本项目针对 Intel Arc A750 进行了深度优化，确保所有默认工作流在 8GB VRAM 下稳定运行。
