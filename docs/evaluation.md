  1. overall_score（综合得分）

  - 介绍：整体风格迁移质量的综合评分。
  - 计算方法：
    - bleu_score * 0.30（BLEU 得分占30%）
    - bert_score * 0.20（BERTScore 占20%）
    - avg_style * 0.20（风格匹配度占20%）
    - avg_fluency * 0.15（文本流畅度占15%）
    - vocab_diversity * 0.075（词汇多样性占7.5%）
    - (100 - abs(length_ratio - 100)) * 0.075（长度比率接近100%的程度占7.5%）

  2. bleu_score（BLEU 得分）

  - 介绍：基于 n-gram 重叠度衡量转换后文本对训练原文本的内容保留程度，采用 Corpus-BLEU。
  - 参考文本来源：从该任务对应的 `training_data_path/original.txt` 中随机采样 `EVALUATION_SAMPLE_COUNT` 条训练原文本作为参考文本（source_texts）。若文件不存在或行数不足，则回退到系统预设的 fallback 样本。
  - 计算方法（`_calculate_bleu`）：
    - 使用 `jieba.cut` 对 source_texts 和 target_texts 分别进行中文分词
    - 使用 `sacrebleu.corpus_bleu(hypotheses=target_texts, references=[source_texts])` 计算语料级 BLEU
    - 返回 sacrebleu 的 `score`（0-100 的百分制数值）

  3. bert_score（BERTScore）

  - 介绍：基于中文 BERT 嵌入语义相似度衡量转换后文本与训练原文本的语义保留程度，采用 F1 均值。弥补 BLEU 基于 n-gram 严格匹配的局限性。
  - 参考文本来源：与 BLEU 共用同一来源，即从 `training_data_path/original.txt` 中采样训练原文本作为参考文本（source_texts）。
  - 计算方法（`_calculate_bertscore`）：
    - 调用 `bert_score(target_texts, source_texts, lang="zh", device="cpu", verbose=False)`
    - 使用 `bert-base-chinese` 模型计算文本对的 Precision、Recall、F1
    - 返回 F1 均值乘以 100（`F1.mean().item() * 100`，0-100 的百分制数值）

  4. char_retention（字符保留率）

  - 介绍：衡量目标文本对源文本中独特字符的保留比例。
  - 计算方法（`_calculate_char_retention`）：
    - 去除空格和换行后，分别得到源文本和目标文本的字符集合
    - len(共同字符) / len(源字符集合) * 100

  5. style_score（风格匹配度）

  - 介绍：评估转换后的文本是否符合目标风格。
  - 计算方法（`_estimate_style_match`）：
    - 预定义了常见风格的关键词库（如"幽默"、"严肃"、"文艺"等）
    - 若目标风格不在预设库中，则尝试从训练数据的 `original.txt` 中提取高频关键词作为风格标识
    - 统计目标文本中包含的关键词数量：50 + keyword_count * 10，上限100

  6. fluency_score（流畅度）

  - 介绍：基于启发式规则评估文本的通顺程度。
  - 计算方法（`_estimate_fluency`）：
    - 句子长度分（40%）：平均句长越接近30字得分越高
    - 标点密度分（35%）：中文标点占比越接近15%得分越高
    - 重复字符分（25%）：惩罚连续重复4次以上的字符

  7. vocab_diversity（词汇多样性）

  - 介绍：衡量生成文本的用词丰富程度。
  - 计算方法（`_calculate_vocab_diversity`）：
    - 提取所有目标文本中的单词（`\b\w+\b`）
    - len(唯一单词) / len(总单词) * 100

  8. length_ratio（长度比率）

  - 介绍：目标文本平均长度相对于源文本平均长度的比例。
  - 计算方法（`_calculate_length_ratio`）：
    - avg_target_length / avg_source_length * 100

  9. avg_source_length / avg_target_length（平均长度）

  - 介绍：源文本和目标文本的平均字符数。
  - 计算方法：分别计算 sum(len(text)) / count

  10. avg_response_time（平均响应时间）

  - 介绍：风格迁移接口的平均推理耗时（秒）。
  - 计算方法：sum(response_times) / len(response_times)

  11. sample_count（样本数）

  - 介绍：参与评估的文本对数量，默认为 `EVALUATION_SAMPLE_COUNT`（可通过环境变量配置）。
