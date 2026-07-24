# AI Capability Framework — 统一AI能力框架

"""
MS Comfy Studio Pro AI 能力层

所有 AI 功能（Portrait/Repair/Product/Creative等）必须通过此框架注册和调用。

架构规范：
    GUI / CLI / API → CapabilityRegistry → Pipeline → ExecutorHub → Scheduler → EngineAdapter → Engine

强制规则：
1. 禁止业务层直接调用 Engine Adapter（ComfyUI/Diffusers等）
2. 所有AI能力必须继承 CapabilityBase 并注册到 CapabilityRegistry
3. 所有执行必须经过 Pipeline 编排
4. 事件驱动通信（src.events模块）

目录结构：
    src/capability/base/      — 能力基类与接口定义（本文件）
    src/capability/registry.py  — 能力注册中心（全局发现+查询过滤）
    src/capability/pipeline.py  — Pipeline编排引擎（参数校验/构建/执行/异常处理）
    src/capability/executor.py  — ExecutorHub（能力实例管理+执行路由）
    src/capability/portrait/   — PortraitAI（后续Module实现）
    src/capability/repair/     — RepairAI（后续Module实现）
    ...
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Tuple
import threading
import time


# ================================================================
# 枚举类
# ================================================================

class CapabilityStatus(Enum):
    """能力状态"""
    REGISTERED = "registered"       # 已注册但未初始化
    READY = "ready"                 # 已就绪可用
    BUSY = "busy"                   # 执行中
    ERROR = "error"                 # 错误/不可用
    DISABLED = "disabled"           # 手动禁用


class CapabilityPriority(Enum):
    """执行优先级"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


# ================================================================
# 数据类
# ================================================================

@dataclass
class CapabilityParam:
    """能力参数定义"""
    name: str                       # 参数名
    param_type: str                 # 类型（str/int/float/bool/path/image）
    display_name: str = ""          # 显示名称
    default: Any = None             # 默认值
    min_val: float = None           # 最小值（数值型）
    max_val: float = None           # 最大值（数值型）
    choices: List[str] = field(default_factory=list)  # 选项列表
    required: bool = True           # 是否必填
    description: str = ""           # 说明文字
    hidden: bool = False            # 是否对普通用户隐藏

    def validate(self, value: Any) -> Tuple[bool, str]:
        """验证参数值"""
        if self.required and value is None:
            return False, f"参数 {self.name} 为必填项"
        if self.choices and value and value not in self.choices:
            return False, f"参数 {self.name} 值不在选项中"
        if isinstance(value, (int, float)) and self.min_val is not None:
            if value < self.min_val:
                return False, f"参数 {self.name} 不能小于 {self.min_val}"
        if isinstance(value, (int, float)) and self.max_val is not None:
            if value > self.max_val:
                return False, f"参数 {self.name} 不能大于 {self.max_val}"
        return True, ""


@dataclass
class CapabilityInputSchema:
    """能力输入 Schema"""
    params: Dict[str, CapabilityParam] = field(default_factory=dict)

    def add_param(self, param: CapabilityParam):
        """添加参数定义"""
        self.params[param.name] = param

    def validate(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """批量验证输入数据"""
        errors = []
        for name, param in self.params.items():
            value = data.get(name)
            ok, msg = param.validate(value)
            if not ok:
                errors.append(msg)
        return len(errors) == 0, errors


@dataclass
class CapabilityOutput:
    """能力输出结果"""
    success: bool
    output_data: Any = None                    # 实际输出结果
    warnings: List[str] = field(default_factory=list)
    elapsed_seconds: float = 0.0               # 耗时
    engine_used: str = ""                      # 使用的引擎
    raw_result: Any = None                     # 原始引擎返回
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据


@dataclass
class CapabilityDescriptor:
    """能力描述信息"""
    capability_id: str                        # 唯一标识（如 portrait_enhance）
    display_name: str                         # 显示名称
    version: str = "1.0.0"                    # 版本
    description: str = ""                     # 描述
    author: str = ""                          # 作者/维护者
    category: str = "general"                 # 分类（portrait/repair/product等）
    priority: CapabilityPriority = CapabilityPriority.NORMAL
    input_schema: Optional[CapabilityInputSchema] = None
    output_schema: Optional[Dict[str, str]] = None  # 输出字段描述
    dependencies: List[str] = field(default_factory=list)  # 依赖的其他能力
    tags: List[str] = field(default_factory=list)
    is_private: bool = False                  # 是否为内部能力


# ================================================================
# CapabilityBase — 能力抽象基类
# ================================================================

class CapabilityBase(ABC):
    """
    AI 能力基类 — 所有AI能力必须继承此类

    必须实现的抽象方法：
    - get_descriptor() → 能力元数据
    - execute(input_params) → 执行推理，返回 Output

    生命周期方法（可选覆写）：
    - on_register() → 注册时回调
    - on_prepare() → 准备模型/资源
    - on_execute() → 具体执行逻辑（替代execute）
    - on_complete() → 完成后回调
    - on_cleanup() → 清理资源
    """

    @abstractmethod
    def get_descriptor(self) -> CapabilityDescriptor:
        """获取能力描述信息"""
        ...

    @abstractmethod
    def execute(self, params: Dict[str, Any], context: Optional[Dict] = None) -> CapabilityOutput:
        """
        执行AI能力

        Args:
            params: 参数字典
            context: 执行上下文（引擎选择、进度回调等）

        Returns:
            CapabilityOutput 对象
        """
        ...

    # ── 生命周期钩子 ──────────────────────

    def on_register(self):
        """能力注册后回调"""
        pass

    def on_prepare(self) -> bool:
        """
        准备执行所需资源

        Returns:
            是否准备成功
        """
        return True

    def on_execute(self, params: Dict[str, Any]) -> Any:
        """
        覆写此方法替代 execute() 直接实现推理逻辑

        Args:
            params: 输入参数

        Returns:
            原始引擎结果（execute会自动包装为CapabilityOutput）
        """
        raise NotImplementedError("覆写 on_execute 而非 execute")

    def on_complete(self, result: CapabilityOutput):
        """执行完成后回调"""
        pass

    def on_cleanup(self):
        """清理资源"""
        pass

    # ── 便捷方法 ──────────────────────────

    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """验证参数合法性"""
        desc = self.get_descriptor()
        if desc.input_schema:
            return desc.input_schema.validate(params)
        return True, []

    def check_available(self) -> bool:
        """检查能力是否可用"""
        return self.on_prepare()

    def __repr__(self):
        desc = self.get_descriptor()
        return f"Capability({desc.capability_id} v{desc.version})"


# ================================================================
# CapabilityRegistry — 能力注册中心
# ================================================================

class CapabilityRegistry:
    """
    全局能力注册中心 — 单例模式

    职责：
    - 能力注册与注销
    - 能力发现与查询
    - 版本管理
    - 依赖解析

    使用方式：
        reg = CapabilityRegistry.instance()
        reg.register(PortraitEnhance())
        caps = reg.find_by_category("portrait")
        cap = reg.get("portrait_enhance")
    """

    _instance = None

    @classmethod
    def instance(cls) -> 'CapabilityRegistry':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._capabilities: Dict[str, CapabilityBase] = {}
        self._categories: Dict[str, List[str]] = {}  # category -> [capability_ids]
        self._on_registry_change_callbacks: List[Callable] = []

    def register(self, capability: CapabilityBase) -> bool:
        """注册一个能力"""
        desc = capability.get_descriptor()
        cap_id = desc.capability_id

        if cap_id in self._capabilities:
            old_cap = self._capabilities[cap_id]
            old_desc = old_cap.get_descriptor()
            # 允许升级覆盖（版本号更高）
            if old_desc.version >= desc.version:
                return False
            logger.info(f"Capability {cap_id} 从 {old_desc.version} 升级到 {desc.version}")

        capability.on_register()
        self._capabilities[cap_id] = capability

        # 按分类索引
        category = desc.category or "general"
        if category not in self._categories:
            self._categories[category] = []
        if cap_id not in self._categories[category]:
            self._categories[category].append(cap_id)

        self._notify_change(registration=True, cap_id=cap_id)
        return True

    def unregister(self, cap_id: str) -> bool:
        """注销一个能力"""
        if cap_id not in self._capabilities:
            return False
        cap = self._capabilities.pop(cap_id)
        cap.on_cleanup()
        self._notify_change(registration=False, cap_id=cap_id)
        return True

    def get(self, cap_id: str) -> Optional[CapabilityBase]:
        """按ID获取能力实例"""
        return self._capabilities.get(cap_id)

    def find_by_category(self, category: str) -> List[CapabilityBase]:
        """按分类查找能力"""
        ids = self._categories.get(category, [])
        return [self._capabilities[i] for i in ids if i in self._capabilities]

    def find_by_tag(self, tag: str) -> List[CapabilityBase]:
        """按标签查找"""
        results = []
        for cap in self._capabilities.values():
            desc = cap.get_descriptor()
            if tag in desc.tags:
                results.append(cap)
        return results

    def list_all(self) -> List[CapabilityBase]:
        """列出所有已注册能力"""
        return list(self._capabilities.values())

    def list_available(self) -> List[CapabilityBase]:
        """列出所有就绪的能力"""
        return [c for c in self._capabilities.values() if c.check_available()]

    def get_categories(self) -> Dict[str, int]:
        """获取分类及对应能力数量"""
        return {cat: len(ids) for cat, ids in self._categories.items()}

    def has_capability(self, cap_id: str) -> bool:
        """检查是否存在某能力"""
        return cap_id in self._capabilities

    def get_statistics(self) -> Dict[str, Any]:
        """获取注册统计"""
        total = len(self._capabilities)
        categories = len(self._categories)
        available = sum(1 for c in self._capabilities.values() if c.check_available())
        return {
            "total": total,
            "categories": categories,
            "available": available,
            "by_category": dict(self.get_categories()),
        }

    def on_change(self, callback: Callable):
        """注册变更监听器"""
        self._on_registry_change_callbacks.append(callback)

    def _notify_change(self, registration: bool, cap_id: str):
        """通知变更"""
        for cb in self._on_registry_change_callbacks:
            try:
                cb(registration, cap_id)
            except Exception:
                pass


# ================================================================
# Pipeline — 能力编排引擎
# ================================================================

class PipelineStep:
    """Pipeline步骤"""
    def __init__(self, capability_id: str, inputs: Dict[str, Any], depends_on: Optional[List[str]] = None):
        self.capability_id = capability_id
        self.inputs = inputs
        self.depends_on = depends_on or []  # 前置步骤ID
        self.result: Optional[Any] = None
        self.error: Optional[str] = None
        self.elapsed_ms: float = 0.0


class PipelineEngine:
    """
    Pipeline编排引擎

    负责：
    - 步骤解析与拓扑排序
    - 参数校验
    - 依赖检测
    - 串行/并行执行
    - 异常处理与回滚
    - 日志输出
    """

    def __init__(self, registry: Optional[CapabilityRegistry] = None):
        self._registry = registry or CapabilityRegistry.instance()
        self._steps: List[PipelineStep] = []
        self._logs: List[str] = []
        self._callbacks: Dict[str, Callable] = {}

    def add_step(self, capability_id: str, inputs: Dict[str, Any],
                 depends_on: Optional[List[str]] = None) -> str:
        """
        添加执行步骤

        Args:
            capability_id: 能力ID
            inputs: 参数映射
            depends_on: 前置步骤ID列表

        Returns:
            步骤ID
        """
        step_id = f"step_{len(self._steps) + 1}"
        self._steps.append(PipelineStep(capability_id, inputs, depends_on))
        self._logs.append(f"Add step [{step_id}] -> {capability_id}")
        return step_id

    def remove_step(self, step_id: str) -> bool:
        """移除指定步骤"""
        idx = int(step_id.split("_")[1]) - 1
        if 0 <= idx < len(self._steps):
            self._steps.pop(idx)
            return True
        return False

    def validate_order(self) -> Tuple[bool, List[str]]:
        """验证执行顺序（拓扑排序检测循环依赖）"""
        errors = []
        visited = set()
        temp = set()

        def visit(step_id: str):
            if step_id in temp:
                errors.append(f"循环依赖: {step_id}")
                return
            if step_id in visited:
                return
            temp.add(step_id)
            step = self._steps[int(step_id.split("_")[1]) - 1] if step_id.startswith("step_") else None
            if step and step.depends_on:
                for dep in step.depends_on:
                    visit(dep)
            temp.remove(step_id)
            visited.add(step_id)

        for i, step in enumerate(self._steps):
            visit(f"step_{i + 1}")

        return len(errors) == 0, errors

    def execute(self, progress_callback: Optional[Callable] = None) -> CapabilityOutput:
        """
        执行整个Pipeline

        Returns:
            最终CapabilityOutput结果
        """
        ok, errors = self.validate_order()
        if not ok:
            return CapabilityOutput(
                success=False,
                error=f"Pipeline校验失败: {', '.join(errors)}",
            )

        step_results = {}
        last_output = None

        for i, step in enumerate(self._steps):
            step_id = f"step_{i + 1}"
            start = time.time()

            # 收集依赖结果
            merged_inputs = dict(step.inputs)
            for dep_id in step.depends_on:
                dep_result = step_results.get(dep_id)
                if dep_result and isinstance(dep_result, CapabilityOutput):
                    merged_inputs["_previous"] = dep_result.output_data
                    merged_inputs["context"] = dep_result.metadata

            # 执行能力
            cap = self._registry.get(step.capability_id)
            if not cap:
                error = f"能力不存在: {step.capability_id}"
                self._logs.append(f"[FAIL] {step_id}: {error}")
                return CapabilityOutput(success=False, error=error)

            try:
                output = cap.execute(merged_inputs)
                step_results[step_id] = output
                step_elapsed = time.time() - start
                step.elapsed_ms = round(step_elapsed * 1000, 2)

                self._logs.append(f"[OK]   {step_id}: {step.capability_id} ({step.elapsed_ms}ms)")

                if output.success:
                    last_output = output
                else:
                    self._logs.append(f"[WARN] {step_id} 返回非成功: {output.error}")
                    # 继续执行（非致命错误）

            except Exception as e:
                self._logs.append(f"[ERROR] {step_id}: {str(e)}")
                return CapabilityOutput(success=False, error=str(e))

            # 进度回调
            if progress_callback:
                progress_callback(i + 1, len(self._steps), step.capability_id)

        return CapabilityOutput(
            success=True,
            output_data=last_output.output_data if last_output else None,
            elapsed_seconds=sum(s.elapsed_ms for s in self._steps) / 1000.0,
            metadata={"pipeline_steps": len(self._steps), "results": step_results},
        )

    def log(self, message: str):
        self._logs.append(message)

    def get_logs(self) -> List[str]:
        return list(self._logs)

    def reset(self):
        """清空Pipeline"""
        self._steps.clear()
        self._logs.clear()
        self._callbacks.clear()


# ================================================================
# ExecutorHub — 能力执行枢纽
# ================================================================

class ExecutorHub:
    """
    能力执行枢纽 — 单例

    统一管理所有能力的运行时执行：
    - 能力实例缓存
    - 线程安全执行
    - 并发控制
    - 资源监控
    """

    _instance = None

    @classmethod
    def instance(cls) -> 'ExecutorHub':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._instances: Dict[str, Any] = {}     # cap_id → 实例
        self._lock = threading.Lock()
        self._max_concurrent = 4
        self._active_count = 0
        self._stats = {"executed": 0, "failed": 0, "total_time": 0.0}

    def execute(self, cap_id: str, params: Dict[str, Any],
                progress_cb: Optional[Callable] = None) -> CapabilityOutput:
        """
        执行指定能力

        Args:
            cap_id: 能力ID
            params: 参数
            progress_cb: 进度回调

        Returns:
            CapabilityOutput
        """
        registry = CapabilityRegistry.instance()
        cap = registry.get(cap_id)
        if not cap:
            return CapabilityOutput(success=False, error=f"未找到能力: {cap_id}")

        with self._lock:
            self._active_count += 1

        try:
            # 确保能力已准备
            if not cap.check_available():
                return CapabilityOutput(success=False, error=f"能力不可用: {cap_id}")

            start = time.time()
            output = cap.execute(params)
            elapsed = time.time() - start

            with self._lock:
                self._active_count -= 1
                self._stats["executed"] += 1
                self._stats["total_time"] += elapsed

                if not output.success:
                    self._stats["failed"] += 1

            return output

        except Exception as e:
            with self._lock:
                self._active_count -= 1
                self._stats["failed"] += 1
            return CapabilityOutput(success=False, error=str(e))

    def get_stats(self) -> Dict[str, Any]:
        return dict(self._stats, active=self._active_count)

    def clear_cache(self):
        """清理缓存实例"""
        with self._lock:
            self._instances.clear()
            self._active_count = 0


# ================================================================
# 全局初始化
# ================================================================

def init_capability_framework():
    """初始化全局Capability框架"""
    CapabilityRegistry.instance()
    ExecutorHub.instance()
    logger.info("AI Capability Framework 初始化完成")


if __name__ == "__main__":
    # 测试Capability框架
    print("=" * 50)
    print("  AI Capability Framework Test")
    print("=" * 50)

    # 创建测试能力
    class TestCap(CapabilityBase):
        def get_descriptor(self):
            return CapabilityDescriptor(
                capability_id="test_capability",
                display_name="测试能力",
                version="1.0.0",
                category="test",
                tags=["test"],
                input_schema=CapabilityInputSchema({
                    "message": CapabilityParam("message", "str", required=True),
                    "count": CapabilityParam("count", "int", default=1, min_val=1, max_val=10),
                }),
            )

        def execute(self, params: Dict[str, Any], context=None):
            msg = params.get("message", "hello")
            count = params.get("count", 1)
            result = f"{msg} " * count
            return CapabilityOutput(success=True, output_data=result.strip())

    # 注册与测试
    reg = CapabilityRegistry.instance()
    cap = TestCap()
    reg.register(cap)

    print(f"注册: {cap.get_descriptor().capability_id}")
    print(f"分类列表: {reg.get_categories()}")
    print(f"可用能力: {[c.get_descriptor().capability_id for c in reg.list_available()]}")

    exec_hub = ExecutorHub.instance()
    output = exec_hub.execute("test_capability", {"message": "Hello", "count": 3})
    print(f"执行结果: success={output.success}, data={output.output_data}")

    stats = exec_hub.get_stats()
    print(f"统计: {stats}")
