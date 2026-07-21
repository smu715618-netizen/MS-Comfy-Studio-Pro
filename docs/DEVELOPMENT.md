# 开发文档

## 项目结构

```
MS-Comfy-Studio-Pro/
├── configs/           # 配置文件
├── src/               # 源代码
│   ├── core/          # 核心框架
│   ├── gui/           # 图形界面
│   ├── models/        # 模型管理（框架）
│   ├── nodes/         # 节点管理（框架）
│   ├── workflows/     # 工作流管理（框架）
│   ├── plugins/       # 插件管理（框架）
│   └── updater/       # 更新系统（框架）
├── data/              # 数据目录
├── tests/             # 测试
├── docs/              # 文档
└── assets/            # 静态资源
```

## 编码规范

### 命名约定

- 模块名: snake_case
- 类名: PascalCase
- 函数/变量: snake_case
- 常量: UPPER_SNAKE_CASE
- 私有成员: _leading_underscore

### 文档字符串

所有公共类和方法必须有文档字符串：

```python
def process_data(data: list, threshold: float = 0.5) -> dict:
    """
    处理数据并返回结果

    Args:
        data: 输入数据列表
        threshold: 处理阈值

    Returns:
        处理结果字典

    Raises:
        ValueError: 当数据为空时
    """
```

### 类型注解

所有函数签名应包含类型注解：

```python
def example(x: int, y: str) -> bool:
    ...
```

### 日志使用

使用 `get_logger` 获取模块日志记录器：

```python
from src.logger import get_logger

logger = get_logger("module_name")
logger.info("message")
logger.error("error: %s", exception)
```

## 模块开发指南

### 创建新模块

1. 在 `src/` 下创建模块文件
2. 继承 `BaseComponent`
3. 实现 `_do_initialize()` 和 `_do_shutdown()`
4. 通过 `EventBus` 发送/接收事件
5. 添加对应的测试文件到 `tests/`

### 事件类型

| 类型 | 事件名 | 数据 |
|------|--------|------|
| system | startup | {} |
| system | shutdown | {} |
| system | error | {"message": str} |
| model | downloading | {"name": str, "progress": float} |
| model | installed | {"name": str} |
| node | installed | {"name": str} |
| node | updated | {"name": str} |
| workflow | saved | {"name": str} |
| workflow | loaded | {"name": str} |
| update | checking | {} |
| update | available | {"version": str} |
| gpu | detected | {"info": dict} |

## 测试指南

### 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行单个测试文件
pytest tests/test_config_manager.py -v

# 带覆盖率
pytest tests/ --cov=src --cov-report=html
```

### 编写测试

- 每个模块应有对应的测试文件
- 测试文件命名: `test_<module_name>.py`
- 使用 `setup_method` 创建干净的测试环境
- 测试隔离，不依赖外部资源

## 发布流程

1. 更新 `CHANGELOG.md`
2. 更新版本号 `src/__version__.py`
3. 运行所有测试
4. 提交并打标签
5. GitHub Actions 自动发布

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交变更
4. 推送到分支
5. 创建 Pull Request
