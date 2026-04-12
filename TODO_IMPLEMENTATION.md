# 待实现/替换代码清单

> 本文件记录 v0.1 版本中需要留空或替换的代码模块，方便后续版本迭代时进行填充。

## 模块清单
<!-- 
### 1. 本地模型推理 → 外部API调用

**文件位置**: `backend/app/services/inference.py`

**当前实现**: 留空/占位，直接调用配置的大模型API

**后续实现**: 支持本地加载QLoRA微调后的模型进行推理

**替换说明**:
```python
# v0.1 - 调用外部API
async def generate_style_transfer(text: str, style_id: str) -> str:
    # 调用配置的OpenAI格式API
    # TODO: 后续支持本地模型推理
    pass

# v0.2+ - 支持本地模型
async def generate_style_transfer(text: str, style_id: str) -> str:
    # 检查是否有本地训练好的Adapter
    # 如果有则加载本地模型+Adapter
    # 否则回退到外部API
    pass
``` -->

---

### 2. QLoRA训练逻辑

**文件位置**: `backend/app/services/training.py`

**当前实现**: 占位逻辑，仅生成示例模型文件

**后续实现**: 完整的QLoRA微调流程

**替换说明**:
<!-- ```python
# v0.1 - 占位实现
def train_style_model(task_id: str, config: dict):
    # 模拟训练进度
    # 生成示例adapter文件
    # TODO: 实现真实QLoRA训练
    pass

# v0.2+ - 真实训练
def train_style_model(task_id: str, config: dict):
    # 1. 加载基础模型
    # 2. 配置LoRA参数
    # 3. 文本数据预处理
    # 4. QLoRA训练循环
    # 5. 保存Adapter权重
    pass
``` -->

---

<!-- ### 3. 评估指标计算

**文件位置**: `backend/app/services/evaluation.py`

**当前实现**: 返回占位HTML界面

**后续实现**: BLEU分数、风格分类准确率等自动评估

**替换说明**:
```python
# v0.1 - 占位HTML
def generate_evaluation_report(task_id: str) -> str:
    # 返回简单HTML占位
    # TODO: 实现自动评估指标
    pass

# v0.2+ - 完整评估
def generate_evaluation_report(task_id: str) -> str:
    # 1. 加载生成文本和参考文本
    # 2. 计算BLEU分数
    # 3. 计算风格分类准确率
    # 4. 生成可视化报告
    pass
``` -->

---

<!-- ### 4. 评估文本生成 → 本地模型推理

**文件位置**: `backend/app/services/evaluation.py` - `generate_transferred_texts()`

**当前实现**: 调用外部LLM API生成风格转换后的文本用于评估

**后续实现**: 使用本地QLoRA微调后的模型进行推理

**替换说明**:
```python
# v0.1 - 调用外部API生成评估样本
def generate_transferred_texts(
    inference_service,
    source_texts: List[str],
    target_style: str
) -> Tuple[List[str], List[float]]:
    # 遍历source_texts，调用inference_service.generate_style_transfer()
    # 该服务目前调用外部LLM API
    # TODO: 后续替换为本地模型推理
    pass

# v0.2+ - 本地模型推理
def generate_transferred_texts(
    model_path: str,
    source_texts: List[str],
    target_style: str
) -> Tuple[List[str], List[float]]:
    # 1. 从task.result_path加载本地Adapter
    # 2. 加载基础模型
    # 3. 应用LoRA配置
    # 4. 批量推理生成转换文本
    # 5. 返回结果和推理时间
    pass
``` -->

---

### 5. 文本预处理

**文件位置**: `backend/app/services/preprocessing.py`

**当前实现**: 仅实现基础文本分块

**后续实现**: 完整的文本清洗和格式化

**已实现**:
- 文本分块（512 tokens，128重叠）

**待实现**:
- 文档格式解析（docx/pdf）
- 文本清洗（去除特殊字符、标准化）
- Tokenization对齐

---

## 技术债务跟踪

| 优先级 | 模块 | 预计工作量 | 阻塞因素 |
|--------|------|-----------|---------|
| P0 | QLoRA训练 | 2周 | 需要GPU环境 |
| P1 | 本地推理 | 3天 | 依赖训练模块完成 |
| P1 | 评估指标 | 1周 | 需要确定评估标准 |
| P1 | 评估文本生成 | 2天 | 依赖本地推理模块完成 |
| P2 | 文档解析 | 2天 | 无 |

## 配置扩展点

以下配置项为后续版本预留：

```python
# config.py 预留配置
LOCAL_MODEL_PATH = ""  # 本地模型路径
ENABLE_LOCAL_INFERENCE = False  # 是否启用本地推理
GPU_DEVICE = "cuda:0"  # GPU设备
LORA_RANK = 8  # LoRA秩
LORA_ALPHA = 32  # LoRA alpha
```
