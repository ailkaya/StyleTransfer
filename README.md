# 个性化文本风格迁移系统

基于 QLoRA 高效微调技术的个性化文本风格迁移原型系统。

## 项目概述

本系统允许用户自定义目标风格，并上传或输入少量示例文本（1-5万字），利用开源大语言模型作为基座，采用 QLoRA 技术对模型进行轻量化微调，实现对输入文本的风格转换。

## v0.1 版本特性

- **风格转化**: AI对话式交互界面，支持双输入框（原文+需求）
- **风格迁移训练**: 创建自定义风格，配置训练参数，实时监控训练进度
- **生成结果可视化**: 预留评估接口，返回占位HTML界面
- **风格管理**: 查看、编辑、删除风格
- **系统配置**: 配置OpenAI格式的大模型API

## 技术栈

### 前端
- Vue 3 + Composition API
- Element Plus 2.4.x
- Pinia 状态管理
- Vue Router 4.x
- Axios HTTP客户端

### 后端
- FastAPI 0.104.x
- SQLAlchemy 2.0.x (异步ORM)
- Pydantic 2.5.x 数据验证
- Celery 5.3.x + Redis (异步任务队列)
- PostgreSQL 15.x (主数据库)
- WebSocket (实时进度推送)

### 基础设施
- Docker & Docker Compose
- Redis (消息代理/缓存)

## 项目结构

```
codesv2/
├── backend/                    # FastAPI 后端
│   ├── app/
│   │   ├── models/            # SQLAlchemy 数据模型
│   │   ├── schemas/           # Pydantic 数据验证
│   │   ├── services/          # 业务服务
│   │   ├── routers/           # API路由
│   │   ├── celery_app/        # Celery配置和任务
│   │   ├── websocket/         # WebSocket实现
│   │   └── utils/             # 工具函数(日志等)
│   ├── main.py                # FastAPI入口
│   ├── config.py              # 全局配置
│   ├── check_celery.py        # Celery诊断工具
│   └── requirements.txt       # Python依赖
├── frontend/                   # Vue3 前端
│   ├── src/
│   │   ├── api/               # API客户端
│   │   ├── components/        # Vue组件
│   │   ├── router/            # 路由配置
│   │   ├── stores/            # Pinia状态管理
│   │   └── views/             # 页面视图
│   ├── package.json
│   └── vite.config.js
├── docker-compose.test.yml    # Docker测试环境
├── spec.md                    # 技术规范文档
├── requ.md                    # 需求文档
└── TODO_IMPLEMENTATION.md     # 待实现清单
```

## 快速开始

### 环境要求

- Python >= 3.10
- Node.js >= 18
- PostgreSQL >= 15
- Redis >= 7.0
- Docker & Docker Compose (可选)

### 1. 启动基础设施

#### 方式一: 使用 Docker (推荐)

```bash
# 启动 PostgreSQL 和 Redis
docker-compose -f docker-compose.test.yml up -d

# 查看状态
docker-compose -f docker-compose.test.yml ps
```

#### 方式二: 使用本地服务

确保本地已安装并启动 PostgreSQL 和 Redis。

### 2. 配置环境变量

```bash
cd backend
cp .env.example .env

# 编辑 .env 文件，配置以下关键参数:
# - DATABASE_URL: PostgreSQL连接URL
# - REDIS_URL: Redis连接URL
# - LLM_BASE_URL: 大模型API基础URL
# - LLM_MODEL_NAME: 模型名称
# - LLM_API_KEY: API密钥
# - LOG_LEVEL: 日志级别 (DEBUG/INFO/WARNING/ERROR)
```

### 3. 安装后端依赖

```bash
cd backend

# 创建虚拟环境 (推荐)
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 4. 启动后端服务

**需要同时启动两个服务:**

#### 终端 1: FastAPI 主服务

```bash
cd backend

# 开发模式 (热重载)
python main.py

# 或使用 uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

后端服务将运行在 http://localhost:8000
- API文档: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

#### 终端 2: Celery Worker (必须)

```bash
cd backend

# Windows (单进程模式，避免fork问题)
celery -A app.celery_app.tasks worker --loglevel=info --without-mingle --without-gossip -P solo

# Linux/Mac (多进程模式)
celery -A app.celery_app.tasks worker --loglevel=info --without-mingle --without-gossip --concurrency=2
```

**⚠️ 重要**: 如果不启动 Celery Worker，训练任务将一直处于"等待中"状态！

### 5. 安装并启动前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端服务将运行在 http://localhost:3000

## 配置大模型API

系统支持 OpenAI 格式的 API。可以通过以下方式配置：

### 1. 环境变量方式

```bash
# backend/.env
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-3.5-turbo
LLM_API_KEY=sk-your-api-key
LLM_TIMEOUT=60
```

### 2. Web界面配置

访问 http://localhost:3000/config 进行配置。

**支持的API服务商:**
- OpenAI
- Azure OpenAI
- DeepSeek
- 本地 vLLM/Text Generation Inference
- 其他 OpenAI 兼容服务

## 主要功能说明

### 风格转化
1. 左侧导航栏选择目标风格
2. 上方输入框输入原文（支持文件上传）
3. 下方输入框输入转换需求
4. 点击转换获取结果

### 风格训练
1. 填写风格名称、描述和目标风格
2. 选择底座模型（LLaMA-2-3B 或 ChatGLM3-6B）
3. 上传或输入示例文本（最少100字符，推荐1万-5万字）
4. 配置训练参数
5. 点击"开始训练"
6. 实时监控训练进度（WebSocket推送）

**注意**: v0.1版本训练是模拟的，实际QLoRA训练将在v0.2+实现。

### 风格管理
- 查看所有风格卡片
- 编辑风格信息（名称、描述、目标风格）
- 删除风格（训练中风格不可删除）
- 支持搜索和分页

## 调试与日志

### 查看日志

后端日志同时输出到控制台和文件（如果配置了 `LOG_FILE`）：

```bash
# 实时查看日志
tail -f backend/logs/app.log

# Windows
Get-Content backend/logs/app.log -Wait
```

### 日志级别

在 `.env` 中设置 `LOG_LEVEL`:
- `DEBUG`: 显示所有日志，包括SQL查询、请求详情
- `INFO`: 显示常规操作日志（推荐开发使用）
- `WARNING`: 仅显示警告和错误
- `ERROR`: 仅显示错误

### Celery诊断

如果训练任务长时间没有响应，运行诊断工具：

```bash
cd backend
python check_celery.py
```

诊断工具会检查：
- Redis连接状态
- 数据库连接状态
- Celery Worker是否运行
- 队列中堆积的任务数

## 常见问题

### Q: 点击"开始训练"后一直显示"训练中"

**原因**: Celery Worker 没有运行。

**解决**:
```bash
# 确保已启动 Worker
celery -A app.celery_app.tasks worker --loglevel=info -P solo
```

### Q: Celery任务启动很慢（>10秒）

**原因**: Redis连接超时。

**解决**: 检查 Redis 是否运行，或在 `celeryconfig.py` 中调整超时设置。

### Q: 前端无法连接后端API

**检查清单**:
1. 后端服务是否运行在 http://localhost:8000
2. CORS配置是否正确（`config.py` 中的 `CORS_ORIGINS`）
3. 前端 `vite.config.js` 中的代理配置是否正确

### Q: WebSocket不推送进度更新

**原因**: 
1. Celery Worker没有运行
2. Redis连接问题

**解决**:
1. 检查 Worker 状态: `python check_celery.py`
2. 确保 Worker 和主服务使用同一个 Redis 实例

### Q: 数据库连接错误

**解决**:
```bash
# 确保PostgreSQL已启动
# 检查数据库是否存在
createdb style_transfer

# 或让SQLAlchemy自动创建表（首次运行时会自动创建）
```

## 开发指南

### 后端开发

```bash
cd backend

# 代码格式化
black .
isort .

# 类型检查
mypy .

# 运行测试
pytest
```

### 前端开发

```bash
cd frontend

# 代码检查
npm run lint

# 构建
npm run build

# 预览生产构建
npm run preview
```

### API测试

启动后端后，访问 http://localhost:8000/docs 使用 Swagger UI 测试API。

## 已知限制 (v0.1)

根据需求文档，以下功能在 v0.1 中为占位实现：

1. **本地模型推理**: 当前调用外部API进行风格转换，本地模型推理框架留空
2. **QLoRA训练**: 实际训练逻辑留空，仅模拟进度，生成示例模型文件
3. **评估指标**: 自动评估指标计算留空，返回占位HTML界面

详见 `TODO_IMPLEMENTATION.md` 了解后续版本迭代计划。

## API 文档

启动后端后访问: http://localhost:8000/docs

主要API端点:

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/styles` | GET/POST | 风格列表/创建 |
| `/api/styles/{id}` | GET/PUT/DELETE | 风格详情/更新/删除 |
| `/api/tasks` | GET/POST | 任务列表/创建训练任务 |
| `/api/tasks/{id}` | GET | 任务详情 |
| `/api/tasks/{id}/logs` | GET | 训练日志 |
| `/api/styles/{id}/messages` | GET/POST | 历史消息/发送消息 |
| `/api/tasks/{id}/evaluation` | GET | 评估报告HTML |
| `/api/config/llm` | GET/PUT | LLM配置管理 |
| `/ws/tasks/{id}` | WS | WebSocket训练进度 |

## 文档

- [需求文档](requ.md) - 项目需求说明
- [技术规范](spec.md) - API规范、数据模型、接口契约
- [待实现清单](TODO_IMPLEMENTATION.md) - 后续版本迭代计划

## 许可证

MIT
