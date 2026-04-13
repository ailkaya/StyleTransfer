### 流程示例
┌─────────────────────────────────────────────────────────────────────────┐
│                         第一阶段：原始数据准备                             │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  输入：数万字小说原始文本（假设为《呐喊》全文，约7万字）                      │
│  格式：纯文本 / EPUB / PDF / TXT                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         第二阶段：文本清洗与标准化                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │  去除页眉页脚 │→│  统一编码格式 │→│  修正标点符号 │→│  段落边界识别 │    │
│  │  (UTF-8)    │  │  (全角/半角) │  │  (中文规范)  │  │  (换行处理)  │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         第三阶段：智能分块策略                              │
│                                                                         │
│   策略选择（推荐方案C：语义边界分块）                                       │
│                                                                         │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────┐    │
│   │  A. 固定长度  │    │  B. 段落级   │    │      C. 语义边界分块      │    │
│   │   (512字符)  │    │  (保留段落)  │    │  ┌─────────────────┐    │    │
│   │  ─────────  │    │  ─────────  │    │  │ 场景/对话/描写   │    │    │
│   │  简单但断句 │    │  较优但不均 │    │  │ 自然边界切分     │    │    │
│   │  可能破坏语义│    │  衡（长短不一）│    │  │ 目标：512-2048字 │    │    │
│   │  [不推荐]   │    │  [次选]     │    │  └─────────────────┘    │    │
│   └─────────────┘    └─────────────┘    │        [推荐★]           │    │
│                                          └─────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         第四阶段：训练样本构造                              │
│                                                                         │
│   每个分块 → 构造多轮对话格式（提升上下文学习能力）                          │
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────────┐  │
│   │  样本1（续写任务）                                               │  │
│   │  ┌─────────────┐                                                │  │
│   │  │ System      │ 你是鲁迅，中国现代文学奠基人，文笔犀利深刻。       │  │
│   │  ├─────────────┤                                                │  │
│   │  │ User        │ <鲁迅风格> 请续写："{前256字}"                   │  │
│   │  ├─────────────┤                                                │  │
│   │  │ Assistant   │ {后256字，即原文后续}                            │  │
│   │  └─────────────┘                                                │  │
│   └─────────────────────────────────────────────────────────────────┘  │
│                                    │                                    │
│   ┌─────────────────────────────────────────────────────────────────┐  │
│   │  样本2（风格模仿任务）                                            │  │
│   │  ┌─────────────┐                                                │  │
│   │  │ System      │ 你是鲁迅，中国现代文学奠基人。                   │  │
│   │  ├─────────────┤                                                │  │
│   │  │ User        │ <鲁迅风格> 请用鲁迅笔法描写："{场景描述}"         │  │
│   │  ├─────────────┤                                                │  │
│   │  │ Assistant   │ {原文对应段落的完整内容}                         │  │
│   │  └─────────────┘                                                │  │
│   └─────────────────────────────────────────────────────────────────┘  │
│                                    │                                    │
│   ┌─────────────────────────────────────────────────────────────────┐  │
│   │  样本3（问答任务 - 增强理解）                                     │  │
│   │  ┌─────────────┐                                                │  │
│   │  │ System      │ 你是鲁迅。                                       │  │
│   │  ├─────────────┤                                                │  │
│   │  │ User        │ <鲁迅风格> 这段文字想表达什么："{分块内容}"       │  │
│   │  ├─────────────┤                                                │  │
│   │  │ Assistant   │ {基于内容的解读 + 原文风格化重述}                │  │
│   │  └─────────────┘                                                │  │
│   └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│   数据增强：每个分块生成2-3种任务类型，总样本数 = 分块数 × 2~3             │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         第五阶段：格式标准化输出                            │
│                                                                         │
│   输出格式选项：                                                          │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐               │
│   │  Alpaca格式 │    │ ShareGPT格式 │    │ 自定义JSONL │               │
│   │  (指令微调) │    │ (对话多轮)  │    │  (最灵活)   │               │
│   └─────────────┘    └─────────────┘    └─────────────┘               │
│                                                                         │
│   推荐：ShareGPT格式用于Chat模型，Alpaca格式用于Base模型                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         第六阶段：质量验证与平衡                            │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│   │ 长度分布检查 │→│ 风格标签验证 │→│ 去重与相似度 │→│ 训练/验证划分│   │
│   │ (避免极端长)│  │ (标签一致性) │  │  (避免冗余) │  │ (95%/5%)   │   │
│   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         最终输出：训练数据集                                │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  train.jsonl  (95% - 用于训练)                                   │   │
│   │  val.jsonl    (5%  - 用于验证)                                   │   │
│   │  metadata.json (数据统计信息)                                    │   │
│   └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘


### 代码示例
import re
import json
import random
from typing import List, Dict, Tuple
from dataclasses import dataclass

@dataclass
class TextChunk:
    """文本分块数据结构"""
    content: str
    start_pos: int
    end_pos: int
    chunk_type: str  # 'narration', 'dialogue', 'description'
    source: str

class NovelDataProcessor:
    """小说数据处理器"""
    
    def __init__(self, style_tag: str = "<鲁迅风格>", system_prompt: str = None):
        self.style_tag = style_tag
        self.system_prompt = system_prompt or "你是鲁迅，中国现代文学奠基人，文笔犀利深刻，善用反讽与白话文。"
        self.chunks: List[TextChunk] = []
        
    # ==================== 第二阶段：文本清洗 ====================
    
    def clean_text(self, raw_text: str) -> str:
        """清洗原始文本"""
        # 1. 去除多余空白
        text = re.sub(r'\s+', ' ', raw_text)
        # 2. 标准化标点（英文标点→中文标点）
        text = text.replace(',', '，').replace('.', '。').replace('?', '？')
        # 3. 去除特殊字符
        text = re.sub(r'[^\u4e00-\u9fa5\u3000-\u303f\uff00-\uffef\s\w]', '', text)
        # 4. 段落边界规范化
        text = re.sub(r'\n+', '\n', text)
        return text.strip()
    
    # ==================== 第三阶段：智能分块 ====================
    
    def semantic_chunking(self, text: str, target_length: int = 1024, 
                         overlap: int = 256) -> List[TextChunk]:
        """
        语义边界分块策略
        优先在以下位置切分：段落结束 > 对话结束 > 句子结束
        """
        # 识别语义边界
        boundaries = self._find_semantic_boundaries(text)
        
        chunks = []
        start = 0
        chunk_id = 0
        
        while start < len(text):
            # 寻找最佳切分点
            end = self._find_optimal_split(text, start, target_length, boundaries)
            
            content = text[start:end].strip()
            if len(content) > 50:  # 过滤过短片段
                chunk_type = self._classify_chunk(content)
                self.chunks.append(TextChunk(
                    content=content,
                    start_pos=start,
                    end_pos=end,
                    chunk_type=chunk_type,
                    source=f"chunk_{chunk_id}"
                ))
                chunk_id += 1
            
            start = end - overlap  # 重叠窗口保持连贯性
            
        return self.chunks
    
    def _find_semantic_boundaries(self, text: str) -> List[int]:
        """识别文本中的语义边界位置"""
        boundaries = []
        
        # 段落边界（两个换行）
        for match in re.finditer(r'\n\s*\n', text):
            boundaries.append(match.end())
        
        # 对话结束（引号后）
        for match in re.finditer(r'[」』"].{0,5}[\n。！？]', text):
            boundaries.append(match.end())
        
        # 章节标题（如：第一章、一、等）
        for match in re.finditer(r'[第卷][一二三四五六七八九十百千\d]+[章节回]', text):
            boundaries.append(match.start())
            
        return sorted(set(boundaries))
    
    def _find_optimal_split(self, text: str, start: int, target: int, 
                           boundaries: List[int]) -> int:
        """在目标长度附近寻找最佳语义边界"""
        ideal_end = start + target
        max_end = min(start + target * 1.5, len(text))
        
        # 在理想位置±20%范围内寻找边界
        candidates = [b for b in boundaries if ideal_end * 0.8 <= b <= max_end]
        
        if candidates:
            # 选择最接近理想长度的边界
            return min(candidates, key=lambda x: abs(x - ideal_end))
        else:
            # 回退：在目标位置寻找最近的句子结束
            fallback = text.find('。', ideal_end)
            return fallback if fallback != -1 and fallback < max_end else min(ideal_end, len(text))
    
    def _classify_chunk(self, content: str) -> str:
        """分类文本块类型（用于后续多样化训练任务）"""
        dialogue_marks = ['「', '『', '"', '“', '‘']
        dialogue_count = sum(content.count(m) for m in dialogue_marks)
        
        if dialogue_count >= 4:
            return 'dialogue'
        elif any(w in content for w in ['描写', '景象', '看见', '只见']):
            return 'description'
        else:
            return 'narration'
    
    # ==================== 第四阶段：训练样本构造 ====================
    
    def generate_training_samples(self, chunks: List[TextChunk]) -> List[Dict]:
        """为每个分块生成多种训练样本"""
        samples = []
        
        for i, chunk in enumerate(chunks):
            # 任务1：续写任务（如果有下文）
            if i < len(chunks) - 1:
                sample = self._create_continuation_task(chunk, chunks[i+1])
                samples.append(sample)
            
            # 任务2：风格模仿（完整段落重写）
            sample = self._create_style_imitation_task(chunk)
            samples.append(sample)
            
            # 任务3：上下文问答（每3个chunk一组）
            if i >= 2:
                sample = self._create_qa_task(chunks[i-2:i+1])
                samples.append(sample)
                
        return samples
    
    def _create_continuation_task(self, current: TextChunk, next_chunk: TextChunk) -> Dict:
        """构造续写任务"""
        # 取当前块的前半部分作为提示，后半部分+下一块作为答案
        split_point = len(current.content) // 2
        prompt_text = current.content[:split_point]
        completion = current.content[split_point:] + " " + next_chunk.content[:500]
        
        return {
            "system": self.system_prompt,
            "instruction": f"{self.style_tag} 请续写：{prompt_text}",
            "input": "",
            "output": completion.strip(),
            "task_type": "continuation"
        }
    
    def _create_style_imitation_task(self, chunk: TextChunk) -> Dict:
        """构造风格模仿任务"""
        # 提取核心内容（去除修饰），要求用风格重写
        # 简化版：直接要求重写这段内容
        return {
            "system": self.system_prompt,
            "instruction": f"{self.style_tag} 请用鲁迅笔法描写以下场景：",
            "input": chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content,
            "output": chunk.content,
            "task_type": "style_imitation"
        }
    
    def _create_qa_task(self, context_chunks: List[TextChunk]) -> Dict:
        """构造问答任务，增强理解能力"""
        context = " ".join([c.content for c in context_chunks])
        # 提取关键句作为问题
        key_sentence = context_chunks[1].content[:100]
        
        return {
            "system": self.system_prompt,
            "instruction": f"{self.style_tag} 基于以下内容进行解读：",
            "input": context[:500],
            "output": f"这段文字表达了...（解读）\n\n原文：{key_sentence}...",
            "task_type": "comprehension"
        }
    
    # ==================== 第五阶段：格式输出 ====================
    
    def to_sharegpt_format(self, samples: List[Dict]) -> List[Dict]:
        """转换为ShareGPT对话格式"""
        sharegpt_data = []
        
        for sample in samples:
            conversation = {
                "id": f"sample_{len(sharegpt_data)}",
                "conversations": [
                    {"from": "system", "value": sample["system"]},
                    {"from": "human", "value": f"{sample['instruction']}\n{sample['input']}".strip()},
                    {"from": "gpt", "value": sample["output"]}
                ],
                "task_type": sample.get("task_type", "general")
            }
            sharegpt_data.append(conversation)
            
        return sharegpt_data
    
    def to_alpaca_format(self, samples: List[Dict]) -> List[Dict]:
        """转换为Alpaca指令格式"""
        return [{
            "instruction": s["instruction"],
            "input": s["input"],
            "output": s["output"],
            "system": s["system"]
        } for s in samples]
    
    # ==================== 第六阶段：质量验证 ====================
    
    def validate_and_split(self, data: List[Dict], train_ratio: float = 0.95) -> Tuple[List, List]:
        """验证数据质量并划分训练/验证集"""
        # 过滤异常样本
        valid_data = []
        for item in data:
            output_len = len(item.get("conversations", [{}])[2].get("value", ""))
            if 50 < output_len < 3000:  # 过滤过长或过短
                valid_data.append(item)
        
        # 统计信息
        lengths = [len(d["conversations"][2]["value"]) for d in valid_data]
        print(f"总样本数: {len(valid_data)}")
        print(f"平均长度: {sum(lengths)/len(lengths):.0f}")
        print(f"长度分布: 短(<500): {sum(1 for l in lengths if l<500)}, "
              f"中(500-1500): {sum(1 for l in lengths if 500<=l<1500)}, "
              f"长(>1500): {sum(1 for l in lengths if l>=1500)}")
        
        # 随机划分
        random.shuffle(valid_data)
        split_idx = int(len(valid_data) * train_ratio)
        
        return valid_data[:split_idx], valid_data[split_idx:]


# ==================== 使用示例 ====================

def main():
    # 假设原始小说文本
    raw_novel = """
    鲁迅小说原文...
    （此处为《呐喊》《彷徨》等数万字文本）
    """
    
    # 初始化处理器
    processor = NovelDataProcessor(
        style_tag="<鲁迅风格>",
        system_prompt="你是鲁迅，中国现代文学奠基人，文笔犀利深刻，善用反讽与白话文，关注社会现实与国民性批判。"
    )
    
    # 执行完整流程
    print("Step 1: 清洗文本...")
    clean_text = processor.clean_text(raw_novel)
    
    print("Step 2: 语义分块...")
    chunks = processor.semantic_chunking(clean_text, target_length=1024, overlap=256)
    print(f"生成分块数: {len(chunks)}")
    
    print("Step 3: 构造训练样本...")
    samples = processor.generate_training_samples(chunks)
    print(f"生成样本数: {len(samples)}")
    
    print("Step 4: 格式转换...")
    sharegpt_data = processor.to_sharegpt_format(samples)
    
    print("Step 5: 验证与划分...")
    train_data, val_data = processor.validate_and_split(sharegpt_data)
    
    # 保存文件
    with open("train.jsonl", "w", encoding="utf-8") as f:
        for item in train_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    
    with open("val.jsonl", "w", encoding="utf-8") as f:
        for item in val_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    
    print("处理完成！输出文件：train.jsonl, val.jsonl")

if __name__ == "__main__":
    main()