# AI Context — MS Comfy Studio Pro

## 项目概述

MS Comfy Studio Pro 是一个基于 ComfyUI 的桌面启动器与管理平台，采用模块化分层架构，通过事件总线实现松耦合通信。

**技术栈：** Python 3.11+、PyQt6、PyTorch (XPU/CUDA)、YAML 配置、pytest

---

## 架构（当前版本 V1.0.5）

```
┌─────────────────────────────────────────────┐
│        GUI (PyQt6 Dashboard)                │
├─────────────────────────────────────────────┤
│        事件总线 (EventBus)                   │
├──────┬──────┬──────┬──────┬──────┬──────────┤
│ 配置  │ 日志  │ 国际化 │ GPU  │ 环境  │ 健康    │
│ 管理  │ 系统  │ 模块  │ 检测  │ 管理  │ 检查    │
├──────┴──────┴──────┴──────┴──────┴──────────┤
│  核心框架 (BaseComponent, DependencyContainer)│
├─────────────────────────────────────────────┤
│  业务模块：模型/节点/工作流/插件/更新/启动器  │
├─────────────────────────────────────────────┤
│        ComfyUI (外部依赖)                     │
└─────────────────────────────────────────────┘
```

---

## 开发规则

1. **所有模块继承 `BaseComponent`**，实现 `_do_initialize()` / `_do_shutdown()`
2. **模块通信走 `EventBus`**，禁止模块间直接耦合调用
3. **命名规范**：模块 `snake_case`，类 `PascalCase`，私有 `_leading_`
4. **所有公共方法必须有文档字符串 + 类型注解**
5. **测试文件与源码一一对应**，`tests/test_<module>.py`
6. **配置文件**：`configs/` 下 YAML 覆盖链 `default.yaml → xpu.yaml → local.yaml`
7. **日志使用 `get_logger(module_name)`**
8. **所有 subprocess 调用必须捕获** `FileNotFoundError, PermissionError, OSError, subprocess.TimeoutExpired, ValueError`

---

## 当前分支：main

**最新 Commit：** `cf79c65` @test: stabilize and align test suite  
**Tag：** v1.0.6  
**发布日期：** 2026-08-13

---

## 已完成模块（19/19）

| 模块 | 状态 |
|------|------|
| 配置管理 | ✅ |
| 日志系统 | ✅ |
| 国际化 | ✅ |
| GPU检测 (XPU优先链，异常处理已加固) | ✅ |
| 环境管理 | ✅ |
| 模型管理 | ✅ |
| 节点管理 | ✅ |
| 工作流管理 | ✅ |
| 插件管理 | ✅ |
| 更新系统 | ✅ |
| 启动器核心 | ✅ |
| 健康检查 | ✅ |
| 事件总线 | ✅ |
| 引擎适配器 (ComfyUI) | ✅ |
| Capability框架 | ✅ |
| Portrait API | ✅ |
| 工作流节点 | ✅ |
| CPU监控 | ✅ |
| GUI面板 | ✅ |
| 平台适配 | ✅ (框架) |

**测试：** 110/110 pytest 通过，100% 编译通过

---

## 已知限制

1. ComfyUI 引擎适配器为框架层，具体调用逻辑待后续阶段完善
2. 模型下载为框架，在线 API 集成待开发
3. GUI 需 PyQt6 环境验证（当前系统无 PyQt6）
4. Scheduler 默认实现为占位，需接入 ComfyUI 后完善

---

## 下一步开发方向

- **V1.1** 工作流可视化编辑器
- **V1.2** 模型中心完善
- **V1.5** Intel Arc/XPU 深度适配
- **V2.0** 企业正式发布
