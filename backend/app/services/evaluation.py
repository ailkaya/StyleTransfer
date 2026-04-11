"""Evaluation service for style transfer results.

This module contains placeholder implementation for v0.1.
In v0.2+, it will implement automatic evaluation metrics.
"""

from datetime import datetime


class EvaluationService:
    """Service for generating evaluation reports."""

    def generate_evaluation_html(self, task_id: str) -> str:
        """
        Generate placeholder evaluation HTML for v0.1.

        In v0.2+, this will:
        - Load generated and reference texts
        - Calculate BLEU scores
        - Calculate style classification accuracy
        - Generate visualization charts

        Args:
            task_id: Training task ID

        Returns:
            HTML string for evaluation report
        """
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>风格迁移评估报告</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }}
        .container {{
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            padding: 48px;
            max-width: 600px;
            width: 100%;
            text-align: center;
        }}
        .icon {{
            width: 80px;
            height: 80px;
            margin: 0 auto 24px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 36px;
        }}
        h1 {{
            color: #1a202c;
            font-size: 28px;
            margin-bottom: 16px;
        }}
        .subtitle {{
            color: #718096;
            font-size: 16px;
            margin-bottom: 32px;
            line-height: 1.6;
        }}
        .info-box {{
            background: #f7fafc;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 24px;
            text-align: left;
        }}
        .info-box p {{
            color: #4a5568;
            font-size: 14px;
            margin-bottom: 8px;
        }}
        .info-box p:last-child {{
            margin-bottom: 0;
        }}
        .info-box strong {{
            color: #2d3748;
        }}
        .badge {{
            display: inline-block;
            background: #edf2f7;
            color: #4a5568;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            margin-top: 16px;
        }}
        .footer {{
            color: #a0aec0;
            font-size: 12px;
            margin-top: 32px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">📊</div>
        <h1>风格迁移评估</h1>
        <p class="subtitle">
            评估功能将在后续版本开放<br>
            届时将提供 BLEU 分数、风格分类准确率等指标
        </p>
        <div class="info-box">
            <p><strong>任务ID:</strong> {task_id}</p>
            <p><strong>生成时间:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>版本:</strong> v0.1.0 (Preview)</p>
        </div>
        <span class="badge">Placeholder Interface</span>
        <p class="footer">
            个性化文本风格迁移系统
        </p>
    </div>
</body>
</html>"""
        return html

    def calculate_bleu(self, reference: str, generated: str) -> float:
        """
        Calculate BLEU score.

        TODO v0.2+: Implement BLEU calculation
        """
        # Placeholder
        return 0.0

    def calculate_style_accuracy(self, text: str, target_style: str) -> float:
        """
        Calculate style classification accuracy.

        TODO v0.2+: Implement style classifier
        """
        # Placeholder
        return 0.0


# Global evaluation service instance
evaluation_service = EvaluationService()
