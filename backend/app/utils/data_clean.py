from .logging_config import get_logger
logger = get_logger(__name__)


def clean_and_filter_dataset(data):
    """
    清洗 + 过滤训练数据

    输入:
        data: List[{"text": ...}]

    输出:
        clean_data: List[{"text": str}]
    """
    clean_data = []

    for i, item in enumerate(data):
        try:
            text = item.get("text", None)

            # ===== 1. 空值过滤 =====
            if text is None:
                continue

            # ===== 2. 类型修复 =====
            if isinstance(text, list):
                # list → 拼接
                text = " ".join(map(str, text))
            elif not isinstance(text, str):
                # 其他类型 → 转字符串
                text = str(text)

            # ===== 3. 去空字符串 =====
            text = text.strip()
            if not text:
                continue

            # ===== 4. 长度过滤（防止极端数据）=====
            if len(text) < 5:       # 太短无意义
                continue
            if len(text) > 20000:   # 太长可能炸显存/tokenizer
                continue

            clean_data.append({"text": text})

        except Exception as e:
            logger.info(f"[Filter] Drop bad sample at index {i}: {e}")
            continue

    logger.info(f"[Filter] 原始数据: {len(data)} → 清洗后: {len(clean_data)}")
    return clean_data