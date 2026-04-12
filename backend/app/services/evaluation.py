"""Evaluation service for style transfer results.

This module implements automatic evaluation metrics.
"""

import os
import time
import re
from datetime import datetime
from typing import List, Tuple, Optional
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import Task, Style, AsyncSessionLocal
from ..utils import get_logger

logger = get_logger(__name__)


@dataclass
class EvaluationMetrics:
    """Evaluation metrics data class."""
    overall_score: float
    semantic_score: float
    char_retention: float
    style_score: float
    fluency_score: float
    vocab_diversity: float
    length_ratio: float
    avg_source_length: float
    avg_target_length: float
    avg_response_time: float
    sample_count: int


def _calculate_char_retention(source: str, target: str) -> float:
    """Calculate character retention rate between source and target."""
    source_chars = set(source.replace(' ', '').replace('\n', ''))
    target_chars = set(target.replace(' ', '').replace('\n', ''))

    if not source_chars:
        return 0.0

    common_chars = source_chars & target_chars
    retention = len(common_chars) / len(source_chars) * 100
    return min(retention, 100.0)


def _calculate_vocab_diversity(texts: List[str]) -> float:
    """Calculate vocabulary diversity (unique words / total words)."""
    all_words = []
    for text in texts:
        words = re.findall(r'\b\w+\b', text.lower())
        all_words.extend(words)

    if not all_words:
        return 0.0

    unique_words = set(all_words)
    diversity = len(unique_words) / len(all_words) * 100
    return diversity


def _calculate_length_ratio(source_texts: List[str], target_texts: List[str]) -> Tuple[float, float, float]:
    """Calculate average length ratio between source and target texts."""
    if not source_texts or not target_texts:
        return 0.0, 0.0, 0.0

    source_lengths = [len(text) for text in source_texts]
    target_lengths = [len(text) for text in target_texts]

    avg_source = sum(source_lengths) / len(source_lengths)
    avg_target = sum(target_lengths) / len(target_lengths)

    ratio = (avg_target / avg_source * 100) if avg_source > 0 else 0.0

    return ratio, avg_source, avg_target


def _calculate_semantic_similarity(source: str, target: str) -> float:
    """Calculate semantic similarity using word and character overlap."""
    source_words = set(re.findall(r'\b\w+\b', source.lower()))
    target_words = set(re.findall(r'\b\w+\b', target.lower()))

    if not source_words:
        return 0.0

    intersection = len(source_words & target_words)
    union = len(source_words | target_words)
    word_sim = (intersection / union * 100) if union > 0 else 0.0

    source_chars = set(source.replace(' ', ''))
    target_chars = set(target.replace(' ', ''))
    char_sim = (len(source_chars & target_chars) / len(source_chars) * 100) if source_chars else 0.0

    semantic_score = word_sim * 0.6 + char_sim * 0.4
    return min(semantic_score, 100.0)


def _estimate_fluency(text: str) -> float:
    """Estimate text fluency based on heuristics."""
    if not text:
        return 0.0

    sentences = re.split(r'[。！？.!?]', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return 50.0

    avg_len = sum(len(s) for s in sentences) / len(sentences)
    length_score = 100 - abs(avg_len - 30) * 2
    length_score = max(0, min(100, length_score))

    punct_count = len(re.findall(r'[。！？，、；：""''（）【】]', text))
    punct_ratio = punct_count / len(text) if text else 0
    punct_score = 100 - abs(punct_ratio - 0.15) * 500
    punct_score = max(0, min(100, punct_score))

    repeats = len(re.findall(r'(.)\1{3,}', text))
    repeat_score = 100 - repeats * 10
    repeat_score = max(0, repeat_score)

    fluency = length_score * 0.4 + punct_score * 0.35 + repeat_score * 0.25
    return fluency


def _estimate_style_match(target_text: str, target_style: str) -> float:
    """Estimate style matching score based on keywords."""
    style_keywords = {
        '幽默': ['哈哈', '笑话', '有趣', '搞笑', '逗', '乐', '笑', '好玩', '滑稽', '诙谐'],
        '严肃': ['郑重', '严肃', '认真', '严谨', '正式', '庄重', '严格', '重要', '重大'],
        '学术': ['研究表明', '实验', '数据', '分析', '理论', '方法', '结论', '证明', '根据'],
        '文艺': ['诗意', '优美', '细腻', '浪漫', '意境', '情怀', '灵动', '雅致'],
        '口语': ['咱们', '是吧', '那个', '这个', '哎呀', '嗯', '啊', '呢', '吧', '啦'],
        '商务': ['合作', '项目', '方案', '客户', '市场', '战略', '效益', '优化', '提升'],
        '新闻': ['报道', '记者', '据悉', '最新消息', '事件', '发布', '声明', '指出'],
    }

    keywords = style_keywords.get(target_style, [])

    if not keywords:
        return 70.0

    text_lower = target_text.lower()
    keyword_count = sum(1 for kw in keywords if kw in text_lower)
    score = 50 + keyword_count * 10
    return min(score, 100.0)


def calculate_metrics(
    source_texts: List[str],
    target_texts: List[str],
    target_style: str,
    response_times: Optional[List[float]] = None
) -> EvaluationMetrics:
    """
    Calculate evaluation metrics between source and target text arrays.

    Args:
        source_texts: List of original texts
        target_texts: List of transformed texts
        target_style: Target style name
        response_times: Optional list of response times

    Returns:
        EvaluationMetrics object
    """
    if len(source_texts) != len(target_texts):
        raise ValueError("Source and target text arrays must have the same length")

    if not source_texts:
        raise ValueError("Text arrays cannot be empty")

    sample_count = len(source_texts)

    semantic_scores = []
    char_retentions = []
    style_scores = []
    fluency_scores = []

    for src, tgt in zip(source_texts, target_texts):
        semantic_scores.append(_calculate_semantic_similarity(src, tgt))
        char_retentions.append(_calculate_char_retention(src, tgt))
        style_scores.append(_estimate_style_match(tgt, target_style))
        fluency_scores.append(_estimate_fluency(tgt))

    length_ratio, avg_source_len, avg_target_len = _calculate_length_ratio(
        source_texts, target_texts
    )

    vocab_diversity = _calculate_vocab_diversity(target_texts)
    avg_response_time = sum(response_times) / len(response_times) if response_times else 0.0

    avg_semantic = sum(semantic_scores) / len(semantic_scores)
    avg_style = sum(style_scores) / len(style_scores)
    avg_fluency = sum(fluency_scores) / len(fluency_scores)

    overall = (
        avg_semantic * 0.3 +
        avg_style * 0.3 +
        avg_fluency * 0.2 +
        min(vocab_diversity, 100) * 0.1 +
        (100 - abs(length_ratio - 100)) * 0.1
    )

    return EvaluationMetrics(
        overall_score=round(overall, 1),
        semantic_score=round(avg_semantic, 1),
        char_retention=round(sum(char_retentions) / len(char_retentions), 1),
        style_score=round(avg_style, 1),
        fluency_score=round(avg_fluency, 1),
        vocab_diversity=round(vocab_diversity, 1),
        length_ratio=round(length_ratio, 1),
        avg_source_length=round(avg_source_len, 1),
        avg_target_length=round(avg_target_len, 1),
        avg_response_time=round(avg_response_time, 2),
        sample_count=sample_count
    )


async def get_style_by_task_id(task_id: str) -> Optional[Style]:
    """Get style information by task ID."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Task, Style).join(Style).where(Task.id == task_id)
        )
        row = result.first()

        if not row:
            return None

        return row[1]


async def generate_test_samples(
    inference_service,
    sample_count: int = 5
) -> List[str]:
    """Generate diverse test samples using LLM API."""
    topics = [
        "科技与创新", "日常生活", "工作职场", "教育培训",
        "文化娱乐", "商业经济", "社会热点", "个人成长"
    ]

    prompts = [
        "请写一段关于{topic}的简短文字，100字左右。",
        "描述一下你对{topic}的看法，约80-120字。",
        "请分享一段关于{topic}的经历或观点，100字左右。",
    ]

    samples = []

    for i in range(sample_count):
        topic = topics[i % len(topics)]
        prompt = prompts[i % len(prompts)].format(topic=topic)

        try:
            response = await inference_service.generate_style_transfer(
                original_text=prompt,
                requirement="生成一段自然的、多样化的文本内容",
                target_style="标准"
            )
            samples.append(response.strip())
        except Exception as e:
            logger.error(f"Failed to generate sample {i+1}: {e}")
            samples.append(f"这是关于{topic}的一段示例文本，用于风格迁移测试。")

    return samples


async def generate_transferred_texts(
    inference_service,
    source_texts: List[str],
    target_style: str
) -> Tuple[List[str], List[float]]:
    """Generate style-transferred texts for given source texts."""
    transferred = []
    response_times = []

    for source in source_texts:
        start_time = time.time()

        try:
            result = await inference_service.generate_style_transfer(
                original_text=source,
                requirement=f"转换为{target_style}风格",
                target_style=target_style
            )
            transferred.append(result.strip())
        except Exception as e:
            logger.error(f"Failed to transfer text: {e}, Source: {source[:50]}...")
            transferred.append(source)

        response_times.append(time.time() - start_time)

    return transferred, response_times


class EvaluationService:
    """Service for generating evaluation data."""

    def _get_fallback_samples(self) -> List[str]:
        """Get fallback sample texts."""
        return [
            "人工智能正在改变我们的生活方式。从智能手机到自动驾驶汽车，AI技术已经渗透到我们日常生活的方方面面。",
            "在现代社会中，工作效率的提升是每个人都关注的话题。如何合理安排时间、优化工作流程，成为了职场人士必须思考的问题。",
            "教育对于个人成长至关重要。通过不断学习和实践，我们能够不断提升自己的能力，适应快速变化的世界。",
            "健康的生活方式包括均衡的饮食、规律的运动和充足的睡眠。保持良好的生活习惯有助于提高生活质量。",
            "团队合作是现代企业中不可或缺的一部分。有效的沟通和协作能够帮助团队更好地完成任务，实现共同目标。"
        ]
    
    async def generate_evaluation_data(
        self,
        task_id: str,
        inference_service=None
    ) -> dict:
        # return self.generate_evaluation_data_true(task_id=task_id, inference_service=inference_service)
        return self.get_mock_evaluation_data(task_id=task_id)

    async def generate_evaluation_data_true(
        self,
        task_id: str,
        inference_service=None
    ) -> dict:
        """
        Generate evaluation data dictionary for frontend.

        Args:
            task_id: Training task ID
            inference_service: Optional inference service instance

        Returns:
            Dictionary with evaluation metrics and sample data
        """
        style = await get_style_by_task_id(task_id)
        if not style:
            raise ValueError(f"Task not found: {task_id}")

        if inference_service:
            try:
                source_texts = await generate_test_samples(inference_service, sample_count=5)
            except Exception as e:
                logger.error(f"Failed to generate samples: {e}")
                source_texts = self._get_fallback_samples()
        else:
            source_texts = self._get_fallback_samples()

        target_texts = []
        response_times = []

        if inference_service:
            try:
                target_texts, response_times = await generate_transferred_texts(
                    inference_service, source_texts, style.target_style
                )
            except Exception as e:
                logger.error(f"Failed to generate transfers: {e}")
                target_texts = source_texts
                response_times = [0.0] * len(source_texts)
        else:
            target_texts = source_texts
            response_times = [0.0] * len(source_texts)

        metrics = calculate_metrics(
            source_texts=source_texts,
            target_texts=target_texts,
            target_style=style.target_style,
            response_times=response_times
        )

        samples = [
            {
                "source": src[:300] + "..." if len(src) > 300 else src,
                "target": tgt[:300] + "..." if len(tgt) > 300 else tgt
            }
            for src, tgt in zip(source_texts[:3], target_texts[:3])
        ]

        return {
            "task_id": str(task_id),
            "task_name": style.name or "未命名任务",
            "target_style": style.target_style,
            "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M'),
            "overall_score": metrics.overall_score,
            "sample_count": metrics.sample_count,
            "semantic_score": metrics.semantic_score,
            "char_retention": metrics.char_retention,
            "style_score": metrics.style_score,
            "fluency_score": metrics.fluency_score,
            "vocab_diversity": metrics.vocab_diversity,
            "length_ratio": metrics.length_ratio,
            "avg_response_time": metrics.avg_response_time,
            "samples": samples
        }

    def get_mock_evaluation_data(self, task_id: str = "mock-task-id") -> dict:
        """
        Return hardcoded sample evaluation data for UI testing.

        Args:
            task_id: Optional task ID for the mock data

        Returns:
            Dictionary with sample evaluation data
        """
        time.sleep(20)
        return {
            "task_id": task_id,
            "task_name": "示例风格任务",
            "target_style": "文艺",
            "generated_at": "2024-01-15 14:30",
            "overall_score": 85.6,
            "sample_count": 5,
            "semantic_score": 82.5,
            "char_retention": 68.3,
            "style_score": 91.2,
            "fluency_score": 88.7,
            "vocab_diversity": 75.4,
            "length_ratio": 105.2,
            "avg_response_time": 1.25,
            "samples": [
                {
                    "source": "人工智能正在改变我们的生活方式。从智能手机到自动驾驶汽车，AI技术已经渗透到我们日常生活的方方面面。",
                    "target": "人工智能如一位悄然降临的诗人，以智慧之笔描绘着生活的画卷。从掌中的智能伴侣到道路上自主驰骋的座驾，AI的韵律已融入时光的每一个角落。"
                },
                {
                    "source": "在现代社会中，工作效率的提升是每个人都关注的话题。如何合理安排时间、优化工作流程，成为了职场人士必须思考的问题。",
                    "target": "于这纷繁的现代尘世，效率的追求宛如一曲悠扬的乐章，萦绕于每个人的心间。如何以智慧编织时光的锦缎，让工作的溪流更加畅达，乃是每一位行者必修的功课。"
                },
                {
                    "source": "教育对于个人成长至关重要。通过不断学习和实践，我们能够不断提升自己的能力，适应快速变化的世界。",
                    "target": "教育，乃是灵魂成长的甘霖，滋养着心田的每一寸土壤。在求知与实践的旅途中，我们如羽翼渐丰的飞鸟，不断向着更高的苍穹翱翔，以适应这瞬息万变的世界。"
                }
            ]
        }


evaluation_service = EvaluationService()
