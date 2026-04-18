"""Text preprocessing service for training data preparation."""

import os
import re
import json
import hashlib
import random
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple, Optional

from ..utils import get_logger

logger = get_logger(__name__)


@dataclass
class TextChunk:
    """文本分块数据结构"""
    content: str
    start_pos: int
    end_pos: int
    source: str

TASK_GENERATE = "generate"
TASK_TRANSFER = "style_transfer"
TASK_TRANSFER_REVERSE = "style_transfer_reverse"
TASK_CONTINUATION = "continuation"

class DataPreprocessor:
    """
    数据预处理器 - 基于 docs/preprocess-improve.md 设计

    支持功能：
    1. 纯中文/纯英文/中英文混合输入处理
    2. 语义边界分块策略（用于续写任务）
    3. 句子级拆分（用于风格转换任务）
    4. 基于LLM的去风格、语义校验、风格残留检测
    5. 训练样本构造（续写任务 + 风格转换任务）
    6. 自定义JSONL格式输出
    """

    def __init__(self, style_config: Optional[dict] = None, cache_dir: str = "./cache/preprocess"):
        logger.info(f"[DataPreprocessor] style config: {style_config}")
        self.style_config = style_config or {}
        self.style_tag = self.style_config.get('target_style', '自定义风格')
        self.system_prompt = self._generate_system_prompt()
        self.chunks: List[TextChunk] = []
        self.cache_dir = cache_dir

    def _generate_system_prompt(self) -> str:
        """根据风格配置生成系统提示词"""
        if 'system_prompt' in self.style_config:
            return self.style_config['system_prompt']
        return f"你是<{self.style_tag}>的文章生成助手，擅长模仿该风格的写作特点。"

    def _get_cache_key(self, raw_text: str) -> str:
        """基于 raw_text 和 style_tag 计算缓存 key"""
        content = f"{self.style_tag}:{raw_text}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def _get_cache_path(self, raw_text: str) -> str:
        key = self._get_cache_key(raw_text)
        return os.path.join(self.cache_dir, "process", key)

    def _load_from_cache(self, raw_text: str) -> Optional[Dict]:
        cache_path = self._get_cache_path(raw_text)
        files = {
            "train_data": "train.jsonl",
            "val_data": "val.jsonl",
            "metadata": "metadata.json",
            "chunks": "chunks.json",
            "samples": "samples.json",
        }
        result = {}
        for field, filename in files.items():
            filepath = os.path.join(cache_path, filename)
            if not os.path.exists(filepath):
                return None
            with open(filepath, "r", encoding="utf-8") as f:
                if filename.endswith(".jsonl"):
                    result[field] = [json.loads(line) for line in f if line.strip()]
                else:
                    result[field] = json.load(f)
        # 读取 cleaned_text
        cleaned_text_path = os.path.join(cache_path, "cleaned_text.txt")
        if os.path.exists(cleaned_text_path):
            with open(cleaned_text_path, "r", encoding="utf-8") as f:
                result["cleaned_text"] = f.read()
        logger.info(f"Loaded preprocessing result from cache: {cache_path}")
        return result

    def _save_to_cache(self, raw_text: str, result: Dict):
        cache_path = self._get_cache_path(raw_text)
        os.makedirs(cache_path, exist_ok=True)
        files = {
            "train_data": "train.jsonl",
            "val_data": "val.jsonl",
            "metadata": "metadata.json",
            "chunks": "chunks.json",
            "samples": "samples.json",
        }
        for field, filename in files.items():
            filepath = os.path.join(cache_path, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                if filename.endswith(".jsonl"):
                    for item in result[field]:
                        f.write(json.dumps(item, ensure_ascii=False) + "\n")
                else:
                    json.dump(result[field], f, ensure_ascii=False, indent=2)
        # 写入 cleaned_text
        cleaned_text = result.get("cleaned_text")
        if cleaned_text is not None:
            with open(os.path.join(cache_path, "cleaned_text.txt"), "w", encoding="utf-8") as f:
                f.write(cleaned_text)
        logger.info(f"Saved preprocessing result to cache: {cache_path}")

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

    def _get_clean_cache_path(self, raw_text: str) -> str:
        key = self._get_cache_key(raw_text)
        return os.path.join(self.cache_dir, "clean", key, "cleaned_chunks.json")

    def _load_clean_from_cache(self, raw_text: str) -> Optional[str]:
        path = self._get_clean_cache_path(raw_text)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info(f"Loaded cleaned text from cache: {path}")
            return data.get("cleaned_text")
        return None

    def _save_clean_to_cache(self, raw_text: str, cleaned_text: str):
        path = self._get_clean_cache_path(raw_text)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"cleaned_text": cleaned_text}, f, ensure_ascii=False)
        logger.info(f"Saved cleaned text to cache: {path}")

    async def clean_text(
        self, raw_text: str, inference_service,
        prev_text: str = ""
    ) -> str:
        """
        使用大模型 API 逐段清洗文本。
        输入前一个 trunk（仅作上下文参考）和当前 trunk，仅输出当前 trunk 的清洗结果。
        """
        text = raw_text
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        lang = self._detect_language(text)
        if lang in ('chinese', 'mixed'):
            punct_map = {
                ',': '，', '.': '。', '?': '？', '!': '！',
                ':': '：', ';': '；', '"': '"', '"': '"',
                "'": ''', "'": ''', '(': '（', ')': '）',
                '[': '【', ']': '】', '{': '｛', '}': '｝'
            }
            for en_punct, cn_punct in punct_map.items():
                text = text.replace(en_punct, cn_punct)
        text = re.sub(r'第\s*\d+\s*[页頁]', '', text)
        text = re.sub(r'Page\s+\d+\s*(of|/|)\s*\d*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'-\s*\d+\s*-', '', text)
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            line = re.sub(r'\s+', ' ', line)
            if line:
                cleaned_lines.append(line)
        text = '\n'.join(cleaned_lines)
        text = text.strip()

        prompt = f"""请对【当前片段】进行文本清洗。前一个片段仅作上下文参考，不影响输出范围。

要求：
1. 规范化换行符，将 \\r\\n 转为 \\n，去除所有控制字符（保留换行）
2. 删除以下非正文内容：
   a) 文末注释块：从"〔x〕"开始到片段结束的所有注释说明文字
   b) 编辑前言：如"某君昆仲...七年四月二日识。"这类小说引言
   c) 出版信息：版本说明、页眉页脚、发表信息
   d) 行内注释标记：删除所有"〔数字〕"格式的标记，但保留标记前后的正文文字
   e) 文章标题，副标题，章节名等
3. 清理行首全角空格（　），段落间保留单个换行
4. 保留原文所有内容和语义，禁止改写、总结、扩写
5. 仅输出【当前片段】的清洗结果，零额外说明

========== 前一个片段（仅参考，不要输出） ==========
{prev_text}

========== 当前片段（请清洗并仅输出此部分） ==========
{text}
"""
        
        try:
            text = await inference_service.call_llm_raw(
                prompt=prompt,
                system_prompt="你是一个文本清洗助手，请按要求输出文本的清洗结果，不要输出其他内容，不要解释。",
                temperature=0.6,
                max_tokens=8192
            )
            text = text.strip()
            # print("call API success")
        except Exception as e:
            # print("call API failed")
            logger.error(f"LLM clean_text failed: {e}, fallback to heuristic cleaning")

        return text

    async def _clean_chunks(
        self,
        raw_chunks: List[TextChunk],
        raw_text: str,
        inference_service,
        target_length: int,
        handle_text_length: int = 2048,
    ) -> Tuple[List[TextChunk], str]:
        """逐段清洗 raw_chunks，整体缓存，合并过短片段后重新分块。返回 (chunks, cleaned_text)。"""
        cached_text = self._load_clean_from_cache(raw_text)
        if cached_text is not None:
            # print("[Clean] use cache")
            chunks = self.semantic_chunking(cached_text, target_length, overlap=0)
            logger.info(f"[Preprocessing] Step 2 completed: {len(chunks)} chunks loaded from clean cache")
            return chunks, cached_text

        # 无缓存：拼接短 chunk 成组，每组总长度 >= handle_text_length
        # print("[Clean] no cache")
        groups = []
        current_group = []
        current_len = 0
        for chunk in raw_chunks:
            current_group.append(chunk)
            current_len += len(chunk.content)
            if current_len >= handle_text_length:
                groups.append(current_group)
                current_group = []
                current_len = 0
        if current_group:
            groups.append(current_group)

        # 逐组调用 clean_text
        cleaned_parts = []
        prev_text = ""
        for group in groups:
            combined = "\n".join(c.content for c in group)
            cleaned = await self.clean_text(combined, inference_service, prev_text=prev_text)
            cleaned_parts.append(cleaned)
            prev_text = combined

        cleaned_text = "\n".join(cleaned_parts)

        # 重新按 target_length 语义分块
        chunks = self.semantic_chunking(cleaned_text, target_length, overlap=0)

        self._save_clean_to_cache(raw_text, cleaned_text)
        return chunks, cleaned_text

    def sentence_split(self, text: str) -> List[str]:
        """
        句子级文本拆分：按句子结束符切分，合并过短片段，保持长句子完整性
        """
        # 按句子结束符切分并保留标点
        raw_parts = re.split(r'([。！？.!?]+)', text)
        sentences = []
        for i in range(0, len(raw_parts) - 1, 2):
            sent = raw_parts[i] + raw_parts[i + 1]
            sent = sent.strip()
            if sent:
                sentences.append(sent)
        if len(raw_parts) % 2 == 1:
            last = raw_parts[-1].strip()
            if last:
                sentences.append(last)

        # 合并过短片段 (<15字)
        sentences_min_length = 15
        merged = []
        for s in sentences:
            if not merged:
                merged.append(s)
            else:
                if len(merged[-1]) < sentences_min_length:
                    merged[-1] += s
                elif len(s) < sentences_min_length:
                    merged[-1] += s
                else:
                    merged.append(s)

        # 返回合并后的结果，不再对长句子进行内部切分
        return merged

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

    def semantic_chunking(self, text: str, target_length: int = 512,
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
                chunks.append(TextChunk(
                    content=content,
                    start_pos=start,
                    end_pos=end,
                    source=f"chunk_{chunk_id}"
                ))
                chunk_id += 1

            # 移动到下一个位置（带重叠）
            start = end - overlap if end < text_len else text_len

        self.chunks = chunks
        return chunks

    def generate_continuation_samples(self, chunks: List[TextChunk]) -> List[Dict]:
        """
        生成续写任务样本
        """
        samples = []
        for i, chunk in enumerate(chunks):
            if i < len(chunks) - 1:
                prompt = chunk.content.strip()
                completion = chunks[i + 1].content.strip()
                samples.append({
                    # "system": self.system_prompt,
                    "instruction": "请续写以下文本，并保持语言风格、语气、节奏和风格一致",
                    "input": prompt,
                    "output": completion,
                    "task_type": TASK_CONTINUATION,
                })
        return samples

    async def _neutralize_text(self, text: str, inference_service) -> str:
        """LLM 去风格生成"""
        prompt = f"""请将以下文本改写为"中性客观表达"，要求：

- 保留原始语义，不改变事实
- 去除文学性表达（如比喻、讽刺、情绪渲染）
- 使用简单、直接、现代的语言
- 不要扩写或缩写内容
- 不要解释

文本：
{text}

输出："""
        try:
            response = await inference_service.call_llm_raw(
                prompt=prompt,
                system_prompt="你是一个文本改写助手，只输出改写后的文本，不要解释。",
                temperature=0.3,
                max_tokens=2048
            )
            return response.strip()
        except Exception as e:
            logger.error(f"Neutralization failed: {e}")
            return ""

    async def _check_semantic_alignment(self, original: str, neutral: str, inference_service) -> bool:
        """语义一致性校验"""
        prompt = f"""判断以下两句话是否表达相同的含义（忽略风格差异）：

A: {original}
B: {neutral}

如果语义一致，回答：是
否则回答：否"""
        try:
            response = await inference_service.call_llm_raw(
                prompt=prompt,
                system_prompt="你是一个文本分析助手，只回答是或否。",
                temperature=0.1,
                max_tokens=10
            )
            return "是" in response.strip()
        except Exception as e:
            logger.error(f"Semantic alignment check failed: {e}")
            return False

    async def _check_style_leakage(self, neutral_text: str, inference_service) -> bool:
        """风格残留检测"""
        prompt = f"""判断以下文本是否仍然具有文学风格（如鲁迅风格）：

文本：
{neutral_text}

如果是中性表达，回答：中性
如果仍有明显文学风格，回答：有风格"""
        try:
            response = await inference_service.call_llm_raw(
                prompt=prompt,
                system_prompt="你是一个文本风格分析助手，只回答中性或有风格。",
                temperature=0.1,
                max_tokens=10
            )
            return "中性" in response.strip()
        except Exception as e:
            logger.error(f"Style leakage check failed: {e}")
            return False

    def _quality_filter(self, original: str, neutral: str) -> bool:
        """数据质量控制"""
        if not original or not neutral:
            return False

        ratio = len(neutral) / len(original)
        if ratio < 0.7 or ratio > 1.5:
            return False

        # 重复检测：连续重复8次以上
        if re.search(r'(.)\1{7,}', neutral):
            return False

        # 关键词覆盖：原文中2-6字的中文词至少保留30%
        keywords = set(re.findall(r'[\u4e00-\u9fa5]{2,6}', original))
        if keywords:
            preserved = sum(1 for k in keywords if k in neutral)
            if preserved / len(keywords) < 0.3:
                return False

        return True

    async def generate_style_transfer_samples(self, sentences: List[str], inference_service) -> List[Dict]:
        """
        生成风格转换样本（基于LLM的多阶段过滤）
        """
        style_name = self.style_tag.strip('<>') if self.style_tag.startswith('<') and self.style_tag.endswith('>') else self.style_tag
        samples = []

        for original in sentences:
            # 去风格
            neutral = await self._neutralize_text(original, inference_service)
            if not neutral:
                logger.info(f"  -> Neutralization returned empty, skip")
                continue

            # 语义校验
            # aligned = await self._check_semantic_alignment(original, neutral, inference_service)
            # if not aligned:
            #     logger.info(f"  -> Semantic alignment failed, dropping")
            #     continue

            # 风格残留检测
            # no_leak = await self._check_style_leakage(neutral, inference_service)
            # if not no_leak:
            #     logger.info(f"  -> Style leakage detected, dropping")
            #     continue

            # 质量过滤
            # if not self._quality_filter(original, neutral):
            #     logger.info(f"  -> Quality filter failed, dropping")
            #     continue

            # 构造正向样本
            samples.append({
                # "system": self.system_prompt,
                "instruction": f"请将文本改写为{style_name}风格，保持原意，不扩写",
                "input": neutral,
                "output": original,
                "task_type": TASK_TRANSFER,
            })

            # 构造反向样本（30%概率）
            if random.random() < 0.3:
                samples.append({
                    # "system": "你是一个文本风格转换模型。",
                    "instruction": "请将文本改写为中性表达，保持原意，不扩写",
                    "input": original,
                    "output": neutral,
                    "task_type": TASK_TRANSFER_REVERSE,
                })

        logger.info(f"Style transfer sample generation complete: {len(samples)} samples kept")
        return samples

    def to_sft_format(self, samples: List[Dict]) -> List[Dict]:
        data = []
        for s in samples:
            text = f"""<|system|>
{self.system_prompt}

<|style_tag|>
{self.style_tag}

<|task|>
{s["task_type"]}

<|instruction|>
{s["instruction"]}

<|input|>
{s["input"]}

<|response|>
{s["output"]}"""
            data.append({
                "text": text,
                "style_tag": self.style_tag,
                "task_type": s["task_type"],
                "system": self.system_prompt,
                "instruction": s["instruction"],
                "input": s["input"],
                "output": s["output"],
            })
        return data

    def _extract_output_from_item(self, item: Dict) -> Optional[str]:
        """从 formatted_data 中提取 output/response 内容。"""
        return item.get("output") or None

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
            output = self._extract_output_from_item(item)
            if output is None:
                continue
            output_len = len(output)

            # 过滤过长或过短
            if 15 < output_len < 3000:
                valid_data.append(item)

        # 统计信息
        lengths = []
        for d in valid_data:
            output = self._extract_output_from_item(d)
            if output is not None:
                lengths.append(len(output))

        short_count = sum(1 for l in lengths if l < 100)
        medium_count = sum(1 for l in lengths if 100 <= l < 500)
        long_count = sum(1 for l in lengths if l >= 500)

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

    async def process(self, raw_text: str, inference_service, target_length: int = 512,
                      train_ratio: float = 0.95) -> Dict:
        """
        完整预处理流程

        Pipeline: 缓存检查 → 清洗 → 语义分块（续写） → 句子拆分（风格转换） →
                  生成续写样本 → LLM生成风格转换样本 → 格式转换 → 验证划分 → 缓存写入

        Args:
            raw_text: 原始输入文本
            inference_service: 推理服务实例（用于调用LLM）
            target_length: 目标分块长度
            train_ratio: 训练集比例

        Returns:
            包含train_data, val_data, metadata的字典
        """
        # Step 0: 检查缓存
        cached = self._load_from_cache(raw_text)
        if cached is not None:
            logger.info("[Preprocessing] Step 0 completed: loaded from cache")
            return cached
        logger.info("[Preprocessing] Step 0 completed: no cache found, proceeding with processing")

        # Step 1: 对原始文本进行语义分块（overlap=0，防止数据过大）
        raw_chunks = self.semantic_chunking(raw_text, target_length, overlap=0)
        # raw_chunks = raw_chunks[4:min(len(raw_chunks), 244)]
        logger.info(f"[Preprocessing] Step 1 completed: {len(raw_chunks)} raw chunks generated")

        # Step 2: 逐段清洗（整体缓存）
        chunks, cleaned_text = await self._clean_chunks(raw_chunks, raw_text, inference_service, target_length)
        logger.info(f"[Preprocessing] Step 2 completed: {len(chunks)} chunks cleaned")
        
        # Step 3: 句子拆分（用于风格转换任务）
        sentences = []
        for chunk in chunks:
            chunk_sentences = self.sentence_split(chunk.content)
            sentences.extend(chunk_sentences)
        sentences = sentences[:min(len(sentences), 450)]
        logger.info(f"[Preprocessing] Step 3 completed: {len(sentences)} sentences extracted")

        # Step 4: 生成续写样本
        continuation_samples = self.generate_continuation_samples(chunks)
        logger.info(f"[Preprocessing] Step 4 completed: {len(continuation_samples)} continuation samples generated")

        # Step 5: 生成风格转换样本（LLM增强）
        style_samples = await self.generate_style_transfer_samples(sentences, inference_service)
        logger.info(f"[Preprocessing] Step 5 completed: {len(style_samples)} style transfer samples generated")

        all_samples = continuation_samples + style_samples

        # Step 6: 转换为SFT格式
        formatted_data = self.to_sft_format(all_samples)
        logger.info(f"[Preprocessing] Step 6 completed: {len(formatted_data)} samples formatted to SFT")

        # Step 7: 验证和划分
        train_data, val_data, metadata = self.validate_and_split(formatted_data, train_ratio)
        logger.info(f"[Preprocessing] Step 7 completed: {len(train_data)} train / {len(val_data)} val samples")

        # 更新元数据
        metadata.update({
            "language": self._detect_language(raw_text),
            "original_length": len(raw_text),
            "cleaned_length": len(cleaned_text),
            "chunk_count": len(chunks),
            "sentence_count": len(sentences),
            "continuation_sample_count": len(continuation_samples),
            "style_sample_count": len(style_samples),
            "sample_count": len(all_samples),
            "style_tag": self.style_tag,
            "system_prompt": self.system_prompt
        })

        result = {
            "train_data": train_data,
            "val_data": val_data,
            "metadata": metadata,
            "chunks": [asdict(c) for c in chunks],
            "samples": all_samples,
            "cleaned_text": cleaned_text,
        }

        # Step 8: 写入缓存
        self._save_to_cache(raw_text, result)
        logger.info("[Preprocessing] Step 8 completed: result saved to cache")
        return result

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
        system = sample.get('system', '')
        instruction = sample.get('instruction', '')
        input_text = sample.get('input', '')
        output = sample.get('output', '')

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
            adjusted_raw = json.loads(response)

            adjusted = {
                'task_type': sample.get('task_type', 'general'),
                'system': adjusted_raw.get('system', system),
                'instruction': adjusted_raw.get('instruction', instruction),
                'input': adjusted_raw.get('input', input_text),
                'output': adjusted_raw.get('output', output),
                'metadata': sample.get('metadata', {})
            }

            adjusted['text'] = f"""<|system|>
{adjusted['system']}

<|task|>
{adjusted['task_type']}

<|instruction|>
{adjusted['instruction']}

<|input|>
{adjusted['input']}

<|response|>
{adjusted['output']}"""

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
