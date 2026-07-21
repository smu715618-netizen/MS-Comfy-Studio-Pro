"""
配置管理模块

提供统一的配置读取、写入、合并和热重载能力。
支持多环境配置覆盖链: default.yaml -> xpu.yaml -> local.yaml
所有配置集中管理，通过 YAML 文件定义。
"""

import os
import yaml
import copy
from pathlib import Path
from typing import Any, Dict, List, Optional
from src.logger import get_logger

logger = get_logger("config")


class ConfigManager:
    """
    配置管理器

    负责加载、合并和管理所有 YAML 配置文件。
    支持嵌套键访问（如 config['gpu']['device']）。

    配置加载顺序（后加载的覆盖前面的）:
    1. default.yaml - 默认配置
    2. xpu.yaml - Intel XPU 覆盖配置
    3. local.yaml - 用户本地覆盖配置（可选）
    """

    def __init__(self, config_dir: Optional[str] = None):
        """
        初始化配置管理器

        Args:
            config_dir: 配置文件目录，默认为 configs/
        """
        if config_dir is None:
            # 自动检测项目根目录
            # src/config_manager.py -> src -> project_root -> configs
            config_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "..",
                "configs",
            )
        self._config_dir = Path(config_dir)
        self._config: Dict[str, Any] = {}
        self._raw_configs: Dict[str, Dict[str, Any]] = {}
        self._watch_files: List[Path] = []
        self._callbacks: List[callable] = []

        # 加载配置
        self._load_all()
        logger.info(f"配置已加载: {self._config_dir}")

    def _load_all(self):
        """按顺序加载所有配置文件"""
        # 1. 加载默认配置
        self._load_file("default.yaml", priority=0)
        # 2. 加载 XPU 覆盖配置
        self._load_file("xpu.yaml", priority=1)
        # 3. 加载本地覆盖配置（如果存在）
        local_path = self._config_dir / "local.yaml"
        if local_path.exists():
            self._load_file("local.yaml", priority=2)
            logger.info("已加载本地覆盖配置: local.yaml")
        else:
            logger.debug("未找到本地覆盖配置: local.yaml（使用默认值）")

    def _load_file(self, filename: str, priority: int = 0):
        """
        加载单个 YAML 配置文件

        Args:
            filename: 文件名
            priority: 优先级（数字越大覆盖优先级越高）
        """
        filepath = self._config_dir / filename
        if not filepath.exists():
            logger.warning(f"配置文件不存在: {filepath}")
            return

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if data is None:
                logger.warning(f"配置文件为空: {filepath}")
                return

            # 深拷贝避免引用问题
            data = copy.deepcopy(data)
            self._raw_configs[filename] = data

            # 合并到主配置
            self._deep_merge(self._config, data)
            logger.info(f"已加载配置: {filename}")

        except yaml.YAMLError as e:
            logger.error(f"解析 YAML 失败 {filepath}: {e}")
        except Exception as e:
            logger.error(f"读取配置失败 {filepath}: {e}")

    @staticmethod
    def _deep_merge(base: dict, override: dict):
        """
        深合并两个字典

        Args:
            base: 基础字典
            override: 覆盖字典（优先级更高）
        """
        for key, value in override.items():
            if (
                key in base
                and isinstance(base[key], dict)
                and isinstance(value, dict)
            ):
                ConfigManager._deep_merge(base[key], value)
            else:
                base[key] = copy.deepcopy(value)

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        通过点分隔路径获取配置值

        Args:
            key_path: 点分隔的配置路径，如 "gpu.device"
            default: 键不存在时的默认值

        Returns:
            配置值，或 default

        Examples:
            >>> config.get("gpu.device")
            "xpu"
            >>> config.get("paths.data_dir", "data")
            "data"
        """
        keys = key_path.split(".")
        value = self._config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def set(self, key_path: str, value: Any):
        """
        通过点分隔路径设置配置值

        Args:
            key_path: 点分隔的配置路径
            value: 新值
        """
        keys = key_path.split(".")
        config = self._config
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        config[keys[-1]] = value

        # 通知监听者
        self._notify_callbacks(key_path, value)

    def get_section(self, section: str) -> dict:
        """
        获取整个配置节

        Args:
            section: 配置节名称，如 "gpu", "paths"

        Returns:
            该节的配置字典
        """
        return self._config.get(section, {})

    def save_local_override(self, filepath: Optional[str] = None):
        """
        将当前配置保存为用户本地覆盖文件

        Args:
            filepath: 保存路径，默认为 configs/local.yaml
        """
        if filepath is None:
            filepath = str(self._config_dir / "local.yaml")

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                yaml.dump(
                    self._config,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                )
            logger.info(f"本地配置已保存到: {filepath}")
        except Exception as e:
            logger.error(f"保存本地配置失败: {e}")

    def reload(self):
        """重新加载所有配置文件"""
        self._config.clear()
        self._raw_configs.clear()
        self._load_all()
        logger.info("配置已重新加载")

    def watch(self, callback: callable):
        """
        注册配置变更回调

        Args:
            callback: 配置变更时调用的函数 (key_path, value) -> None
        """
        self._callbacks.append(callback)

    def _notify_callbacks(self, key_path: str, value: Any):
        """通知所有回调函数"""
        for cb in self._callbacks:
            try:
                cb(key_path, value)
            except Exception as e:
                logger.error(f"配置回调执行失败: {e}")

    @property
    def config_dir(self) -> Path:
        """配置文件目录"""
        return self._config_dir

    @property
    def raw_config(self) -> Dict[str, Any]:
        """原始配置字典（只读）"""
        return copy.deepcopy(self._config)

    def __repr__(self):
        return f"ConfigManager(config_dir={self._config_dir})"


# 全局配置单例
_config_instance = None


def get_config() -> ConfigManager:
    """
    获取全局配置实例（单例模式）

    Returns:
        ConfigManager 实例
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigManager()
    return _config_instance
