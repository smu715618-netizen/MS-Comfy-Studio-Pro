# 变更日志 (Changelog)

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 规范。

## [Unreleased]

### 新增
- (未来新增内容将记录在此区域)

---

## [1.0.0] — 2026-07-23 — 核心平台发布 (V1.0)

### 新增

#### Engine Adapter 引擎适配层 (src/engines/)
- `EngineAdapter` — AI推理引擎抽象基类（7个抽象方法）
- `EngineRegistry` — 引擎注册表（单例模式，动态注册/注销）
- `InferenceRequest/Result` — 统一推理请求/响应数据结构
- `EngineCapability` 枚举 — 9种AI能力类型
- `EngineBackend` 枚举 — XPU/CUDA/DirectML/ROCm/MPS/ONNX/OpenVINO
- `get_best_for_capability()` — 自动选择最优引擎（Intel XPU优先链）
- ComfyUI引擎适配器 (`src/engines/comfyui/adapter.py`)

#### AI Scheduler 智能调度器 (src/core/scheduler.py, src/scheduler/)
- `AIScheduler` ABC — 调度器抽象接口
- `DefaultScheduler` — 默认占位实现
- `ScheduleTask` 数据类 — 任务信息（优先级/回调/状态追踪）
- 任务队列管理（入队/出队/取消/统计）

#### Model Center 模型管理 (src/models.py, 重构版)
- `ModelType` 枚举 — 10种模型类型（含IPAdapter预留、Textual Inversion预留）
- `ModelStatus` 枚举 — 7种状态追踪
- `ModelMetadata` 数据类 — 完整模型元数据（名称/类型/大小/SHA256/版本/作者/标签）
- `ModelScanner` — 磁盘扫描器（按类型递归扫描）
- `ModelIndex` — JSON索引管理器（增删查改+持久化+线程安全）
- `ModelVerifier` — SHA256完整性校验
- `ModelManager` — 主管理类（scan_and_index/register_model/verify/storage_stats）
- `configs/models.yaml` — 模型管理配置（目录/格式/下载设置/镜像源）

#### Node Center 节点管理 (src/nodes.py, 重构版)
- `NodeType` 枚举 — 内置/社区/自定义
- `NodeStatus` 枚举 — 启用/禁用/错误/过时
- `InstallSource` 枚举 — GitHub/GitLab/Zip/本地/企业
- `NodeDependency` — 依赖包信息（包名/版本规格/必需标志）
- `NodeInfo` 数据类 — **17字段**完整节点元数据
- `NodeRegistryAPI` — 节点仓库接口（预留搜索/详情/列表/更新检查）
- `NodeScanner` — 自动扫描三类节点（内置/社区/自定义）
- `DependencyChecker` — 依赖检测与冲突识别
- `NodeManager` — 全生命周期管理：install_from_git/zip/local → uninstall → enable/disable → update → check_updates → auto_fix_dependencies
- Git安装、Zip本地安装、本地目录安装、启用/禁用、版本检测、依赖检测与自动修复

#### Environment Manager 环境管理 (src/env_manager.py, 重构版)
- `PythonDetector` — Python版本/路径/虚拟环境检测
- `IntelRuntimeDetector` — Intel驱动/OneAPI/IPEX/OpenVINO检测
- `ComfyUIManager` — ComfyUI安装/更新/版本检测
- `PackageManager` — 包检测/安装/冲突解决
- `EnvironmentManager` — 总控：一键检查/修复/获取完整环境状态

#### Launcher 启动器系统 (src/launcher.py, 重构版)
- `LauncherState` 状态机 — 6状态循环（idle→checking→starting→running→stopping→error）
- `StartupConfig` — 硬件自适应启动参数（自动选low_vram/normal/high_vram + XPU/DirectML/CUDA）
- `ComfyUIProcess` — 进程管理器（后台日志捕获线程/优雅终止）
- `DashboardData` — 仪表盘数据汇总（GPU/CPU/内存/ComfyUI状态）
- `Launcher` 主类 — 整合所有模块：health_check/start_comfyui/stop_comfyui/get_dashboard_data/get_launch_recommendation
- CLI工具 — 终端模式（health/start/stop/dashboard）

#### GUI Panel 图形面板 (src/gui/)
- `Application` — PyQt6应用入口（Qt初始化/i18n/font/style）
- `MainWindow` — 主窗口（Toolbar + 左侧导航 + Stacked Pages + StatusBar）
- `ConsoleWidget` — 实时控制台（可清空/复制/颜色消息）
- `LogPanel` — 结构化日志列表（分级颜色/过滤）
- `CustomStatusBar` — 状态栏（GPU指示/进度条/版本显示）
- Catppuccin Mocha 暗色主题QSS样式表
- 健康检查页面

#### Download Manager (src/download_manager.py)
- `DownloadTask` 数据类 — 单个下载任务
- `DownloadManager` — 统一下载框架（并发/进度回调/失败重试/任务取消/SHA256验证）
- 为模型下载、插件安装、更新系统提供通用基础设施

#### Plugin API (src/plugins.py)
- `PluginInfo` 数据类 — 插件信息
- `PluginManager` — 插件安装/卸载/启用/禁用/更新
- GitHub/PyPI ZIP安装支持

#### Health Check System (src/health_check.py)
- `HealthCheck` 类 — 完整系统健康诊断
- GPU状态 / Python版本 / 磁盘空间 / 网络连接 / 依赖完整性 / 目录结构
- 结果格式化（通过/警告/错误）

#### Configuration System (src/config_manager.py)
- `ConfigManager` — YAML配置覆盖链（default→xpu→local）
- 嵌套键访问（config['gpu']['device']）
- 运行时热重载支持

#### Internationalization (src/i18n.py)
- `I18nManager` — JSON翻译文件加载
- 嵌套键支持（i18n.t("gui.start_button")）
- 默认值回退机制

#### GPU Detector (src/gpu_detector.py)
- `GPUDetector` — Intel XPU/DirectML/NVIDIA CUDA/AMD ROCm/CPU Only多后端检测
- `SystemInfo` — CPU信息/内存/Python版本/OS版本
- `check_compatibility()` — 兼容性诊断与建议
- `get_full_hardware_report()` — 综合硬件报告

#### Logger (src/logger.py)
- 彩色控制台输出
- 文件日志自动轮转
- 线程安全日志写入

#### Startup Parameters (src/start_config.py)
- VramMode枚举 — LOW_VRAM/NORMAL_VRAM/HIGH_VRAM/MAX_VRAM
- LaunchArgs — 启动参数集合
- LaunchConfigManager — 根据硬件自动生成推荐配置
- 4个预置配置文件（Intel Arc A750/RTX 3060/RTX 4090/CPU Only）

#### Workflows (src/workflows/)
- `WorkflowManager` — 工作流模板/导入/导出/分类管理
- `NodeSignature` — 节点签名定义（输入/输出/参数schema）
- `BindingEngine` — 参数绑定引擎（直接值/控件绑定/表达式绑定）

#### System Monitoring (src/cpu_monitor.py)
- `CpuMonitor` — CPU型号/核心数/负载监控
- `MemoryMonitor` — 内存总量/已用/可用/Swap监控
- `SystemHealth` — 综合健康状态
- `check_minimum_requirements()` — 最低配置检测

#### Deployment Scripts
- setup.bat — Windows一键安装脚本
- setup.ps1 — PowerShell安装脚本
- run_comfy.bat — 启动ComfyUI服务
- run_launcher.bat — 启动PyQt6管理面板
- uninstall.bat — 卸载脚本

#### CI/CD Pipeline (.github/workflows/)
- ci.yml — 自动lint(mypy/ruff)/test(pytest/coverage)/codecov
- release.yml — 自动tagged release生成

---

### 架构演进

| 阶段 | 核心成果 | Python文件数 |
|------|----------|-------------|
| Phase 1 | 基础架构（配置/日志/i18n/GPU/健康检查） | 25 |
| Phase 1.1 | GPU优先级优化（XPU主/DirectML备） | 修改 |
| Phase 1.2 | 跨平台架构预留（Windows/macOS/Linux） | +3 |
| Phase 1.3 | 项目优化（文档完善/平台目录优化） | +2 |
| Phase 2 | Launcher系统（状态机/硬件自适应/进程管理） | +5 |
| Phase 3 | 环境管理（Python/Intel/ComfyUI/依赖检测） | +4 |
| Phase 4 | Model Center（模型扫描/索引/SHA256/下载框架） | +2 |
| Phase 5 | Node Center（安装/卸载/启用/禁用/版本/依赖） | +6 |
| Phase 6 | Core Platform（Engine Adapter抽象层/Project Manager） | +2 |
| **Phase 7** | **Full Platform Integration** | **+4** |
| **总计** | | **~54** |

---

### 技术栈

- **语言**: Python 3.11.x
- **GUI框架**: PyQt6（Catppuccin Mocha暗色主题）
- **AI引擎**: ComfyUI（默认执行引擎，通过Engine Adapter调用）
- **GPU加速**: Intel Arc XPU / DirectML / CUDA(预留) / ROCm(预留) / Metal(预留)
- **配置管理**: PyYAML + JSON
- **网络请求**: requests
- **CI/CD**: GitHub Actions
- **测试框架**: pytest + coverage
- **代码规范**: Ruff + MyPy

---

### 已知限制

1. **ComfyUI未集成**: 引擎适配器为框架层，ComfyUI引擎具体调用逻辑待后续阶段完善
2. **Scheduler实际调度**: DefaultScheduler为占位，Phase 7后接入ComfyUI引擎后完善
3. **模型下载**: DownloadManager为框架，模型下载功能待开发
4. **模型市场**: ModelCenter仅支持本地扫描，在线模型市场API待接入
5. **节点市场**: NodeCenter支持Git安装，节点市场浏览/搜索功能待开发
6. **GUI面板**: MainWindow为功能框架，各Page内容待逐项填充
7. **健康检查部分依赖**: GPU实时状态需psutil支持
