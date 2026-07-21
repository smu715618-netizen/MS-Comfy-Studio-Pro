"""
国际化测试
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.i18n import I18nManager


class TestI18nManager:
    """测试国际化管理器"""

    def setup_method(self):
        """每次测试前创建新的 I18nManager"""
        self.i18n = I18nManager()

    def test_default_locale(self):
        """测试默认语言为中文"""
        assert self.i18n.current_locale == "zh-CN"

    def test_available_locales(self):
        """测试可用语言列表"""
        assert "zh-CN" in self.i18n.available_locales
        assert "en-US" in self.i18n.available_locales

    def test_translate_zh(self):
        """测试中文翻译"""
        result = self.i18n.t("app.name")
        assert result == "MS Comfy Studio Pro"

    def test_translate_en(self):
        """测试英文翻译"""
        self.i18n.set_locale("en-US")
        result = self.i18n.t("app.name")
        assert result == "MS Comfy Studio Pro"

    def test_nested_key(self):
        """测试嵌套键翻译"""
        result = self.i18n.t("launcher.start_comfy")
        assert result == "启动 ComfyUI"

    def test_missing_key_returns_default(self):
        """测试翻译缺失时使用默认值"""
        result = self.i18n.t("nonexistent.key", default="fallback")
        assert result == "fallback"

    def test_missing_key_returns_key(self):
        """测试翻译缺失时返回键本身"""
        result = self.i18n.t("nonexistent.key")
        assert result == "nonexistent.key"

    def test_format_params(self):
        """测试格式化参数（如果翻译支持）"""
        # 当前翻译文件不包含格式化参数，此测试验证不会崩溃
        result = self.i18n.t("app.name", extra="ignored")
        assert result == "MS Comfy Studio Pro"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
