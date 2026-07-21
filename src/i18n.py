"""
国际化 (i18n) 模块

提供多语言翻译支持：
- JSON 翻译文件加载
- 键路径查找（支持嵌套键，如 "app.name"）
- 默认值回退
- 运行时语言切换
- 翻译缺失警告
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from src.logger import get_logger

logger = get_logger("i18n")


class I18nManager:
    """
    国际化管理器

    管理多语言翻译文件，提供统一的翻译接口。

    翻译文件位于 configs/locales/{locale}.json
    支持嵌套键访问: "app.launcher.start_comfy"
    """

    def __init__(self, locale_dir: Optional[str] = None):
        """
        初始化国际化管理器

        Args:
            locale_dir: 翻译文件目录，默认为 configs/locales/
        """
        if locale_dir is None:
            # src/i18n.py -> ../configs/locales
            locale_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "..",
                "configs",
                "locales",
            )
        self._locale_dir = Path(locale_dir)
        self._translations: Dict[str, dict] = {}
        self._current_locale: str = "zh-CN"
        self._missing_keys: set = set()

        # 加载所有可用的翻译文件
        self._load_all_locales()

        # 设置默认语言为中文
        if "zh-CN" in self._translations:
            self._current_locale = "zh-CN"
            logger.info("默认语言: 中文 (zh-CN)")
        else:
            logger.warning("未找到中文翻译文件，使用英文")
            self._current_locale = "en-US"

    def _load_all_locales(self):
        """加载所有可用的翻译文件"""
        if not self._locale_dir.exists():
            logger.error(f"翻译目录不存在: {self._locale_dir}")
            return

        for filepath in self._locale_dir.glob("*.json"):
            locale_code = filepath.stem  # 如 "zh-CN", "en-US"
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._translations[locale_code] = data
                logger.info(f"已加载翻译: {locale_code}")
            except (json.JSONDecodeError, Exception) as e:
                logger.error(f"加载翻译文件失败 {filepath}: {e}")

    def set_locale(self, locale: str):
        """
        切换当前语言

        Args:
            locale: 语言代码，如 "zh-CN", "en-US"

        Raises:
            ValueError: 如果该语言不可用
        """
        if locale not in self._translations:
            raise ValueError(f"不可用的语言: {locale}。可用: {list(self._translations.keys())}")

        self._current_locale = locale
        self._missing_keys.clear()
        logger.info(f"语言已切换为: {locale}")

    @property
    def current_locale(self) -> str:
        """当前语言代码"""
        return self._current_locale

    @property
    def available_locales(self) -> List[str]:
        """可用的语言列表"""
        return list(self._translations.keys())

    def t(self, key: str, default: Optional[str] = None, **kwargs) -> str:
        """
        翻译键值

        通过点分隔路径查找嵌套翻译键。
        如果找不到且提供了 default，则返回 default。
        如果找不到且没有 default，则返回 key 本身。

        Args:
            key: 翻译键，如 "app.name"
            default: 键不存在时的默认返回值
            **kwargs: 格式化参数，如 t("greeting", name="World") -> "Hello World"

        Returns:
            翻译后的字符串
        """
        value = self._get_nested_value(self._translations.get(self._current_locale, {}), key)

        if value is None:
            # 尝试 fallback 到英文
            if self._current_locale != "en-US":
                value = self._get_nested_value(
                    self._translations.get("en-US", {}), key
                )

            if value is None:
                if default is not None:
                    value = default
                else:
                    value = key
                    if key not in self._missing_keys:
                        logger.warning(f"翻译缺失: '{key}' (locale: {self._current_locale})")
                        self._missing_keys.add(key)

        # 支持格式化参数
        if kwargs:
            try:
                value = value.format(**kwargs)
            except (KeyError, IndexError, ValueError):
                pass  # 格式化失败则返回原始值

        return value

    def _get_nested_value(self, data: dict, key: str) -> Optional[str]:
        """
        通过点分隔路径获取嵌套字典的值

        Args:
            data: 字典数据
            key: 点分隔的路径

        Returns:
            对应的值，或 None
        """
        keys = key.split(".")
        current = data
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return None
        return str(current) if current is not None else None

    def get_all_translations(self, locale: Optional[str] = None) -> dict:
        """
        获取指定语言的全部翻译

        Args:
            locale: 语言代码，默认为当前语言

        Returns:
            完整的翻译字典
        """
        target = locale or self._current_locale
        return self._translations.get(target, {})

    def add_translation(self, locale: str, translations: dict):
        """
        动态添加翻译（用于运行时加载额外翻译）

        Args:
            locale: 语言代码
            translations: 翻译字典
        """
        if locale in self._translations:
            self._translations[locale].update(translations)
        else:
            self._translations[locale] = translations
        logger.info(f"已添加翻译: {locale}")

    def __repr__(self):
        return f"I18nManager(locale={self._current_locale}, available={self.available_locales})"


# 全局 i18n 单例
_i18n_instance = None


def get_i18n() -> I18nManager:
    """获取全局 i18n 实例（单例）"""
    global _i18n_instance
    if _i18n_instance is None:
        _i18n_instance = I18nManager()
    return _i18n_instance


def t(key: str, default: Optional[str] = None, **kwargs) -> str:
    """快捷翻译函数"""
    return get_i18n().t(key, default=default, **kwargs)


def set_locale(locale: str):
    """切换语言"""
    get_i18n().set_locale(locale)
