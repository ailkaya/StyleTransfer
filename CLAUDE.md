# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

个性化文本风格迁移系统 (Personalized Text Style Transfer System) - A web application for text style transfer using QLoRA fine-tuning.

**Architecture**: FastAPI backend + Vue 3 frontend with Celery for async training tasks.

## Common Commands

### Infrastructure
```bash
# Start PostgreSQL and Redis (required for development)
docker-compose -f docker-compose.test.yml up -d

# Stop infrastructure
docker-compose -f docker-compose.test.yml down
```

### Backend
```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run FastAPI server (terminal 1)
python main.py
# or
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Run Celery worker (terminal 2) - REQUIRED for training tasks
# Windows:
celery -A app.celery_app.tasks worker --loglevel=info --without-mingle --without-gossip -P solo

# Linux/Mac:
celery -A app.celery_app.tasks worker --loglevel=info --without-mingle --without-gossip --concurrency=2

# Diagnose Celery issues
python check_celery.py

# Run tests
pytest
```

### Frontend
```bash
cd frontend

# Install dependencies
npm install

# Run dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Lint
npm run lint
```

### Database
```bash
# Database auto-initializes on first backend startup via init_db() in main.py lifespan
# Manual schema changes: modify backend/app/models/*.py files
```

## Architecture

### Backend Structure

**Layer Organization**:
- `models/` - SQLAlchemy 2.0 async ORM models (Style, Task, Message)
- `schemas/` - Pydantic v2 request/response validation
- `routers/` - FastAPI route handlers
- `services/` - Business logic (inference.py, training.py, preprocessing.py, evaluation.py)
- `celery_app/` - Celery configuration and training tasks

**Key Data Flow - Training**:
1. Client POST `/api/tasks` creates task, sets status=PENDING, with raw training text
2. Celery task `train_style_model.delay()` dispatched
3. Preprocessing pipeline runs (clean text → extract style guide → generate 5 task type samples → format to SFT)
4. `training_service.training_progress_true()` runs QLoRA fine-tuning on formatted samples
5. Worker updates progress via `update_task_progress()` → saves to database
6. Client polls task status via GET `/api/tasks/{id}` to check progress
7. Trained adapter files saved to `./models/adapters/`

**Key Data Flow - Style Transfer**:
1. Client POST `/api/styles/{id}/messages` with source_text + requirements
2. `inference_service.transform_text()` builds prompt and calls external LLM API
3. LLM API configured via env vars (OpenAI-compatible format)
4. Response saved to Message model and returned

**Important Patterns**:
- Celery tasks use SYNC database operations (SQLAlchemy sync engine) while main app uses async
- Task.name corresponds to Style.name for display purposes

### Frontend Structure

**Key Directories**:
- `views/` - Page components (StyleTransfer.vue, StyleTraining.vue, Evaluation.vue, StyleManagement.vue)
- `stores/` - Pinia state management (style.js, task.js, message.js)
- `api/` - Axios clients per domain
- `router/` - Vue Router configuration

**Proxy Configuration** (vite.config.js):
- `/api` → `http://localhost:8000`

## Configuration

### Environment Variables (backend/.env)
Critical variables that must be set:
- `DATABASE_URL` - PostgreSQL async connection string
- `REDIS_URL` - Redis connection for Celery task queue
- `LLM_BASE_URL`, `LLM_MODEL_NAME`, `LLM_API_KEY` - External LLM API configuration
- `SYNC_DATABASE_URL` - Sync connection for Celery tasks

See `backend/.env.example` for full template.

## Important Implementation Notes

### Mock vs Real Implementation
Core features have both mock (simulated) and real implementations, toggled via environment variables:
- **Training**: `training_service.simulate_training_progress()` (mock) vs `training_progress_true()` (real QLoRA). Controlled by `GENERATING_MOCK_MODE`
- **Inference**: `generate_style_transfer_mock()` (external API) vs `generate_style_transfer_true()` (local LoRA with PEFT). Controlled by `GENERATING_MOCK_MODE`
- **Evaluation**: `generate_evaluation_data_mock()` (random metrics) vs `generate_evaluation_data_true()` (BLEU, BERTScore, style match, fluency). Controlled by `EVALUATION_MOCK_MODE`

When mock modes are disabled, the system performs actual QLoRA fine-tuning, local model inference, and real metric calculation.

### Preprocessing Pipeline
`preprocessing.py` is a key module for training data preparation:
- **Step 1-2**: Semantic chunking → LLM-based text cleaning
- **Step 2.5**: Style feature extraction (samples chunks, LLM generates `style_guide.md`)
- **Step 2.6**: Keyword extraction from `cleaned_text` (jieba + preset `keyword_library.json`)
- **Step 3-5**: Sentence split → Generate 5 task types:
  - **Continuation**: chunk[i] → chunk[i+1] (direct, no LLM)
  - **Generation/Explanation/Summarization**: LLM-driven with `style_guide`
  - **Style Transfer**: neutral → styled via LLM with `style_guide`
- All 4 LLM-intensive tasks run in parallel via `asyncio.gather()` with Rich progress bars

### Celery Worker Requirements
Training tasks will hang at PENDING state if Celery worker is not running. Always ensure worker is started in a separate terminal.

### Database Migrations
No migration tool configured (Alembic not set up). Schema changes require:
1. Modify model in `backend/app/models/`
2. Manually alter database or recreate tables
3. SQLAlchemy auto-creates tables on startup if they don't exist

### Windows Compatibility
Celery must use `-P solo` pool on Windows due to lack of fork() support.
