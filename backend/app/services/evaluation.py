"""Evaluation service for style transfer results.

This module implements automatic evaluation metrics.
"""

import os
import random
import time
import re
from datetime import datetime
from typing import List, Tuple, Optional
from dataclasses import dataclass

import sacrebleu

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import Task, Style, AsyncSessionLocal
from ..db_operations import DatabaseOperations
from ..utils import get_logger

logger = get_logger(__name__)

# Load evaluation settings from config
from config import settings

EVALUATION_SAMPLE_COUNT = settings.EVALUATION_SAMPLE_COUNT
EVALUATION_MOCK_DELAY = settings.EVALUATION_MOCK_DELAY
EVALUATION_MOCK_MODE = settings.EVALUATION_MOCK_MODE


@dataclass
class EvaluationMetrics:
    """Evaluation metrics data class."""
    overall_score: float
    char_retention: float
    bleu_score: float
    bert_score: float
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


# def _calculate_semantic_similarity(source: str, target: str) -> float:
#     """Calculate semantic similarity using word and character overlap."""
#     source_words = set(re.findall(r'\b\w+\b', source.lower()))
#     target_words = set(re.findall(r'\b\w+\b', target.lower()))

#     if not source_words:
#         return 0.0

#     intersection = len(source_words & target_words)
#     union = len(source_words | target_words)
#     word_sim = (intersection / union * 100) if union > 0 else 0.0

#     source_chars = set(source.replace(' ', ''))
#     target_chars = set(target.replace(' ', ''))
#     char_sim = (len(source_chars & target_chars) / len(source_chars) * 100) if source_chars else 0.0

#     semantic_score = word_sim * 0.6 + char_sim * 0.4
#     return min(semantic_score, 100.0)


def _calculate_bertscore(source_texts: List[str], target_texts: List[str]) -> float:
    """Calculate BERTScore F1 between source and target texts using Chinese BERT.

    Candidates: target_texts, References: source_texts.
    Returns F1 mean scaled to 0-100.
    """
    try:
        from bert_score import score as bert_score_func

        if not source_texts or not target_texts:
            return 0.0

        P, R, F1 = bert_score_func(
            target_texts,
            source_texts,
            lang="zh",
            device="cpu",
            verbose=False
        )
        return F1.mean().item() * 100
    except Exception as e:
        logger.error(f"BERTScore calculation failed: {e}")
        return 0.0


def _calculate_bleu(source_texts: List[str], target_texts: List[str]) -> float:
    """Calculate corpus-level BLEU score between source and target texts.

    Uses jieba for Chinese word segmentation and sacrebleu for corpus-level BLEU.
    Reference: source_texts (training originals), Candidate: target_texts.
    """
    import jieba

    if not source_texts or not target_texts:
        return 0.0

    refs = [" ".join(jieba.cut(s)) for s in source_texts]
    hyps = [" ".join(jieba.cut(t)) for t in target_texts]

    bleu = sacrebleu.corpus_bleu(hyps, [refs])
    return bleu.score


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


def _extract_keywords_from_text(text: str, top_n: int = 50) -> List[str]:
    """Extract keywords from training text using simple frequency analysis."""
    import jieba

    # Tokenize text
    words = list(jieba.cut(text))

    # Filter: only keep Chinese words with length >= 2 and not stopwords
    stopwords = set(['的', '了', '在', '是', '我', '有', '和', '就', '不', '人',
                     '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去',
                     '你', '会', '着', '没有', '看', '好', '自己', '这'])

    filtered_words = [w for w in words
                      if len(w) >= 2
                      and re.match(r'^[\u4e00-\u9fff]+$', w)
                      and w not in stopwords]

    # Count frequency
    word_freq = {}
    for word in filtered_words:
        word_freq[word] = word_freq.get(word, 0) + 1

    # Get top N keywords
    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, freq in sorted_words[:top_n]]


async def _estimate_style_match(
    task_id: str,
    target_text: str,
    target_style: str,
    inference_service=None
) -> float:
    """Estimate style matching score by calling LLM API.

    Uses a large language model to judge how well the target_text matches
    the target_style, returning a score from 1 to 100.
    """
    if inference_service is None:
        logger.warning("No inference_service provided for style match evaluation, using fallback score")
        return 70.0

    prompt = (
        f"请判断以下文本是否符合『{target_style}』风格。\n\n"
        f"文本：{target_text}\n\n"
        f"请从1到100打分，1表示完全不符合，100表示完全符合。"
        f"只输出一个1-100之间的整数分数，不要有任何解释。"
    )

    try:
        result = await inference_service.call_llm_raw(
            prompt=prompt,
            system_prompt="你是一个专业的文学风格评审专家，只输出1-100的整数分数。",
            temperature=0.1,
            max_tokens=10,
        )

        # Extract the first integer from the response
        match = re.search(r'\b(\d{1,3})\b', result.strip())
        if match:
            score = int(match.group(1))
            score = max(1, min(100, score))
            logger.info(f"Style match score for '{target_style}': {score}")
            return float(score)
        else:
            logger.warning(f"Could not parse score from LLM response: {result}")
            return 70.0
    except Exception as e:
        logger.error(f"LLM style match evaluation failed: {e}")
        return 70.0


async def calculate_metrics(
    task_id: str,
    source_texts: List[str],
    target_texts: List[str],
    target_style: str,
    response_times: Optional[List[float]] = None,
    inference_service=None
) -> EvaluationMetrics:
    """
    Calculate evaluation metrics between source and target text arrays.

    Args:
        source_texts: List of original texts
        target_texts: List of transformed texts
        target_style: Target style name
        response_times: Optional list of response times
        inference_service: Optional inference service for LLM-based style evaluation

    Returns:
        EvaluationMetrics object
    """
    if len(source_texts) != len(target_texts):
        raise ValueError("Source and target text arrays must have the same length")

    if not source_texts:
        raise ValueError("Text arrays cannot be empty")

    sample_count = len(source_texts)

    bleu_score = _calculate_bleu(source_texts, target_texts)
    bert_score = _calculate_bertscore(source_texts, target_texts)

    semantic_scores = []
    char_retentions = []
    style_scores = []
    fluency_scores = []

    for src, tgt in zip(source_texts, target_texts):
        # semantic_scores.append(_calculate_semantic_similarity(src, tgt))
        char_retentions.append(_calculate_char_retention(src, tgt))
        style_scores.append(await _estimate_style_match(task_id, tgt, target_style, inference_service))
        fluency_scores.append(_estimate_fluency(tgt))

    length_ratio, avg_source_len, avg_target_len = _calculate_length_ratio(
        source_texts, target_texts
    )

    vocab_diversity = _calculate_vocab_diversity(target_texts)
    avg_response_time = sum(response_times) / len(response_times) if response_times else 0.0

    avg_semantic = sum(semantic_scores) / len(semantic_scores) if semantic_scores else 0.0
    avg_style = sum(style_scores) / len(style_scores)
    avg_fluency = sum(fluency_scores) / len(fluency_scores)

    overall = (
        bleu_score * 0.2 +
        bert_score * 0.6 +
        avg_style * 0.1 +
        avg_fluency * 0.1
    )

    return EvaluationMetrics(
        overall_score=round(overall, 1),
        # semantic_score=round(avg_semantic, 1),
        char_retention=round(sum(char_retentions) / len(char_retentions), 1),
        bleu_score=round(bleu_score, 1),
        bert_score=round(bert_score, 1),
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
    db = DatabaseOperations(async_mode=True)
    try:
        task = await db.get_task_async(task_id)
        if not task:
            return None
        # Get style using the style_id from task
        style = await db.get_style_async(task.style_id)
        return style
    finally:
        await db.close_async()


async def generate_test_samples(
    inference_service,
    task_id: str,
    sample_count: int = EVALUATION_SAMPLE_COUNT
) -> List[str]:
    """Generate diverse test samples using LLM API."""
    topics = [
        "日常生活", "文化娱乐", "社会热点", "个人成长"
    ]

    prompts = [
        "请写一段关于{topic}的简短文字，60字左右。",
        "描述一下你对{topic}的看法，约60字。",
        "请分享一段关于{topic}的经历或观点，60字左右。",
    ]

    # Get style_id once outside the loop
    style = await get_style_by_task_id(task_id=task_id)
    style_id = style.id if style else None

    samples = []

    for i in range(sample_count):
        topic = topics[i % len(topics)]
        prompt = prompts[i % len(prompts)].format(topic=topic)

        try:
            response = await inference_service.generate_style_transfer(
                input=prompt,
                target_style="标准",
                style_id=style_id,
                use_api=True,
            )
            samples.append(response.strip())
        except Exception as e:
            logger.error(f"Failed to generate sample {i+1}: {e}")
            samples.append(f"这是关于{topic}的一段示例文本，用于风格迁移测试。")

    return samples


async def generate_transferred_texts(
    inference_service,
    task_id: str,
    source_texts: List[str],
    target_style: str
) -> Tuple[List[str], List[float]]:
    """Generate style-transferred texts for given source texts."""
    transferred = []
    response_times = []

    # Get style_id once outside the loop
    style = await get_style_by_task_id(task_id=task_id)
    style_id = style.id if style else None

    for source in source_texts:
        start_time = time.time()

        try:
            result = await inference_service.generate_style_transfer(
                input=f"请把给定的文本转换为{target_style}风格，不要增加原文没有的含义，不要对输出进行解释，不要输出除了转化结果以外的东西。\n\n{source}",
                target_style=target_style,
                style_id=style_id,
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
        logger.info(f"[Evaluation] Starting evaluation for task: {task_id}, mock_mode: {EVALUATION_MOCK_MODE}")
        if EVALUATION_MOCK_MODE:
            # logger.info(f"[Evaluation] Using mock data for task: {task_id}")
            return self.generate_evaluation_data_mock(task_id=task_id)
        # logger.info(f"[Evaluation] Using real evaluation for task: {task_id}")
        return await self.generate_evaluation_data_true(task_id=task_id, inference_service=inference_service)

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
        # logger.info(f"[Evaluation] Starting true evaluation for task: {task_id}, inference_service={inference_service is not None}")

        style = await get_style_by_task_id(task_id)
        if not style:
            logger.error(f"[Evaluation] Style not found for task: {task_id}")
            raise ValueError(f"Task not found: {task_id}")
        logger.info(f"[Evaluation] Loaded style: {style.name}, target_style={style.target_style}")

        if inference_service:
            try:
                logger.info(f"[Evaluation] Generating {EVALUATION_SAMPLE_COUNT} test samples...")
                source_texts = await generate_test_samples(inference_service, task_id, sample_count=EVALUATION_SAMPLE_COUNT)
                logger.info(f"[Evaluation] Generated {len(source_texts)} test samples")
                for i, src in enumerate(source_texts):
                    logger.debug(f"[Evaluation] Sample {i+1}: {src[:60]}...")
            except Exception as e:
                logger.error(f"[Evaluation] Failed to generate samples: {e}")
                source_texts = self._get_fallback_samples()
                logger.info(f"[Evaluation] Fallback to {len(source_texts)} preset samples")
        else:
            source_texts = self._get_fallback_samples()
            logger.info(f"[Evaluation] No inference service, using {len(source_texts)} fallback samples")

        target_texts = []
        response_times = []

        if inference_service:
            try:
                logger.info(f"[Evaluation] Transferring {len(source_texts)} samples to style '{style.target_style}'...")
                target_texts, response_times = await generate_transferred_texts(
                    inference_service, task_id, source_texts, style.target_style
                )
                logger.info(f"[Evaluation] Transferred {len(target_texts)} texts, avg_response_time={sum(response_times)/len(response_times):.2f}s")
                for i, tgt in enumerate(target_texts):
                    logger.debug(f"[Evaluation] Transferred {i+1}: {tgt[:60]}...")
            except Exception as e:
                logger.error(f"[Evaluation] Failed to generate transfers: {e}")
                target_texts = source_texts
                response_times = [0.0] * len(source_texts)
        else:
            target_texts = source_texts
            response_times = [0.0] * len(source_texts)
            logger.info(f"[Evaluation] No inference service, using source texts as targets")

        logger.info(f"[Evaluation] Calculating metrics for {len(source_texts)} sample pairs...")
        metrics = await calculate_metrics(
            task_id=task_id,
            source_texts=source_texts,
            target_texts=target_texts,
            target_style=style.target_style,
            response_times=response_times,
            inference_service=inference_service
        )
        logger.info(
            f"[Evaluation] Metrics calculated: "
            f"overall_score={metrics.overall_score}, bleu={metrics.bleu_score}, bert={metrics.bert_score}, "
            f"style={metrics.style_score}, fluency={metrics.fluency_score}, "
            f"char_retention={metrics.char_retention}, vocab_diversity={metrics.vocab_diversity}, length_ratio={metrics.length_ratio}"
        )

        samples = [
            {
                "source": src[:300] + "..." if len(src) > 300 else src,
                "target": tgt[:300] + "..." if len(tgt) > 300 else tgt
            }
            for src, tgt in zip(source_texts[:3], target_texts[:3])
        ]
        logger.info(f"[Evaluation] Returning evaluation data with {len(samples)} display samples")

        return {
            "task_id": str(task_id),
            "task_name": style.name or "未命名任务",
            "target_style": style.target_style,
            "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M'),
            "overall_score": metrics.overall_score,
            "sample_count": metrics.sample_count,
            # "semantic_score": metrics.semantic_score,
            "char_retention": metrics.char_retention,
            "bleu_score": metrics.bleu_score,
            "bert_score": metrics.bert_score,
            "style_score": metrics.style_score,
            "fluency_score": metrics.fluency_score,
            "vocab_diversity": metrics.vocab_diversity,
            "length_ratio": metrics.length_ratio,
            "avg_response_time": metrics.avg_response_time,
            "samples": samples
        }

    def generate_evaluation_data_mock(self, task_id: str = "mock-task-id") -> dict:
        """
        Return hardcoded sample evaluation data for UI testing.

        Args:
            task_id: Optional task ID for the mock data

        Returns:
            Dictionary with sample evaluation data
        """
        time.sleep(EVALUATION_MOCK_DELAY)
        return {
            "task_id": task_id,
            "task_name": "示例风格任务",
            "target_style": "文艺",
            "generated_at": "2024-01-15 14:30",
            "overall_score": 74.5,
            "sample_count": 5,
            # "semantic_score": 82.5,
            "char_retention": 68.3,
            "bleu_score": 48.5,
            "bert_score": 76.4,
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
