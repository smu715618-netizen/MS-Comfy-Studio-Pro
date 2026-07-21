# 平台支持策略 (Platform Support)

本文档记录 MS Comfy Studio Pro 的平台支持策略和设计。

---

## 当前支持平台

### Windows 11 (✅ 已支持)

**主要目标平台**

- 操作系统：Windows 11 (22H2+)
- GPU 后端：
  - Intel XPU (主路线) — PyTorch XPU 后端，性能最优
  - DirectML (备用路线) — Windows DirectX 12 抽象层
  - NVIDIA CUDA (预留) — 未来扩展
- 启动器：PyQt6 桌面面板
- 安装方式：setup.bat / setup.ps1

**为什么选择 Windows 11：**
- 目标用户群体主要在 Windows 平台
- Intel Arc A750 主要面向 Windows 用户
- ComfyUI 在 Windows 上的生态最成熟

---

### macOS (🔄 预留)

**未来支持计划**

- 操作系统：macOS 14+ (Sonoma)
- GPU 后端：
  - Apple Metal / MPS — PyTorch MPS 后端
- 启动器：PyQt6 桌面面板（需验证 PyQt6 在 macOS 上的兼容性）
- 安装方式：Homebrew / Python pip

**技术考量：**
- Apple Silicon (M1/M2/M3) 使用统一内存架构
- MPS 后端与 PyTorch CUDA 接口类似，迁移成本较低
- 需要独立的依赖树和构建流程
- 文件系统差异（HFS+/APFS vs NTFS）

**何时启用：** 收到明确 macOS 用户需求时

---

### Linux (🔄 预留)

**未来支持计划**

- 操作系统：Ubuntu 22.04+ / Fedora 38+
- GPU 后端：
  - NVIDIA CUDA (主要) — 企业级首选
  - AMD ROCm — 针对 AMD GPU
  - Intel XPU — 针对 Intel Arc
- 启动器：PyQt6 桌面面板
- 安装方式：pip / conda

**技术考量：**
- Linux 是 ComfyUI 的原生开发环境
- NVIDIA CUDA 在 Linux 上支持最完善
- 需要处理不同的包管理器和依赖解析

**何时启用：** 社区需求驱动

---

## 跨平台架构设计

### 平台适配层 (`platform/`)

```
platform/
├── __init__.py          # 平台检测和路由
├── windows/
│   └── __init__.py      # Windows GPU 后端
├── macos/
│   └── __init__.py      # macOS GPU 后端 (预留)
└── linux/
    └── __init__.py      # Linux GPU 后端 (预留)
```

**设计原则：**

1. **运行时检测** — 启动时自动检测当前平台和 GPU 设备
2. **懒加载** — 仅加载当前平台对应的 GPU 后端模块
3. **内存隔离** — 未使用的平台代码不进入内存空间
4. **配置驱动** — 通过 `preferred_type` 配置项控制优先选项

### 核心模块跨平台兼容

所有核心模块已设计为跨平台兼容：

| 模块 | 跨平台状态 | 说明 |
|------|-----------|------|
| 配置管理 | ✅ 跨平台 | 使用 pathlib，不硬编码路径 |
| 日志系统 | ✅ 跨平台 | 标准 logging 模块 |
| 国际化 | ✅ 跨平台 | 纯 Python，无平台依赖 |
| GPU 检测 | ✅ 跨平台 | 支持 Intel/NVIDIA/AMD/CPU |
| 环境管理 | ⚠️ Windows 优先 | venv 路径区分 win/mac/linux |
| 模型管理 | ✅ 跨平台 | 使用 pathlib |
| 节点管理 | ✅ 跨平台 | Git 跨平台兼容 |
| 工作流管理 | ✅ 跨平台 | 纯 JSON 操作 |
| 插件管理 | ✅ 跨平台 | pip/git 跨平台兼容 |
| 启动器 | ⚠️ Windows 优先 | taskkill → kill 需适配 |
| 健康检查 | ✅ 跨平台 | 部分检测逻辑需适配 |
| GUI | ⚠️ Windows 优先 | PyQt6 跨平台，字体需适配 |

---

## 扩展路线图

| 阶段 | 平台 | 状态 |
|------|------|------|
| Phase 1 | Windows 11 + Intel Arc | ✅ 已完成 |
| Phase 3 | macOS + Apple Silicon | 🔄 预留 |
| Phase 5 | Linux + NVIDIA/AMD | 🔄 预留 |

---

## 注意事项

> 当前阶段（Phase 1）仅支持 Windows 11。
> macOS 和 Linux 支持为架构预留，不要求立即开发完整功能。
> 所有核心代码必须跨平台设计，禁止硬编码 Windows 路径。
