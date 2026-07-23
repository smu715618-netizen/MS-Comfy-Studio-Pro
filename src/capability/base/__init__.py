# AI Capability Framework — 统一AI能力框架

"""
MS Comfy Studio Pro AI 能力层

所有 AI 功能（Portrait/Repair/Product/Creative等）必须通过此框架注册和调用。

架构：
    GUI / CLI / API → CapabilityRegistry → Pipeline → Executor → Scheduler → Engine Adapter → AI Engine

规范：
1. 禁止业务层直接调用 Engine Adapter（ComfyUI/Diffusers等）
2. 所有 AI 能力必须继承 CapabilityBase 并注册到 CapabilityRegistry
3. 所有执行必须经过 Pipeline 编排
4. 事件驱动通信（src.events模块）

目录结构：
    src/capability/base/      — 能力基类与接口定义
    src/capability/registry.py  — 能力注册中心
    src/capability/pipeline.py  — Pipeline编排引擎
    src/capability/executor.py  — 执行枢纽
"""
