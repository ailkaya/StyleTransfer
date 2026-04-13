"""Text preprocessing service for training data preparation."""

import re
import json
import random
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple, Optional

from ..utils import get_logger

logger = get_logger(__name__)

class PreprocessingService:
    """Service for preprocessing training text data."""

    # Approximate tokens per character (rough estimate for CJK + English)
    CHARS_PER_TOKEN = 2.0

    def __init__(self):
        self.default_chunk_size = 512
        self.default_overlap = 128

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        return int(len(text) / self.CHARS_PER_TOKEN)

    def chunk_text(
        self,
        text: str,
        chunk_size: int = None,
        overlap: int = None,
    ) -> List[str]:
        """
        Split text into overlapping chunks.

        Args:
            text: Input text to chunk
            chunk_size: Target chunk size in tokens (default: 512)
            overlap: Overlap between chunks in tokens (default: 128)

        Returns:
            List of text chunks
        """
        chunk_size = chunk_size or self.default_chunk_size
        overlap = overlap or self.default_overlap

        # Convert token counts to character counts
        chunk_chars = int(chunk_size * self.CHARS_PER_TOKEN)
        overlap_chars = int(overlap * self.CHARS_PER_TOKEN)

        chunks = []
        start = 0
        text_len = len(text)

        while start < text_len:
            # Calculate end position
            end = min(start + chunk_chars, text_len)

            # Try to break at a sentence boundary
            if end < text_len:
                # Look for sentence endings (. ! ?)
                search_end = min(end + 50, text_len)
                search_text = text[end:search_end]
                sentence_end = re.search(r'[.!?。！？]+\s*', search_text)
                if sentence_end:
                    end += sentence_end.end()

            # Extract chunk
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # Move to next chunk with overlap
            start = end - overlap_chars if end < text_len else text_len

        return chunks

    def clean_text(self, text: str) -> str:
        """
        Basic text cleaning.

        TODO v0.2+: Add more sophisticated cleaning
        - Remove special characters
        - Normalize whitespace
        - Fix encoding issues
        """
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove control characters
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        return text.strip()

    def preprocess_training_text(
        self,
        text: str,
        chunk_size: int = None,
        overlap: int = None,
    ) -> dict:
        """
        Full preprocessing pipeline for training text.

        Args:
            text: Raw input text
            chunk_size: Target chunk size in tokens
            overlap: Overlap between chunks in tokens

        Returns:
            Dictionary with:
                - cleaned_text: Cleaned full text
                - chunks: List of text chunks
                - chunk_count: Number of chunks
                - estimated_tokens: Estimated total tokens
        """
        # Clean text
        cleaned = self.clean_text(text)

        # Chunk text
        chunks = self.chunk_text(cleaned, chunk_size, overlap)

        return {
            "cleaned_text": cleaned,
            "chunks": chunks,
            "chunk_count": len(chunks),
            "estimated_tokens": self.estimate_tokens(cleaned),
        }

    def format_for_training(self, chunks: List[str], target_style: str) -> List[dict]:
        """
        Format chunks for training.

        TODO v0.2+: Format as instruction-following dataset for QLoRA
        """
        formatted = []
        for chunk in chunks:
            formatted.append({
                "text": chunk,
                "target_style": target_style,
                # v0.2+: Add instruction templates
            })
        return formatted


# ==================== Data Preprocessor (New Implementation) ====================

@dataclass
class TextChunk:
    """文本分块数据结构"""
    content: str
    start_pos: int
    end_pos: int
    chunk_type: str  # 'narration', 'dialogue', 'description'
    source: str


class DataPreprocessor:
    """
    数据预处理器 - 基于 docs/preprocess.md 设计

    支持功能：
    1. 纯中文/纯英文/中英文混合输入处理
    2. 语义边界分块策略（方案C）
    3. 训练样本构造（类型1续写任务、类型2风格模仿任务）
    4. 自定义JSONL格式输出
    """

    def __init__(self, style_config: Optional[dict] = None):
        """
        初始化数据预处理器

        Args:
            style_config: 风格配置字典
                - target_style: 目标风格标签，如 "<鲁迅风格>"
                - system_prompt: 系统提示词
                - style_name: 风格名称（用于生成system_prompt）
                - style_description: 风格描述（用于生成system_prompt）
        """
        self.style_config = style_config or {}
        self.style_tag = self.style_config.get('target_style', '<自定义风格>')
        self.system_prompt = self._generate_system_prompt()
        self.chunks: List[TextChunk] = []

    def _generate_system_prompt(self) -> str:
        """根据风格配置生成系统提示词"""
        if 'system_prompt' in self.style_config:
            return self.style_config['system_prompt']

        style_name = self.style_config.get('style_name', '自定义')
        style_desc = self.style_config.get('style_description', '')

        if style_desc:
            return f"你是{style_name}风格的文章生成助手。{style_desc}"
        return f"你是{style_name}风格的文章生成助手，擅长模仿该风格的写作特点。"

    def _detect_language(self, text: str) -> str:
        """
        检测文本语言类型

        Returns:
            'chinese': 纯中文
            'english': 纯英文
            'mixed': 中英文混合
        """
        chinese_chars = len(re.findall(r'[\u4e00-\u9fa5]', text))
        english_chars = len(re.findall(r'[a-zA-Z]', text))
        total_chars = len(text.strip())

        if total_chars == 0:
            return 'mixed'

        chinese_ratio = chinese_chars / total_chars
        english_ratio = english_chars / total_chars

        if chinese_ratio > 0.8:
            return 'chinese'
        elif english_ratio > 0.8:
            return 'english'
        else:
            return 'mixed'

    def clean_text(self, raw_text: str) -> str:
        """
        清洗原始文本 - 支持中文/英文/混合

        处理步骤：
        1. 去除多余空白
        2. 标准化标点（英文标点→中文标点，适用于中文/混合文本）
        3. 去除特殊字符和控制字符
        4. 段落边界规范化
        5. 去除页眉页脚模式（如页码、章节标记）
        """
        text = raw_text
        lang = self._detect_language(text)

        # 1. 规范化换行符
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        # 2. 去除控制字符（保留换行）
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

        # 3. 根据语言类型处理标点
        if lang in ('chinese', 'mixed'):
            # 英文标点转为中文标点
            punct_map = {
                ',': '，', '.': '。', '?': '？', '!': '！',
                ':': '：', ';': '；', '"': '"', '"': '"',
                "'": ''', "'": ''', '(': '（', ')': '）',
                '[': '【', ']': '】', '{': '｛', '}': '｝'
            }
            for en_punct, cn_punct in punct_map.items():
                text = text.replace(en_punct, cn_punct)

        # 4. 去除页眉页脚模式（如 "第X页"、"Page X of Y"）
        text = re.sub(r'第\s*\d+\s*[页頁]', '', text)
        text = re.sub(r'Page\s+\d+\s*(of|/|)\s*\d*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'-\s*\d+\s*-', '', text)

        # 5. 规范化空白字符
        # 保留段落间的换行，但去除行内多余空白
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            # 去除行首行尾空白
            line = line.strip()
            # 将行内多个空白合并为一个
            line = re.sub(r'\s+', ' ', line)
            if line:  # 只保留非空行
                cleaned_lines.append(line)

        # 段落间保留单个换行
        text = '\n'.join(cleaned_lines)

        return text.strip()

    def _find_semantic_boundaries(self, text: str) -> List[int]:
        """
        识别文本中的语义边界位置

        优先级：段落边界 > 对话结束 > 章节标题 > 句子结束
        """
        boundaries = []

        # 1. 段落边界（两个换行）
        for match in re.finditer(r'\n\s*\n', text):
            boundaries.append(match.end())

        # 2. 对话结束（引号后）- 支持中文和英文引号
        dialogue_patterns = [
            r'[」』""''」』].{0,5}[\n。！？]',
            r'["\'"\'].{0,10}[\n.!?]'
        ]
        for pattern in dialogue_patterns:
            for match in re.finditer(pattern, text):
                boundaries.append(match.end())

        # 3. 章节标题（如：第一章、一、等）
        chapter_patterns = [
            r'[第卷][一二三四五六七八九十百千\d]+[章节回篇]',
            r'^[一二三四五六七八九十]+[、.．]',
            r'^Chapter\s+\d+',
            r'^\d+\s*[.．]'
        ]
        for pattern in chapter_patterns:
            for match in re.finditer(pattern, text, re.MULTILINE):
                boundaries.append(match.start())

        # 4. 句子结束（。！？.!?）- 优先级最低
        for match in re.finditer(r'[。！？.!?]+\s*', text):
            boundaries.append(match.end())

        return sorted(set(boundaries))

    def _find_optimal_split(self, text: str, start: int, target: int,
                           boundaries: List[int]) -> int:
        """
        在目标长度附近寻找最佳语义边界

        Args:
            text: 完整文本
            start: 当前起始位置
            target: 目标块长度
            boundaries: 语义边界位置列表

        Returns:
            最佳切分位置
        """
        ideal_end = start + target
        max_end = min(start + int(target * 1.5), len(text))
        min_end = start + int(target * 0.5)  # 至少达到目标长度的一半

        # 在理想位置±20%范围内寻找边界
        candidates = [b for b in boundaries if min_end <= b <= max_end]

        if candidates:
            # 选择最接近理想长度的边界
            return min(candidates, key=lambda x: abs(x - ideal_end))
        else:
            # 回退：在目标位置寻找最近的句子结束
            fallback_search_start = min(ideal_end, len(text) - 1)
            fallback = text.find('。', fallback_search_start)
            if fallback != -1 and fallback < max_end:
                return fallback + 1

            # 最终回退：按目标长度硬切分
            return min(ideal_end, len(text))

    def _classify_chunk(self, content: str) -> str:
        """
        分类文本块类型（用于后续多样化训练任务）

        Returns:
            'dialogue': 对话为主
            'description': 描写为主
            'narration': 叙述为主
        """
        # 对话标记
        dialogue_marks = ['「', '『', '"', '"', ''', ''', '"', "'"]
        dialogue_count = sum(content.count(m) for m in dialogue_marks)

        # 描写关键词（中文和英文）
        desc_keywords = ['描写', '景象', '看见', '只见', 'scene', 'describe',
                        'looked', 'saw', 'appearance', 'landscape']
        desc_count = sum(content.count(w) for w in desc_keywords)

        if dialogue_count >= 4:
            return 'dialogue'
        elif desc_count >= 2:
            return 'description'
        else:
            return 'narration'

    def semantic_chunking(self, text: str, target_length: int = 1024,
                         overlap: int = 256) -> List[TextChunk]:
        """
        语义边界分块策略（方案C）

        优先在以下位置切分：段落结束 > 对话结束 > 章节标题 > 句子结束
        目标块大小：512-2048字符（默认1024）

        Args:
            text: 清洗后的文本
            target_length: 目标块长度（字符数）
            overlap: 重叠窗口大小（保持上下文连贯性）

        Returns:
            TextChunk对象列表
        """
        # 识别语义边界
        boundaries = self._find_semantic_boundaries(text)

        chunks = []
        start = 0
        chunk_id = 0
        text_len = len(text)

        while start < text_len:
            # 寻找最佳切分点
            end = self._find_optimal_split(text, start, target_length, boundaries)

            content = text[start:end].strip()
            if len(content) > 50:  # 过滤过短片段
                chunk_type = self._classify_chunk(content)
                chunks.append(TextChunk(
                    content=content,
                    start_pos=start,
                    end_pos=end,
                    chunk_type=chunk_type,
                    source=f"chunk_{chunk_id}"
                ))
                chunk_id += 1

            # 移动到下一个位置（带重叠）
            start = end - overlap if end < text_len else text_len

        self.chunks = chunks
        return chunks

    def _create_continuation_task(self, current: TextChunk, next_chunk: TextChunk) -> Dict:
        """
        构造续写任务（类型1）

        取当前块的前半部分作为提示，后半部分+下一块作为答案
        """
        split_point = len(current.content) // 2
        prompt_text = current.content[:split_point].strip()
        completion = current.content[split_point:].strip()

        # 添加下一块的开头部分（最多500字符）
        next_part = next_chunk.content[:500].strip()
        if next_part:
            completion += " " + next_part

        return {
            "system": self.system_prompt,
            "instruction": f"{self.style_tag} 请续写：{prompt_text}",
            "input": "",
            "output": completion,
            "task_type": "continuation",
            "metadata": {
                "chunk_id": current.source,
                "prompt_length": len(prompt_text),
                "output_length": len(completion)
            }
        }

    def _create_style_imitation_task(self, chunk: TextChunk) -> Dict:
        """
        构造风格模仿任务（类型2）

        提取核心内容要求用目标风格重写
        """
        # 取前200字符作为场景描述提示
        input_text = chunk.content[:200].strip()
        if len(chunk.content) > 200:
            input_text += "..."

        return {
            "system": self.system_prompt,
            "instruction": f"{self.style_tag} 请用指定风格描写以下场景：",
            "input": input_text,
            "output": chunk.content,
            "task_type": "style_imitation",
            "metadata": {
                "chunk_id": chunk.source,
                "chunk_type": chunk.chunk_type,
                "content_length": len(chunk.content)
            }
        }

    def generate_training_samples(self, chunks: List[TextChunk]) -> List[Dict]:
        """
        为每个分块生成训练样本

        生成类型：
        - 类型1：续写任务（如果有下文）
        - 类型2：风格模仿任务
        忽略类型3：问答任务（根据需求）
        """
        samples = []

        for i, chunk in enumerate(chunks):
            # 类型1：续写任务（如果有下一个块）
            if i < len(chunks) - 1:
                sample = self._create_continuation_task(chunk, chunks[i + 1])
                samples.append(sample)

            # 类型2：风格模仿任务
            sample = self._create_style_imitation_task(chunk)
            samples.append(sample)

            # 注意：根据需求，类型3（问答任务）被忽略

        return samples

    def to_custom_jsonl(self, samples: List[Dict]) -> List[Dict]:
        """
        转换为自定义JSONL格式

        输出格式：
        {
            "system": "系统提示词",
            "conversations": [
                {"from": "human", "value": "用户指令\n输入内容"},
                {"from": "gpt", "value": "输出内容"}
            ],
            "task_type": "continuation|style_imitation",
            "metadata": {...}
        }
        """
        jsonl_data = []

        for i, sample in enumerate(samples):
            # 构造对话内容
            human_value = sample["instruction"]
            if sample["input"]:
                human_value += f"\n{sample['input']}"

            conversation = {
                "id": f"sample_{i:06d}",
                "system": sample["system"],
                "conversations": [
                    {"from": "human", "value": human_value},
                    {"from": "gpt", "value": sample["output"]}
                ],
                "task_type": sample.get("task_type", "general"),
                "metadata": sample.get("metadata", {})
            }
            jsonl_data.append(conversation)

        return jsonl_data

    def validate_and_split(self, data: List[Dict],
                          train_ratio: float = 0.95) -> Tuple[List[Dict], List[Dict], Dict]:
        """
        验证数据质量并划分训练/验证集

        Returns:
            (train_data, val_data, metadata)
        """
        # 过滤异常样本
        valid_data = []
        for item in data:
            try:
                output = item["conversations"][1]["value"]  # gpt response
                output_len = len(output)

                # 过滤过长或过短
                if 50 < output_len < 3000:
                    valid_data.append(item)
            except (KeyError, IndexError):
                continue

        # 统计信息
        lengths = [len(d["conversations"][1]["value"]) for d in valid_data]
        short_count = sum(1 for l in lengths if l < 500)
        medium_count = sum(1 for l in lengths if 500 <= l < 1500)
        long_count = sum(1 for l in lengths if l >= 1500)

        metadata = {
            "total_samples": len(data),
            "valid_samples": len(valid_data),
            "avg_length": sum(lengths) / len(lengths) if lengths else 0,
            "length_distribution": {
                "short(<500)": short_count,
                "medium(500-1500)": medium_count,
                "long(>1500)": long_count
            },
            "train_ratio": train_ratio,
            "val_ratio": 1 - train_ratio
        }

        # 随机划分
        random.shuffle(valid_data)
        split_idx = int(len(valid_data) * train_ratio)

        return valid_data[:split_idx], valid_data[split_idx:], metadata

    def process(self, raw_text: str, target_length: int = 1024,
                overlap: int = 256, train_ratio: float = 0.95) -> Dict:
        """
        完整预处理流程

        Pipeline: 清洗 → 语义分块 → 生成样本 → 格式转换 → 验证划分

        Args:
            raw_text: 原始输入文本
            target_length: 目标分块长度
            overlap: 重叠窗口大小
            train_ratio: 训练集比例

        Returns:
            包含train_data, val_data, metadata的字典
        """
        # Step 1: 清洗文本
        clean_text = self.clean_text(raw_text)

        # Step 2: 语义分块
        chunks = self.semantic_chunking(clean_text, target_length, overlap)

        # Step 3: 生成训练样本
        samples = self.generate_training_samples(chunks)

        # Step 4: 转换为自定义JSONL格式
        formatted_data = self.to_custom_jsonl(samples)

        # Step 5: 验证和划分
        train_data, val_data, metadata = self.validate_and_split(formatted_data, train_ratio)

        # 更新元数据
        metadata.update({
            "language": self._detect_language(raw_text),
            "original_length": len(raw_text),
            "cleaned_length": len(clean_text),
            "chunk_count": len(chunks),
            "sample_count": len(samples),
            "style_tag": self.style_tag,
            "system_prompt": self.system_prompt
        })

        return {
            "train_data": train_data,
            "val_data": val_data,
            "metadata": metadata,
            "chunks": [asdict(c) for c in chunks],
            "samples": samples
        }

    async def adjust_samples_by_comment(
        self,
        samples: List[Dict],
        comment: str,
        inference_service=None
    ) -> List[Dict]:
        """
        根据用户评论调整训练样本。

        Args:
            samples: 生成的训练样本列表
            comment: 用户评价/反馈
            inference_service: 推理服务实例（用于调用LLM）

        Returns:
            调整后的样本列表
        """
        if not comment or not inference_service:
            return samples

        # 1. 验证 comment 语义有效性
        is_valid = await self._validate_comment_semantic(comment, inference_service)
        if not is_valid:
            logger.info(f"Comment '{comment[:50]}...' is not semantically valid, skipping adjustment")
            return samples

        logger.info(f"Adjusting {len(samples)} samples based on comment: {comment[:50]}...")

        # 2. 对每个样本进行调整
        adjusted_samples = []
        for sample in samples:
            adjusted = await self._apply_comment_adjustment(sample, comment, inference_service)
            if adjusted:
                adjusted_samples.append(adjusted)
            else:
                adjusted_samples.append(sample)

        return adjusted_samples

    async def _validate_comment_semantic(
        self,
        comment: str,
        inference_service
    ) -> bool:
        """使用 LLM 验证评论是否有有效语义。"""
        prompt = f"""请判断以下用户反馈是否包含可用于改进训练数据的具体、有效语义。

用户反馈："{comment}"

有效反馈示例：
- "风格可以更幽默一些"
- "减少重复用词"
- "增加文学性描写"
- "语气应该更正式"

无效反馈示例：
- "很好"
- "不错"
- "无"
- "还可以"

请只回答 "VALID" 或 "INVALID"。"""

        try:
            response = await inference_service.call_llm_for_validation(prompt)
            is_valid = "VALID" in response.upper()
            logger.info(f"Comment validation result: {is_valid} (response: {response})")
            return is_valid
        except Exception as e:
            logger.error(f"Failed to validate comment: {e}")
            return False

    async def _apply_comment_adjustment(
        self,
        sample: Dict,
        comment: str,
        inference_service
    ) -> Optional[Dict]:
        """使用 LLM 根据评论调整单个样本。"""
        # 从对话格式中提取信息
        conversations = sample.get('conversations', [])
        system = sample.get('system', '')
        instruction = ''
        input_text = ''
        output = ''

        if conversations and len(conversations) >= 2:
            human_msg = conversations[0].get('value', '')
            parts = human_msg.split('\n', 1)
            instruction = parts[0]
            input_text = parts[1] if len(parts) > 1 else ''
            output = conversations[1].get('value', '')

        prompt = f"""请根据用户的改进要求，调整以下训练样本。

用户改进要求："{comment}"

原始样本：
系统提示：{system}
用户指令：{instruction}
输入：{input_text}
期望输出：{output}

请输出调整后的 JSON 格式：
{{
  "system": "调整后的系统提示（如有必要）",
  "instruction": "调整后的用户指令",
  "input": "调整后的输入",
  "output": "调整后的期望输出"
}}

只输出 JSON，不要其他解释。"""

        try:
            response = await inference_service.call_llm_for_adjustment(prompt)
            # 解析 JSON 响应
            import json
            adjusted_raw = json.loads(response)

            # 转换回对话格式
            adjusted = {
                'id': sample.get('id', ''),
                'system': adjusted_raw.get('system', system),
                'conversations': [
                    {'from': 'human', 'value': adjusted_raw.get('instruction', instruction) +
                     ('\n' + adjusted_raw.get('input', input_text) if adjusted_raw.get('input', input_text) else '')},
                    {'from': 'gpt', 'value': adjusted_raw.get('output', output)}
                ],
                'task_type': sample.get('task_type', 'general'),
                'metadata': sample.get('metadata', {})
            }
            adjusted['metadata']['adjusted_by_comment'] = True
            return adjusted
        except Exception as e:
            logger.error(f"Failed to adjust sample: {e}")
            return None

    def save_to_jsonl(self, data: List[Dict], filepath: str):
        """保存数据为JSONL格式"""
        with open(filepath, 'w', encoding='utf-8') as f:
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')


# Global preprocessing service instance
preprocessing_service = PreprocessingService()
