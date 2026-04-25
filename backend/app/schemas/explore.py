"""Schemas for Explore integration."""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class EvaluationResultItem(BaseModel):
    """Schema for a single evaluation sample."""

    source: str
    expected: str
    generated: str
    score: float


class PullAdapterEvaluation(BaseModel):
    """Schema for evaluation data when pulling an adapter."""

    overall_score: float = Field(default=0.0, description="综合评分")
    sample_count: int = Field(default=0, description="样本数量")
    char_retention: float = Field(default=0.0, description="字符保留率")
    style_score: float = Field(default=0.0, description="风格符合度")
    fluency_score: float = Field(default=0.0, description="文本流畅度")
    vocab_diversity: float = Field(default=0.0, description="词汇多样性")
    length_ratio: float = Field(default=0.0, description="长度变化率")
    bleu_score: float = Field(default=0.0, description="BLEU得分")
    bert_score: float = Field(default=0.0, description="BERTScore得分")
    avg_response_time: float = Field(default=0.0, description="平均响应时间(秒)")
    samples: Optional[List[Dict[str, Any]]] = Field(default=None, description="样本对比数据")
    comment: Optional[str] = Field(default=None, description="用户评价/反馈")


class PullAdapterRequest(BaseModel):
    """Schema for pulling an adapter from explore cloud."""

    cloud_adapter_id: str = Field(..., description="Cloud adapter ID")
    style_name: str = Field(..., min_length=1, max_length=50, description="Style name")
    style_tag: str = Field(..., min_length=1, max_length=50, description="Style tag / target style")
    description: Optional[str] = Field(None, max_length=500, description="Description")
    base_model: str = Field(..., min_length=1, max_length=50, description="Base model")
    evaluation_results: Optional[PullAdapterEvaluation] = Field(None, description="评估结果")


class PullAdapterResponse(BaseModel):
    """Schema for pull adapter response."""

    id: str
    name: str
    target_style: str
    description: Optional[str] = None
    base_model: str
    adapter_path: Optional[str] = None
    status: str
    source: str
    created_at: str
