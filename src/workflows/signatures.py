"""节点签名预定义

定义 ComfyUI 核心节点的输入/输出签名。
这些签名用于 UI 表单生成、连接校验和参数绑定。
"""

from src.workflows.nodes import NodeSignature, NodeType, ParamType, ParamInfo, NodeRegistry

# ============================================================
# 核心节点签名
# ============================================================

# CheckpointLoaderSimple
NodeRegistry.register(NodeSignature(
    node_class="CheckpointLoaderSimple",
    display_name="加载 Checkpoint",
    node_type=NodeType.BUILTIN,
    category="loaders",
    description="加载 Stable Diffusion 模型检查点",
    input_params=[
        ParamInfo(name="ckpt_name", param_type=ParamType.CHOICE,
                  display_name="模型名称", tooltip="选择要加载的模型文件"),
    ],
    output_params=[
        ParamInfo(name="model", param_type=ParamType.MODEL),
        ParamInfo(name="clip", param_type=ParamType.CLIP),
        ParamInfo(name="vae", param_type=ParamType.VAE),
    ],
))

# CLIPTextEncode
NodeRegistry.register(NodeSignature(
    node_class="CLIPTextEncode",
    display_name="CLIP 文本编码",
    node_type=NodeType.BUILTIN,
    category="conditioning",
    description="将文本提示词编码为条件向量",
    input_params=[
        ParamInfo(name="clip", param_type=ParamType.CLIP),
        ParamInfo(name="text", param_type=ParamType.STRING,
                  display_name="提示词", tooltip="输入文本提示词"),
    ],
    output_params=[
        ParamInfo(name="conditioning", param_type=ParamType.CONDITIONING),
    ],
))

# KSampler
NodeRegistry.register(NodeSignature(
    node_class="KSampler",
    display_name="K 采样器",
    node_type=NodeType.BUILTIN,
    category="sampling",
    description="使用 K 采样算法生成图像",
    input_params=[
        ParamInfo(name="model", param_type=ParamType.MODEL),
        ParamInfo(name="positive", param_type=ParamType.CONDITIONING),
        ParamInfo(name="negative", param_type=ParamType.CONDITIONING),
        ParamInfo(name="latent_image", param_type=ParamType.LATENT),
        ParamInfo(name="seed", param_type=ParamType.INT, default=0,
                  display_name="随机种子"),
        ParamInfo(name="steps", param_type=ParamType.INT, default=20,
                  display_name="步数", min_val=1, max_val=100),
        ParamInfo(name="cfg", param_type=ParamType.FLOAT, default=8.0,
                  display_name="CFG 系数", min_val=1.0, max_val=30.0, step=0.5),
        ParamInfo(name="sampler_name", param_type=ParamType.CHOICE,
                  default="euler", choices=["euler", "euler_ancestral",
                                           "heun", "heunpp2", "dpm_2",
                                           "dpm_2_ancestral", "lms",
                                           "dpm_fast", "dpm_adaptive"]),
        ParamInfo(name="scheduler", param_type=ParamType.CHOICE,
                  default="normal", choices=["normal", "karras", "exponential",
                                            "sgm_uniform", "simple", "ddim_uniform"]),
        ParamInfo(name="denoise", param_type=ParamType.FLOAT, default=1.0,
                  display_name="去噪强度", min_val=0.0, max_val=1.0, step=0.01),
    ],
    output_params=[
        ParamInfo(name="latent", param_type=ParamType.LATENT),
    ],
))

# EmptyLatentImage
NodeRegistry.register(NodeSignature(
    node_class="EmptyLatentImage",
    display_name="空潜空间图像",
    node_type=NodeType.BUILTIN,
    category="latent",
    description="创建空的潜空间张量",
    input_params=[
        ParamInfo(name="width", param_type=ParamType.INT, default=512,
                  display_name="宽度", min_val=64, max_val=2048, step=64),
        ParamInfo(name="height", param_type=ParamType.INT, default=512,
                  display_name="高度", min_val=64, max_val=2048, step=64),
        ParamInfo(name="batch_size", param_type=ParamType.INT, default=1,
                  display_name="批次大小", min_val=1, max_val=64),
    ],
    output_params=[
        ParamInfo(name="latent", param_type=ParamType.LATENT),
    ],
))

# VAEDecode
NodeRegistry.register(NodeSignature(
    node_class="VAEDecode",
    display_name="VAE 解码",
    node_type=NodeType.BUILTIN,
    category="latent",
    description="将潜空间张量解码为图像",
    input_params=[
        ParamInfo(name="vae", param_type=ParamType.VAE),
        ParamInfo(name="samples", param_type=ParamType.LATENT),
    ],
    output_params=[
        ParamInfo(name="images", param_type=ParamType.IMAGE),
    ],
))

# SaveImage
NodeRegistry.register(NodeSignature(
    node_class="SaveImage",
    display_name="保存图片",
    node_type=NodeType.BUILTIN,
    category="image",
    description="保存生成的图像到文件",
    input_params=[
        ParamInfo(name="images", param_type=ParamType.IMAGE),
        ParamInfo(name="filename_prefix", param_type=ParamType.STRING,
                  default="ComfyUI", display_name="文件名前缀"),
    ],
    output_params=[
        ParamInfo(name="images", param_type=ParamType.IMAGE),
    ],
    extra_info={"output_node": True},
))

# UpscaleImage
NodeRegistry.register(NodeSignature(
    node_class="UpscaleImage",
    display_name="图像放大",
    node_type=NodeType.BUILTIN,
    category="image",
    description="使用超分辨率模型放大图像",
    input_params=[
        ParamInfo(name="image", param_type=ParamType.IMAGE),
        ParamInfo(name="upscale_model", param_type=ParamType.MODEL),
        ParamInfo(name="scale", param_type=ParamType.FLOAT, default=2.0,
                  display_name="放大倍数", min_val=1.0, max_val=8.0, step=0.1),
    ],
    output_params=[
        ParamInfo(name="images", param_type=ParamType.IMAGE),
    ],
))

# ControlNetApply
NodeRegistry.register(NodeSignature(
    node_class="ControlNetApply",
    display_name="应用 ControlNet",
    node_type=NodeType.BUILTIN,
    category="conditioning",
    description="将 ControlNet 应用到条件向量",
    input_params=[
        ParamInfo(name="positive", param_type=ParamType.CONDITIONING),
        ParamInfo(name="negative", param_type=ParamType.CONDITIONING),
        ParamInfo(name="control_net", param_type=ParamType.MODEL),
        ParamInfo(name="image", param_type=ParamType.IMAGE),
        ParamInfo(name="strength", param_type=ParamType.FLOAT, default=1.0,
                  display_name="强度", min_val=0.0, max_val=1.0, step=0.01),
    ],
    output_params=[
        ParamInfo(name="positive", param_type=ParamType.CONDITIONING),
        ParamInfo(name="negative", param_type=ParamType.CONDITIONING),
    ],
))

# ImageScale
NodeRegistry.register(NodeSignature(
    node_class="ImageScale",
    display_name="图像缩放",
    node_type=NodeType.BUILTIN,
    category="image",
    description="缩放图像尺寸",
    input_params=[
        ParamInfo(name="image", param_type=ParamType.IMAGE),
        ParamInfo(name="width", param_type=ParamType.INT, default=512,
                  display_name="目标宽度", min_val=64),
        ParamInfo(name="height", param_type=ParamType.INT, default=512,
                  display_name="目标高度", min_val=64),
        ParamInfo(name="crop", param_type=ParamType.CHOICE, default="disabled",
                  choices=["disabled", "center"]),
    ],
    output_params=[
        ParamInfo(name="images", param_type=ParamType.IMAGE),
    ],
))

# LoadImage
NodeRegistry.register(NodeSignature(
    node_class="LoadImage",
    display_name="加载图像",
    node_type=NodeType.BUILTIN,
    category="image",
    description="从文件加载图像",
    input_params=[],
    output_params=[
        ParamInfo(name="images", param_type=ParamType.IMAGE),
        ParamInfo(name="mask", param_type=ParamType.MASK, optional=True),
    ],
))
