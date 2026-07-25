"""Portrait AI API Layer — 人物修图统一入口

所有GUI/CLI/Web请求必须通过此API访问Portrait AI能力。
禁止绕过此API直接调用底层Engine或ComfyUI。

架构：
    GUI/CLI → PortraitAPI → CapabilityRegistry → Pipeline → Scheduler → EngineAdapter → ComfyUI

新增能力（Module 02）：
    - face_detect: 人脸检测
    - portrait_segment: 人像分割
    - upscale_face: AI高清修复
    - remove_object: AI对象消除
    - expand_canvas: AI图像扩图
    - inpaint_region: 局部重绘

未来扩展（后续Module）：
    - retouch_skin: 磨皮美白
    - adjust_features: 五官微调
    - hair_color: 染发换色
    - body_shape: 身材调整
    - background_replace: 背景替换
"""

from pathlib import Path
from typing import List, Optional, Dict, Any

# 确保项目路径在搜索路径中
_project_root = Path(__file__).parent.parent.parent
if str(_project_root) not in __import__('sys').path:
    __import__('sys').path.insert(0, str(_project_root))

from src.capability.base import CapabilityRegistry, CapabilityOutput


class PortraitAPI:
    """
    Portrait AI 统一API

    提供5个核心修图能力的统一调用接口。
    所有底层细节（模型/节点/工作流/参数映射）对用户完全隐藏。
    
    使用示例:
        api = PortraitAPI()
        result = api.face_detect(image_path)
        result = api.upscale_face(image_path)
        # ... 或直接使用 do_all(image_path) 一键完成全套流程
    """

    _instance = None

    @classmethod
    def instance(cls) -> 'PortraitAPI':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._registry = CapabilityRegistry.instance()

    # ── 5个核心修图能力 ──────────────────────────

    def face_detect(self, image_path: str, max_faces: int = 10) -> CapabilityOutput:
        """
        人脸检测 — 识别图片中的人脸并返回位置和数量

        Args:
            image_path: 输入图片路径
            max_faces: 最大检测人脸数（默认10）

        Returns:
            CapabilityOutput containing face detection results
        """
        return self._registry.execute('portrait_face_detect', {
            'image_path': image_path,
            'max_faces': max_faces,
        })

    def portrait_segment(self, image_path: str, background: Optional[str] = 'transparent') -> CapabilityOutput:
        """
        人像分割 — 提取人物主体与背景分离

        Args:
            image_path: 输入图片路径
            background: 背景类型 (transparent/blur/crop/color)

        Returns:
            CapabilityOutput containing segmentation mask + cropped person
        """
        return self._registry.execute('portrait_segment', {
            'image_path': image_path,
            'background': background or 'transparent',
        })

    def upscale_face(self, image_path: str, scale_factor: float = 2.0) -> CapabilityOutput:
        """
        AI高清修复 — 提升面部细节清晰度

        Args:
            image_path: 输入图片路径
            scale_factor: 放大倍数（默认2倍）

        Returns:
            CapabilityOutput containing restored face image
        """
        return self._registry.execute('portrait_upscale_face', {
            'image_path': image_path,
            'scale_factor': scale_factor,
        })

    def remove_object(self, image_path: str, mask_image: Optional[str] = None, prompt: str = '') -> CapabilityOutput:
        """
        AI对象消除 — 移除图片中不需要的物体

        Args:
            image_path: 输入图片路径
            mask_image: 遮罩图片路径（可选，自动生成）
            prompt: 描述要移除的内容（辅助AI理解）

        Returns:
            CapabilityOutput containing cleaned image
        """
        return self._registry.execute('portrait_remove_object', {
            'image_path': image_path,
            'mask_image': mask_image,
            'prompt': prompt or '',
        })

    def expand_canvas(self, image_path: str, expansion_ratio: float = 1.5) -> CapabilityOutput:
        """
        AI图像扩图 — 智能扩展画布生成内容

        Args:
            image_path: 原始图片路径
            expansion_ratio: 扩图比例（默认1.5倍）

        Returns:
            CapabilityOutput containing expanded canvas image
        """
        return self._registry.execute('portrait_expand_canvas', {
            'image_path': image_path,
            'expansion_ratio': expansion_ratio,
        })

    def inpaint_region(self, image_path: str, mask_path: str, prompt: str, negative_prompt: str = '') -> CapabilityOutput:
        """
        局部重绘 — 针对指定区域重新生成内容

        Args:
            image_path: 原始图片路径
            mask_path: 遮罩区域路径
            prompt: 生成提示词（描述想要的内容）
            negative_prompt: 负面提示词

        Returns:
            CapabilityOutput containing inpainted image
        """
        return self._registry.execute('portrait_inpaint_region', {
            'image_path': image_path,
            'mask_path': mask_path,
            'prompt': prompt,
            'negative_prompt': negative_prompt or '',
        })

    # ── 一键全流程 ────────────────────────────────

    def do_all(self, image_path: str, quality: str = 'standard', output_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        一键完成全套修图流程（人脸检测→分割→高清修复→消除→扩图）

        Args:
            image_path: 输入图片路径
            quality: 质量等级 ('fast'/'standard'/'ultra')
            output_dir: 输出目录（默认同输入目录）

        Returns:
            包含各步骤结果的字典
        """
        results = {}
        try:
            for method_name in ['face_detect', 'portrait_segment', 'upscale_face',
                               'remove_object', 'expand_canvas']:
                method = getattr(self, method_name)
                kwargs = {'image_path': image_path}
                if method_name == 'upscale_face':
                    kwargs['scale_factor'] = 2.0
                elif method_name == 'remove_object':
                    kwargs['prompt'] = 'unwanted objects'
                elif method_name == 'expand_canvas':
                    kwargs['expansion_ratio'] = 1.5
                elif method_name == 'inpaint_region':
                    continue  # inpaint需要mask，跳过

                try:
                    output = method(**kwargs)
                    results[method_name] = {'success': output.success, 'data': output.output_data}
                except Exception as e:
                    results[method_name] = {'success': False, 'error': str(e)}
        except Exception as e:
            results['_error'] = str(e)
        return results


if __name__ == '__main__':
    # Test: verify all capabilities are registered
    api = PortraitAPI.instance()
    reg = CapabilityRegistry.instance()
    stats = reg.get_statistics()
    print(f"Registered capabilities: {stats['total']}")
    print(f"Available: {stats['available']}")
