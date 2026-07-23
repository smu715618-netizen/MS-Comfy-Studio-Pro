"""AI Scheduler — AI 任务调度器

负责任务识别、资源调度、引擎选择。

未来所有 AI 能力统一经过此调度器。

流程：
1. 接收用户请求（如"一键磨皮"）
2. 自动识别需要的模型/节点/工作流
3. 检测资源是否就绪（未就绪则自动下载）
4. 选择最优推理引擎
5. 执行推理任务
6. 返回结果给用户

禁止业务层直接调用底层引擎或ComfyUI。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Callable


class TaskPriority(Enum):
    """任务优先级"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ScheduleTask:
    """调度的单个AI任务"""
    task_id: str
    capability: str                     # 能力标识（如"portrait_retouch"）
    priority: TaskPriority = TaskPriority.NORMAL
    engine_type: str = ""               # 目标引擎类型
    parameters: Dict[str, Any] = field(default_factory=dict)
    input_data: Any = None              # 输入数据
    callbacks: List[Callable] = field(default_factory=list)  # 进度回调
    status: str = "pending"             # pending/scheduled/executing/completed/failed
    result: Any = None                  # 执行结果
    error_message: str = ""
    started_at: float = 0.0
    completed_at: float = 0.0
    elapsed_seconds: float = 0.0


class AIScheduler(ABC):
    """
    AI 调度器（抽象基类）

    所有调度逻辑必须通过此接口。
    实现子类可接入不同的调度策略（本地/FIFO/LRU）。
    """

    @abstractmethod
    def submit_task(self, task: ScheduleTask) -> bool:
        """提交AI任务到队列"""
        ...

    @abstractmethod
    def execute_next(self) -> Optional[ScheduleTask]:
        """执行下一个任务"""
        ...

    @abstractmethod
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        ...

    @abstractmethod
    def get_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        ...

    @abstractmethod
    def get_queue_stats(self) -> Dict[str, int]:
        """获取队列统计"""
        ...

    @abstractmethod
    def release_resources(self):
        """释放所有调度资源"""
        ...


# ================================================================
# 默认调度器（占位实现，Phase 7 完善）
# ================================================================

class DefaultScheduler(AIScheduler):
    """
    默认调度器（占位实现）

    当前仅提供任务管理和状态追踪。
    实际调度逻辑在 Phase 7 实现。
    """

    def __init__(self):
        self._tasks: Dict[str, ScheduleTask] = {}
        self._queue: List[str] = []

    def submit_task(self, task: ScheduleTask) -> bool:
        self._tasks[task.task_id] = task
        self._queue.append(task.task_id)
        return True

    def execute_next(self) -> Optional[ScheduleTask]:
        if not self._queue:
            return None
        task_id = self._queue.pop(0)
        task = self._tasks.get(task_id)
        if task:
            task.status = "completed"
        return task

    def cancel_task(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task:
            task.status = "cancelled"
            if task_id in self._queue:
                self._queue.remove(task_id)
            return True
        return False

    def get_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        task = self._tasks.get(task_id)
        if not task:
            return None
        return {
            "status": task.status,
            "priority": task.priority.value,
            "elapsed_seconds": task.elapsed_seconds,
        }

    def get_queue_stats(self) -> Dict[str, int]:
        pending = sum(1 for t in self._tasks.values() if t.status == "pending")
        queued = len(self._queue)
        completed = sum(1 for t in self._tasks.values() if t.status == "completed")
        failed = sum(1 for t in self._tasks.values() if t.status == "failed")
        cancelled = sum(1 for t in self._tasks.values() if t.status == "cancelled")
        total = len(self._tasks)
        return {"total": total, "pending": pending, "queued": queued,
                "completed": completed, "failed": failed, "cancelled": cancelled}

    def release_resources(self):
        self._tasks.clear()
        self._queue.clear()
