"""Celery configuration."""

# Use socket connection for faster startup on Windows
broker_url = "redis://localhost:6379/0"
result_backend = "redis://localhost:6379/0"

# Redis connection settings - aggressive timeouts to prevent blocking
broker_connection_timeout = 2
broker_connection_retry = True
broker_connection_max_retries = 1
broker_connection_retry_on_startup = False
broker_pool_limit = 5
broker_transport_options = {
    'visibility_timeout': 7200,
    'queue_order_strategy': 'priority',
    'socket_connect_timeout': 2,
    'socket_timeout': 2,
}

# Connection pool settings - reduced to prevent connection overhead
broker_pool_limit = 5
result_backend_max_connections = 5

task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]

timezone = "UTC"
enable_utc = True

# Task settings
task_track_started = True
task_time_limit = 3600  # 1 hour max
task_acks_late = True  # Acknowledge after task completes, not before
task_ignore_result = False

# Worker settings
worker_prefetch_multiplier = 1
worker_concurrency = 2  # Number of concurrent workers
worker_max_tasks_per_child = 100  # Restart worker after 100 tasks

# Disable features that slow down startup (single worker setup)
worker_hijack_root_logger = False  # Don't hijack root logger

# Additional settings to disable mingle completely
broker_heartbeat = 0  # Disable heartbeat to speed up connection
task_send_sent_event = False  # Don't send sent events
worker_send_task_events = False  # Don't send task events
worker_state_db = None  # Don't persist worker state

# Result settings
result_expires = 86400  # Results expire after 24 hours
result_extended = True
