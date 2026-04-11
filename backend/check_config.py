"""Configuration diagnostic script."""

import sys
import os

print("=" * 60)
print("Configuration Diagnostic Tool")
print("=" * 60)

# Check 1: .env file exists and readable
print("\n[1/5] Checking .env file...")
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    print(f"  [OK] .env file found: {env_path}")
    with open(env_path, 'r', encoding='utf-8') as f:
        content = f.read()
        # Check for LLM config
        has_base_url = 'LLM_BASE_URL' in content
        has_api_key = 'LLM_API_KEY' in content
        has_model = 'LLM_MODEL_NAME' in content
        print(f"  [INFO] LLM_BASE_URL defined: {has_base_url}")
        print(f"  [INFO] LLM_API_KEY defined: {has_api_key}")
        print(f"  [INFO] LLM_MODEL_NAME defined: {has_model}")
else:
    print(f"  [FAIL] .env file not found at: {env_path}")

# Check 2: Python dotenv can parse it
print("\n[2/5] Checking python-dotenv...")
try:
    from dotenv import load_dotenv, find_dotenv
    env_file = find_dotenv()
    if env_file:
        print(f"  [OK] Found .env: {env_file}")
        load_dotenv(env_file, override=True)
        print("  [OK] .env loaded successfully")
    else:
        print("  [FAIL] find_dotenv() returned None")
except Exception as e:
    print(f"  [FAIL] Error loading .env: {e}")

# Check 3: Environment variables
print("\n[3/5] Checking environment variables...")
llm_base = os.getenv('LLM_BASE_URL', 'NOT SET')
llm_key = os.getenv('LLM_API_KEY', 'NOT SET')
llm_model = os.getenv('LLM_MODEL_NAME', 'NOT SET')

print(f"  [INFO] LLM_BASE_URL: {llm_base[:50] if llm_base else 'NOT SET'}...")
print(f"  [INFO] LLM_API_KEY: {'*' * 10 if llm_key and llm_key != 'NOT SET' else 'NOT SET'}")
print(f"  [INFO] LLM_MODEL_NAME: {llm_model}")

if llm_key == 'NOT SET' or not llm_key:
    print("  [FAIL] LLM_API_KEY is not set!")
else:
    print(f"  [OK] LLM_API_KEY is set (length: {len(llm_key)})")

# Check 4: Pydantic Settings
print("\n[4/5] Checking Pydantic Settings...")
try:
    from config import settings
    print("  [OK] Settings loaded successfully")
    print(f"  [INFO] settings.LLM_BASE_URL: {settings.LLM_BASE_URL}")
    print(f"  [INFO] settings.LLM_MODEL_NAME: {settings.LLM_MODEL_NAME}")
    print(f"  [INFO] settings.LLM_API_KEY exists: {settings.LLM_API_KEY is not None}")
    if settings.LLM_API_KEY:
        print(f"  [INFO] settings.LLM_API_KEY length: {len(settings.LLM_API_KEY)}")
    else:
        print("  [FAIL] settings.LLM_API_KEY is None!")
except Exception as e:
    print(f"  [FAIL] Error loading settings: {e}")
    import traceback
    traceback.print_exc()

# Check 5: Inference Service
print("\n[5/5] Checking Inference Service...")
try:
    from app.services import inference_service
    print(f"  [INFO] inference_service.client: {inference_service.client}")
    print(f"  [INFO] inference_service.model_name: {inference_service.model_name}")
    if inference_service.client is None:
        print("  [FAIL] Inference client is None! Configuration not loaded.")
    else:
        print("  [OK] Inference client is configured")
except Exception as e:
    print(f"  [FAIL] Error checking inference service: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Diagnostic complete")
print("=" * 60)

print("\n[Troubleshooting]")
print("- If .env file not found: Create it from .env.example")
print("- If env vars not loaded: Check python-dotenv is installed")
print("- If settings.LLM_API_KEY is None: Check config.py loads from .env")
print("- If inference client is None: Check service initialization order")
