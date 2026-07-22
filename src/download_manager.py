"""download_manager.py — 统一下载管理模块

为模型、插件、ComfyUI更新等提供统一的下载基础设施。

设计原则：
- 仅定义接口和核心逻辑
- 按需实例化，不占用后台资源
- 支持断点续传、进度回调、重试、取消

后续阶段：
- 模型下载（引用 DownloadManager）
- 节点/插件安装下载
- 应用更新下载
"""

import os
import sys
import time
import hashlib
import threading
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable, Dict, Any, List
from urllib.parse import urlparse

# 确保项目路径在搜索路径中
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.logger import get_logger

logger = get_logger("download")


class DownloadStatus(Enum):
    """下载状态枚举"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class DownloadTask:
    """单个下载任务"""
    url: str
    dest_path: str
    filename: str = ""
    status: DownloadStatus = DownloadStatus.PENDING
    total_bytes: int = 0
    downloaded_bytes: int = 0
    speed_mbps: float = 0.0
    error_msg: str = ""
    retries: int = 0
    max_retries: int = 3
    chunk_size: int = 8 * 1024 * 1024

    _cancel_event: threading.Event = field(default_factory=threading.Event, repr=False)
    _progress_callback: Optional[Callable] = None
    _stop_event: bool = False

    def set_progress_callback(self, callback: Callable):
        self._progress_callback = callback

    @property
    def task_id(self) -> str:
        return f"{self.filename}@{urlparse(self.url).netloc}"

    @property
    def progress_percent(self) -> float:
        if self.total_bytes <= 0:
            return 0.0
        return min(100.0, (self.downloaded_bytes / self.total_bytes) * 100)

    @property
    def is_active(self) -> bool:
        return self.status in (DownloadStatus.DOWNLOADING,)

    @property
    def is_terminal(self) -> bool:
        return self.status in (DownloadStatus.COMPLETED, DownloadStatus.FAILED, DownloadStatus.CANCELLED)

    def cancel(self):
        self._stop_event = True
        self._cancel_event.set()

    def should_stop(self) -> bool:
        return self._stop_event or self._cancel_event.is_set()


class DownloadManager:
    """
    统一下载管理器

    提供单文件/多文件并发下载、进度回调、自动重试、任务取消、SHA256校验。
    """

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        max_concurrent: int = 2,
        timeout: int = 3600,
        retry_count: int = 3,
        chunk_size_mb: int = 8,
    ):
        if cache_dir is None:
            cache_dir = str(_project_root / "data" / ".downloads_cache")
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._max_concurrent = max_concurrent
        self._timeout = timeout
        self._retry_count = retry_count
        self._chunk_size = chunk_size_mb * 1024 * 1024
        self._tasks: Dict[str, DownloadTask] = {}
        self._lock = threading.RLock()

    def add_task(
        self,
        url: str,
        dest_path: str,
        filename: str = "",
        max_retries: int = None,
        progress_callback: Optional[Callable] = None,
    ) -> DownloadTask:
        task = DownloadTask(
            url=url, dest_path=dest_path,
            filename=filename or self._extract_filename(url),
            max_retries=max_retries or self._retry_count,
        )
        task.set_progress_callback(progress_callback)
        with self._lock:
            self._tasks[task.task_id] = task
        logger.info(f"添加下载任务: {task.task_id}")
        return task

    def remove_task(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if task and not task.is_terminal:
                task.cancel()
            self._tasks.pop(task_id, None)
        return True

    def clear_completed_tasks(self):
        with self._lock:
            self._tasks = {tid: t for tid, t in self._tasks.items() if not t.is_terminal}

    def get_all_tasks(self) -> Dict[str, DownloadTask]:
        with self._lock:
            return dict(self._tasks)

    def get_task(self, task_id: str) -> Optional[DownloadTask]:
        with self._lock:
            return self._tasks.get(task_id)

    def cancel_all(self):
        with self._lock:
            for task in self._tasks.values():
                task.cancel()

    def wait_for_completion(self, timeout: int = 0) -> bool:
        """等待所有活动任务完成（同步阻塞）。实际GUI用轮询查询任务状态更合适。"""
        deadline = time.time() + timeout if timeout > 0 else None
        while True:
            active = [t for t in self._tasks.values() if t.is_active]
            if not active:
                break
            if deadline and time.time() >= deadline:
                return False
            time.sleep(0.5)
        completed = sum(1 for t in self._tasks.values() if t.status == DownloadStatus.COMPLETED)
        failed = sum(1 for t in self._tasks.values() if t.status == DownloadStatus.FAILED)
        return failed == 0

    def on_progress(self, callback: Callable):
        self._global_callbacks.append(callback) if hasattr(self, '_global_callbacks') else None

    # ---- 内部方法 ----

    def _start_download_thread(self, task_id: str):
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return
        logger.info(f"开始下载: {task.filename}")
        task.status = DownloadStatus.DOWNLOADING
        try:
            self._execute_download(task)
        except Exception as e:
            logger.error(f"下载失败: {task_id} - {e}")
            task.status = DownloadStatus.FAILED
            task.error_msg = str(e)
        finally:
            if task.status == DownloadStatus.DOWNLOADING and not task.should_stop():
                task.status = DownloadStatus.COMPLETED

    def _execute_download(self, task: DownloadTask):
        """执行单次下载（含重试逻辑）"""
        import requests
        dest_dir = Path(task.dest_path)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_file = dest_dir / task.filename

        headers = {}
        if dest_file.exists():
            existing_size = dest_file.stat().st_size
            if existing_size > 0:
                headers["Range"] = f"bytes={existing_size}-"

        start_time = time.time()

        try:
            resp = requests.head(task.url, timeout=10)
            if resp.status_code == 200:
                content_length = resp.headers.get('Content-Length')
                if content_length:
                    task.total_bytes = int(content_length)
        except Exception:
            pass

        try:
            resp = requests.get(task.url, headers=headers, stream=True, timeout=self._timeout)
            resp.raise_for_status()

            actual_start = dest_file.stat().st_size if dest_file.exists() else 0
            downloaded = actual_start
            last_update = time.time()

            with open(dest_file, "ab") as f:
                for chunk in resp.iter_content(chunk_size=task.chunk_size):
                    if task.should_stop():
                        task.status = DownloadStatus.CANCELLED
                        return
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        task.downloaded_bytes = downloaded
                        now = time.time()
                        if now - last_update >= 0.5:
                            elapsed = now - start_time
                            speed = (downloaded / (1024*1024)) / max(elapsed, 0.1)
                            task.speed_mbps = round(speed, 2)
                            last_update = now
                            if task._progress_callback:
                                try:
                                    task._progress_callback(task, downloaded, task.total_bytes, speed)
                                except Exception:
                                    pass

            if task.total_bytes and downloaded < task.total_bytes:
                raise ValueError("下载不完整")

            if task._progress_callback and not task.should_stop():
                task._progress_callback(task, downloaded, task.total_bytes, 0)

        except requests.exceptions.RequestException as e:
            if task.retries < task.max_retries:
                task.retries += 1
                wait_time = min(2 ** task.retries, 30)
                logger.warning(f"下载失败，{wait_time}s后重试 ({task.retries}/{task.max_retries}): {e}")
                time.sleep(wait_time)
                task.downloaded_bytes = 0
                self._execute_download(task)
            else:
                task.status = DownloadStatus.FAILED
                task.error_msg = str(e)
                raise

    def _validate_hash(self, filepath: str, expected_hash: str) -> bool:
        try:
            sha256 = hashlib.sha256()
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    sha256.update(chunk)
            return sha256.hexdigest().lower() == expected_hash.lower()
        except Exception:
            return False

    def get_statistics(self) -> dict:
        tasks = list(self._tasks.values())
        return {
            "total": len(tasks),
            "active": sum(1 for t in tasks if t.is_active),
            "completed": sum(1 for t in tasks if t.status == DownloadStatus.COMPLETED),
            "failed": sum(1 for t in tasks if t.status == DownloadStatus.FAILED),
            "cancelled": sum(1 for t in tasks if t.status == DownloadStatus.CANCELLED),
            "pending": sum(1 for t in tasks if t.status == DownloadStatus.PENDING),
            "total_downloaded_mb": round(sum(t.downloaded_bytes for t in tasks) / (1024 * 1024), 2),
        }

    @staticmethod
    def _extract_filename(url: str) -> str:
        from urllib.parse import unquote
        parsed = urlparse(url)
        name = Path(unquote(parsed.path)).name
        if not name or name in ("", "/"):
            name = "downloaded_file"
        return name


def get_download_manager() -> DownloadManager:
    if not hasattr(get_download_manager, "_instance"):
        get_download_manager._instance = DownloadManager()
    return get_download_manager._instance


if __name__ == "__main__":
    mgr = DownloadManager(max_concurrent=1)
    print(f"SHA256验证测试: {mgr._validate_hash(__file__, 'nonexistent')}")
    stats = mgr.get_statistics()
    print(f"统计: {stats}")
