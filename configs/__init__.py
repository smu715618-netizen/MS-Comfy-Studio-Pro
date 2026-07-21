# 配置文件模块 __init__.py

"""
配置管理模块

提供统一的配置读取、合并和热重载能力。
支持多环境配置覆盖（default -> xpu -> local）。
"""

from src.config_manager import ConfigManager

# 全局配置单例
_config_instance = None


def get_config() -> ConfigManager:
    """获取全局配置实例（单例模式）"""
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigManager()
    return _config_instance


def reload_config():
    """重新加载配置"""
    global _config_instance
    _config_instance = ConfigManager()
