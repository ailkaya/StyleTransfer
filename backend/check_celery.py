"""Celery diagnostic script."""

import os
import sys
import time

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("Celery Diagnostic Tool")
print("=" * 60)

# Check 1: Redis connection
print("\n[1/5] Checking Redis connection...")
try:
    import redis
    redis_client = redis.Redis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        decode_responses=True,
        socket_connect_timeout=5,
    )
    start = time.time()
    redis_client.ping()
    elapsed = time.time() - start
    print(f"  [OK] Redis connected in {elapsed:.3f}s")

    # Check for pending tasks
    pending_count = redis_client.llen("celery")
    print(f"  [INFO] Pending tasks in queue: {pending_count}")

except Exception as e:
    print(f"  [FAIL] Redis connection failed: {e}")
    sys.exit(1)

# Check 2: Database connection
print("\n[2/5] Checking Database connection...")
try:
    from sqlalchemy import create_engine
    SYNC_DATABASE_URL = os.getenv(
        "SYNC_DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/style_transfer"
    )
    start = time.time()
    engine = create_engine(SYNC_DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute("SELECT 1")
    elapsed = time.time() - start
    print(f"  [OK] Database connected in {elapsed:.3f}s")
except Exception as e:
    print(f"  [FAIL] Database connection failed: {e}")

# Check 3: Celery app import
print("\n[3/5] Checking Celery app...")
try:
    start = time.time()
    from app.celery_app.tasks import celery_app, train_style_model
    elapsed = time.time() - start
    print(f"  [OK] Celery app imported in {elapsed:.3f}s")
    print(f"  [INFO] Broker URL: {celery_app.conf.broker_url}")
    print(f"  [INFO] Registered tasks: {list(celery_app.tasks.keys())[:5]}")
except Exception as e:
    print(f"  [FAIL] Celery import failed: {e}")
    import traceback
    traceback.print_exc()

# Check 4: Inspect Celery workers
print("\n[4/5] Checking Celery workers...")
try:
    from celery.app.control import Inspect
    inspect = Inspect(app=celery_app)

    start = time.time()
    stats = inspect.stats()
    elapsed = time.time() - start

    if stats:
        print(f"  [OK] Workers found in {elapsed:.3f}s:")
        for worker_name, worker_stats in stats.items():
            print(f"    - {worker_name}")
            print(f"      Processes: {worker_stats.get('pool', {}).get('max-concurrency', 'N/A')}")
            print(f"      Tasks processed: {worker_stats.get('total', {}).get('tasks', 'N/A')}")
    else:
        print(f"  [FAIL] No Celery workers running!")
        print(f"  [INFO] Start worker with: celery -A app.celery_app.tasks worker --loglevel=info")

    # Check active tasks
    active = inspect.active()
    if active:
        print(f"  [INFO] Active tasks: {sum(len(t) for t in active.values())}")

    scheduled = inspect.scheduled()
    if scheduled:
        print(f"  [INFO] Scheduled tasks: {sum(len(t) for t in scheduled.values())}")

except Exception as e:
    print(f"  [FAIL] Worker inspection failed: {e}")

# Check 5: Task ping test
print("\n[5/5] Testing task dispatch...")
try:
    from app.celery_app.tasks import publish_progress_update
    start = time.time()
    # Try to publish a test message
    test_result = publish_progress_update("test-task-id", {"status": "TEST", "progress": 0})
    elapsed = time.time() - start
    print(f"  [OK] Test message published in {elapsed:.3f}s")
except Exception as e:
    print(f"  [FAIL] Test publish failed: {e}")

print("\n" + "=" * 60)
print("Diagnostic complete")
print("=" * 60)

# Summary
print("\nSummary:")
print("- If workers not found: Start Celery worker")
print("- If tasks pending: Workers may be stuck or not processing")
print("- If Redis slow: Check Redis server load")
