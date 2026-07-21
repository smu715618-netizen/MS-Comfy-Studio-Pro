# 架构设计文档

## 整体架构

MS Comfy Studio Pro 采用模块化分层架构设计，各模块之间通过事件总线通信，实现松耦合。

```
┌─────────────────────────────────────────────┐
│              启动器 GUI (PyQt6)               │
├─────────────────────────────────────────────┤
│  事件总线 (EventBus)                         │
├──────┬──────┬──────┬──────┬──────┬──────────┤
│ 配置  │ 日志  │ 国际化 │ GPU  │ 环境  │ 健康    │
│ 管理  │ 系统  │ 模块  │ 检测  │ 管理  │ 检查    │
├──────┴──────┴──────┴──────┴──────┴──────────┤
│  核心框架 (BaseComponent, DependencyContainer)│
├─────────────────────────────────────────────┤
│  业务模块                                   │
│  ┌─────────┬─────────┬─────────┬──────────┐ │
│  │ 模型管理 │ 节点管理 │ 工作流管理 │ 插件管理 │ │
│  └─────────┴─────────┴─────────┴──────────┘ │
├─────────────────────────────────────────────┤
│  更新系统 (AppUpdater, ModelUpdater)         │
├─────────────────────────────────────────────┤
│  启动器 (ComfyUIProcess)                     │
├─────────────────────────────────────────────┤
│  ComfyUI (外部依赖)                           │
└─────────────────────────────────────────────┘
```

## 模块说明

### 1. 核心框架 (src/core/)

- **BaseComponent**: 所有模块组件的基类，提供生命周期管理
- **EventBus**: 事件总线，实现模块间的发布/订阅通信
- **DependencyContainer**: 依赖注入容器

### 2. 配置管理 (src/config_manager.py)

集中管理所有 YAML 配置文件，支持多环境覆盖链：

```
default.yaml → xpu.yaml → local.yaml
```

提供点分隔路径访问：`config.get("gpu.device")`

### 3. 日志系统 (src/logger.py)

- 彩色控制台输出
- 文件日志（自动轮转）
- 分级日志（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- 线程安全

### 4. 国际化 (src/i18n.py)

- JSON 翻译文件
- 嵌套键支持
- 默认值回退
- 运行时语言切换

### 5. GPU 检测 (src/gpu_detector.py)

检测顺序（按路线优先级）：
1. Intel Arc XPU (主路线) — PyTorch XPU 后端，性能最优
2. Intel Arc DirectML (备用路线) — DirectX 12 抽象层，兼容性好
3. NVIDIA CUDA
4. AMD ROCm
5. CPU Only

### 6. 环境管理 (src/env_manager.py)

- Python 版本检测
- 虚拟环境创建
- 依赖安装
- ComfyUI 克隆

### 7. 模型管理 (src/models.py)

- 8 种模型类型管理
- SHA256 完整性验证
- 下载进度回调
- 存储统计

### 8. 节点管理 (src/nodes.py)

- 内置/社区/自定义节点
- Git 安装和更新
- 启用/禁用控制
- 兼容性检查

### 9. 工作流管理 (src/workflows.py)

- 模板系统
- 导入/导出
- 依赖检查
- 分类管理

### 10. 插件管理 (src/plugins.py)

- GitHub/PyPI 安装
- 元数据解析
- 更新检查
- 启用/禁用

### 11. 更新系统 (src/updater.py)

- 应用更新
- 模型更新
- 节点更新
- 回滚支持

### 12. 启动器 (src/launcher.py)

- ComfyUI 进程管理
- 日志捕获
- 状态监控
- 优雅停止

### 13. 健康检查 (src/health_check.py)

- GPU 状态
- Python 版本
- 磁盘空间
- 网络连接
- 依赖完整性
- 目录结构

### 14. GUI (src/gui/)

- PyQt6 管理面板
- Catppuccin Mocha 暗色主题
- 实时控制台
- 状态栏

## 数据流

```
用户操作 → GUI → 事件总线 → 模块处理 → 状态更新 → GUI 刷新
                                    ↓
                              日志记录 → 控制台/文件
```

## 扩展点

### 添加新模块

1. 在 `src/` 下创建新模块
2. 继承 `BaseComponent`
3. 通过 `EventBus` 与其他模块通信
4. 在 `src/__init__.py` 中注册

### 添加新语言

1. 在 `configs/locales/` 下添加 `{locale}.json`
2. 在 `default.yaml` 的 `app.available_locales` 中添加语言代码

### 添加新模型类型

1. 在 `ModelType` 枚举中添加新值
2. 在 `data/models/` 下创建对应目录
3. 更新 `ModelManager` 的目录扫描逻辑
