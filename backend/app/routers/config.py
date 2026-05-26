"""API routes for configuration management."""

import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, HTTPException

from ..schemas import Response, ConfigItem, ConfigCategory, ConfigListResponse, ConfigUpdateRequest, ConfigUpdateResponse
from ..utils import get_logger

router = APIRouter(prefix="/api/config", tags=["config"])
logger = get_logger(__name__)

# Configuration categories mapping with display labels
CONFIG_CATEGORIES = {
    "app": ("应用配置", ["APP_NAME", "APP_VERSION", "DEBUG", "LOG_LEVEL", "LOG_FILE"]),
    "database": ("数据库配置", ["DATABASE_URL", "SYNC_DATABASE_URL", "DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"]),
    "redis": ("Redis/Celery 配置", ["REDIS_URL", "CELERY_BROKER_URL", "CELERY_RESULT_BACKEND", "REDIS_HOST", "REDIS_PORT", "REDIS_DB"]),
    "llm": ("大模型 API 配置", ["LLM_BASE_URL", "LLM_MODEL_NAME", "LLM_API_KEY", "LLM_TIMEOUT"]),
    "storage": ("文件存储配置", ["UPLOAD_DIR", "MODELS_DIR", "MAX_UPLOAD_SIZE"]),
    "cors": ("CORS 配置", ["CORS_ORIGINS"]),
    "security": ("安全配置", ["SECRET_KEY", "ACCESS_TOKEN_EXPIRE_MINUTES"]),
    "evaluation": ("评估配置", ["EVALUATION_SAMPLE_COUNT", "EVALUATION_MOCK_DELAY", "EVALUATION_MOCK_MODE", "APPLY_COMMENT_ADJUSTMENT"]),
    "training": ("训练配置", ["TRAINING_MOCK_MODE", "TRAINING_USE_CHUNK_DATA", "SIMPLE_PREPROCESSING"]),
    "model": ("模型管理配置", ["MODEL_RESERVED_GPU_RATIO", "RECOVER_PENDING_TASKS_ON_STARTUP", "ENABLE_MESSAGE_HISTORY", "GENERATING_MOCK_MODE"]),
    "explore": ("探索服务配置", ["EXPLORE_SERVICE_URL"]),
}

# Sensitive keys that should be masked
SENSITIVE_KEYS = {
    "LLM_API_KEY", "SECRET_KEY", "DB_PASSWORD", "DATABASE_URL", "SYNC_DATABASE_URL"
}

# Keys that require service restart to take effect
REQUIRES_RESTART_KEYS = {
    "APP_NAME", "APP_VERSION", "DATABASE_URL", "SYNC_DATABASE_URL", "REDIS_URL",
    "CELERY_BROKER_URL", "CELERY_RESULT_BACKEND", "UPLOAD_DIR", "MODELS_DIR",
    "SECRET_KEY", "EXPLORE_SERVICE_URL"
}

# Descriptions for configuration items
CONFIG_DESCRIPTIONS = {
    "APP_NAME": "应用名称",
    "APP_VERSION": "应用版本号",
    "DEBUG": "调试模式 (true/false)",
    "LOG_LEVEL": "日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    "LOG_FILE": "日志文件路径 (可选)",
    "DATABASE_URL": "PostgreSQL 异步数据库连接字符串",
    "SYNC_DATABASE_URL": "PostgreSQL 同步数据库连接字符串 (用于 Celery 任务)",
    "DB_HOST": "数据库主机地址",
    "DB_PORT": "数据库端口",
    "DB_NAME": "数据库名称",
    "DB_USER": "数据库用户名",
    "DB_PASSWORD": "数据库密码",
    "REDIS_URL": "Redis 连接 URL",
    "CELERY_BROKER_URL": "Celery Broker URL",
    "CELERY_RESULT_BACKEND": "Celery 结果后端 URL",
    "REDIS_HOST": "Redis 主机地址",
    "REDIS_PORT": "Redis 端口",
    "REDIS_DB": "Redis 数据库编号",
    "LLM_BASE_URL": "大模型 API 基础 URL",
    "LLM_MODEL_NAME": "大模型名称",
    "LLM_API_KEY": "大模型 API 密钥",
    "LLM_TIMEOUT": "API 请求超时时间 (秒)",
    "UPLOAD_DIR": "上传文件存储路径",
    "MODELS_DIR": "模型文件存储路径",
    "MAX_UPLOAD_SIZE": "最大上传文件大小 (MB)",
    "CORS_ORIGINS": "允许的跨域源 (逗号分隔, * 表示允许所有)",
    "SECRET_KEY": "安全密钥 (用于加密令牌)",
    "ACCESS_TOKEN_EXPIRE_MINUTES": "访问令牌过期时间 (分钟)",
    "EVALUATION_SAMPLE_COUNT": "评估时生成的测试样本数量",
    "EVALUATION_MOCK_DELAY": "Mock 评估时的延迟时间 (秒)",
    "EVALUATION_MOCK_MODE": "是否使用 Mock 评估数据 (true/false)",
    "APPLY_COMMENT_ADJUSTMENT": "是否将评论应用于下次微调 (true/false)",
    "TRAINING_MOCK_MODE": "训练 Mock 模式 (true=模拟训练, false=真实 QLoRA 训练)",
    "TRAINING_USE_CHUNK_DATA": "训练数据生成是否使用原始 chunks 数据",
    "SIMPLE_PREPROCESSING": "简化预处理阶段 (true=每类任务只生成1条样本)",
    "MODEL_RESERVED_GPU_RATIO": "GPU 显存预留比例 (0.15 ~ 0.20)",
    "RECOVER_PENDING_TASKS_ON_STARTUP": "启动时是否恢复未完成的任务",
    "ENABLE_MESSAGE_HISTORY": "是否启用消息上下文拼接",
    "GENERATING_MOCK_MODE": "是否通过 API 代替本地模型生成 (true/false)",
    "EXPLORE_SERVICE_URL": "探索服务地址",
}


def get_env_file_path() -> str:
    """Get the path to the .env file."""
    # Look for .env in the backend directory
    backend_dir = Path(__file__).parent.parent.parent
    env_path = backend_dir / ".env"
    if env_path.exists():
        return str(env_path)
    # Fallback to .env.example if .env doesn't exist
    example_path = backend_dir / ".env.example"
    if example_path.exists():
        return str(example_path)
    return str(env_path)


def parse_value_type(value: str) -> tuple[str, str]:
    """
    Parse the value and determine its type.
    Returns (type, normalized_value)
    """
    value = value.strip()

    # Check for boolean
    if value.lower() in ("true", "false"):
        return ("boolean", value.lower())

    # Check for integer
    if re.match(r'^-?\d+$', value):
        return ("integer", value)

    # Check for float
    if re.match(r'^-?\d+\.\d+$', value):
        return ("float", value)

    return ("string", value)


def mask_sensitive_value(key: str, value: str) -> str:
    """Mask sensitive value for display."""
    if not value or len(value) <= 8:
        return "********" if value else ""

    # Show first 4 and last 4 characters for long values
    return f"{value[:4]}****{value[-4:]}"


def parse_env_file(env_path: str) -> Dict[str, Any]:
    """
    Parse the .env file and return a dictionary of configurations.
    Preserves comments and empty lines for reconstruction.
    """
    configs = {}
    lines = []

    if not os.path.exists(env_path):
        logger.warning(f"Env file not found: {env_path}")
        return configs, lines

    with open(env_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line_num, line in enumerate(lines):
        line_content = line.rstrip('\n')
        stripped = line_content.strip()

        # Empty line
        if not stripped:
            continue

        # Comment line
        if stripped.startswith('#'):
            continue

        # Key-value pair
        match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)=(.*)$', line_content)
        if match:
            key = match.group(1)
            value = match.group(2)
            configs[key] = {
                'value': value,
                'line_num': line_num,
                'raw_line': line_content,
            }

    return configs, lines


def categorize_config(key: str) -> str:
    """Determine the category for a configuration key."""
    for category, (label, keys) in CONFIG_CATEGORIES.items():
        if key in keys:
            return category

    # Default categorization based on prefix
    if key.startswith(("APP_", "DEBUG", "LOG_")):
        return "app"
    elif key.startswith(("DB_", "DATABASE_", "SYNC_DATABASE")):
        return "database"
    elif key.startswith(("REDIS_", "CELERY_")):
        return "redis"
    elif key.startswith("LLM_"):
        return "llm"
    elif key.startswith(("UPLOAD_", "MODELS_", "MAX_UPLOAD")):
        return "storage"
    elif key.startswith("CORS_"):
        return "cors"
    elif key.startswith(("SECRET_", "ACCESS_TOKEN")):
        return "security"
    elif key.startswith("EVALUATION_"):
        return "evaluation"
    elif key.startswith("TRAINING_") or key == "SIMPLE_PREPROCESSING":
        return "training"
    elif key.startswith(("MODEL_", "RECOVER_", "ENABLE_", "GENERATING_")):
        return "model"
    elif key.startswith("EXPLORE_"):
        return "explore"

    return "other"


def create_config_item(key: str, value: str) -> ConfigItem:
    """Create a ConfigItem from key and value."""
    value_type, normalized_value = parse_value_type(value)
    category = categorize_config(key)
    is_sensitive = key in SENSITIVE_KEYS
    requires_restart = key in REQUIRES_RESTART_KEYS
    description = CONFIG_DESCRIPTIONS.get(key, "")

    # Determine if this is a secret type
    if is_sensitive:
        value_type = "secret"

    display_value = mask_sensitive_value(key, value) if is_sensitive else value

    return ConfigItem(
        key=key,
        value=display_value,
        raw_value=value if is_sensitive else None,
        value_type=value_type,
        category=category,
        description=description,
        is_sensitive=is_sensitive,
        requires_restart=requires_restart,
    )


def update_env_file(env_path: str, updates: Dict[str, str]) -> tuple[bool, Optional[str], List[dict]]:
    """
    Update the .env file with new values.
    Returns (success, backup_path, failures)
    """
    if not os.path.exists(env_path):
        logger.error(f"Env file not found: {env_path}")
        return False, None, [{"key": k, "reason": "Env file not found"} for k in updates.keys()]

    # Create backup
    backup_path = None
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{env_path}.backup.{timestamp}"
        shutil.copy2(env_path, backup_path)
        logger.info(f"Created backup: {backup_path}")
    except Exception as e:
        logger.error(f"Failed to create backup: {e}")
        return False, None, [{"key": k, "reason": f"Backup failed: {e}"} for k in updates.keys()]

    # Parse existing file
    configs, lines = parse_env_file(env_path)

    # Track which keys need to be added
    keys_to_add = set(updates.keys())
    updated_lines = []
    failures = []

    # Process existing lines
    for line in lines:
        line_content = line.rstrip('\n')
        stripped = line_content.strip()

        # Keep empty lines and comments as-is
        if not stripped or stripped.startswith('#'):
            updated_lines.append(line_content)
            continue

        # Check if this line contains a key we want to update
        match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)=(.*)$', line_content)
        if match:
            key = match.group(1)
            if key in updates:
                # Update this line
                new_value = updates[key]
                updated_lines.append(f"{key}={new_value}")
                keys_to_add.discard(key)
                logger.info(f"Updated config: {key}")
            else:
                # Keep original line
                updated_lines.append(line_content)
        else:
            # Keep unrecognized lines
            updated_lines.append(line_content)

    # Add new keys that weren't in the file
    if keys_to_add:
        updated_lines.append("")
        updated_lines.append("# Added by Config Management")
        for key in sorted(keys_to_add):
            updated_lines.append(f"{key}={updates[key]}")
            logger.info(f"Added new config: {key}")

    # Write back to file
    try:
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(updated_lines))
            if not updated_lines[-1].endswith('\n'):
                f.write('\n')
        logger.info(f"Successfully updated env file: {env_path}")

        # Remove backup file after successful update (it was just for recovery during the operation)
        if backup_path and os.path.exists(backup_path):
            try:
                os.remove(backup_path)
                logger.info(f"Removed temporary backup: {backup_path}")
            except Exception as e:
                logger.warning(f"Failed to remove backup file: {e}")

        return True, None, failures
    except Exception as e:
        logger.error(f"Failed to write env file: {e}")
        # Try to restore from backup
        try:
            shutil.copy2(backup_path, env_path)
            logger.info("Restored from backup after write failure")
        except Exception as restore_error:
            logger.error(f"Failed to restore from backup: {restore_error}")
        return False, backup_path, [{"key": k, "reason": str(e)} for k in updates.keys()]


@router.get("", response_model=Response)
async def get_configurations():
    """Get all configuration items grouped by category."""
    env_path = get_env_file_path()
    configs, _ = parse_env_file(env_path)

    # Group by category
    category_items: Dict[str, List[ConfigItem]] = {}

    for key, config_data in configs.items():
        item = create_config_item(key, config_data['value'])
        if item.category not in category_items:
            category_items[item.category] = []
        category_items[item.category].append(item)

    # Build response with ordered categories
    categories = []
    for cat_key, (cat_label, _) in CONFIG_CATEGORIES.items():
        if cat_key in category_items:
            categories.append(ConfigCategory(
                name=cat_key,
                label=cat_label,
                items=category_items[cat_key]
            ))
            del category_items[cat_key]

    # Add remaining categories
    for cat_key, items in category_items.items():
        categories.append(ConfigCategory(
            name=cat_key,
            label=cat_key.capitalize(),
            items=items
        ))

    return Response(
        code=200,
        message="success",
        data=ConfigListResponse(
            categories=categories,
            env_path=env_path,
        ),
        timestamp=datetime.utcnow(),
    )


@router.post("", response_model=Response)
async def update_configurations(request: ConfigUpdateRequest):
    """Update configuration values."""
    if not request.configs:
        raise HTTPException(status_code=400, detail="No configurations provided")

    env_path = get_env_file_path()

    # Convert list to dict
    updates = {item.key: item.value for item in request.configs}

    success, backup_path, failures = update_env_file(env_path, updates)

    if not success:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Failed to update configurations",
                "failures": failures,
                "backup_path": backup_path,
            }
        )

    updated_keys = [item.key for item in request.configs if item.key not in [f["key"] for f in failures]]

    return Response(
        code=200,
        message="Configurations updated successfully",
        data=ConfigUpdateResponse(
            updated=updated_keys,
            failed=failures,
            backup_path=backup_path,
        ),
        timestamp=datetime.utcnow(),
    )


@router.get("/reload-hint", response_model=Response)
async def get_restart_hint():
    """Get hint about which configurations require service restart."""
    return Response(
        code=200,
        message="success",
        data={
            "requires_restart": list(REQUIRES_RESTART_KEYS),
            "hint": "标有重启图标的配置项需要重启服务后才能生效",
        },
        timestamp=datetime.utcnow(),
    )
