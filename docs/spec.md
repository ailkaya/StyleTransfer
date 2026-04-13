# 个性化文本风格迁移系统 - 技术规范文档

**版本**: v0.1  
**日期**: 2026-04-11  
**状态**: 草案  

---

## 1. 概述

### 1.1 项目愿景
构建一个轻量化的个性化文本风格迁移系统，验证 QLoRA 技术在降低大模型微调门槛、实现可控文本风格转换方面的可行性，为智能写作辅助、内容风格适配等场景提供解决方案。

### 1.2 核心价值主张
1. **低成本**：利用 QLoRA 技术在消费级 GPU 上完成微调
2. **个性化**：支持用户自定义目标风格，仅需少量样本（1-5万字）
3. **易用性**：Web 界面管理风格、执行转换、监控训练进度
4. **可扩展**：模块化架构，预留模型评估和迭代优化接口

---

## 2. 功能规格

### 2.1 功能清单（MoSCoW 优先级）

| 功能模块 | 功能点 | 优先级 | 备注 |
|---------|--------|--------|------|
| **风格转化** | AI对话式交互界面 | Must | 核心功能 |
| | 多风格历史记录管理 | Must | 每个风格独立历史 |
| | 双输入框设计（原文+需求） | Must | 需求定义 |
| **风格迁移模型训练** | 训练参数配置 | Must | 可视化配置界面 |
| | 底座模型选择 | Must | 支持初始模型/带Adapter模型 |
| | 示例文本上传与分割 | Must | 支持1-5万字 |
| | 训练进度实时监控 | Must | WebSocket推送 |
| | 实际QLoRA训练逻辑 | **Won't** | v0.1输出示例模型文件 |
| **生成结果可视化** | 评估结果API接口 | Must | 预留接口 |
| | 评估界面渲染 | Should | 返回简单替代界面 |
| | 自动评估指标计算 | **Won't** | v0.1版本暂不做 |
| **风格管理** | 风格列表查看 | Must | 屏蔽底座模型细节 |
| | 风格信息编辑 | Must | 元数据管理 |
| | 风格删除 | Must | 含确认机制 |
| **系统功能** | 左导航栏布局 | Must | UI要求 |
| | 免注册/登录 | Must | 简化用户使用 |
| | Docker测试环境 | Must | docker-compose.test.yml |
| | 大模型API配置 | Must | OpenAI格式兼容 |

### 2.2 用户故事与验收标准

#### US-001: 风格转化 - 执行风格转换
**作为**内容创作者，**我希望**通过对话界面将文本转换为特定风格，**以便**快速生成符合目标风格的内容。

**验收标准**:
```gherkin
Given 用户已选择一个目标风格
And 系统已加载该风格的历史记录
When 用户在第一输入框输入原文（或上传文件预览部分内容）
And 用户在第二输入框输入具体需求
And 用户点击"转换"按钮
Then 系统调用配置的大模型API
And 返回风格转换后的文本
And 将该对话添加到当前风格的历史记录中

Given 用户正在查看风格转化界面
When 页面加载完成
Then 显示当前可选择的所有目标风格列表
And 不同风格拥有独立的历史记录会话
```

**验证标准**:
- [ ] 输入框支持多行文本，原文框显示内容前20字符（可展开）
- [ ] API响应时间 < 30秒（超时显示友好提示）
- [ ] 历史记录按时间倒序排列，支持点击查看详情

---

#### US-002: 风格迁移模型训练 - 创建新风格
**作为**用户，**我希望**通过上传示例文本创建自定义风格，**以便**获得个性化的风格转换能力。

**验收标准**:
```gherkin
Given 用户进入"风格迁移模型训练"界面
When 用户填写风格名称、描述、目标风格
And 用户选择底座模型（LLaMA-2/3B或ChatGLM3-6B或带Adapter的模型）
And 用户上传或输入示例文本（目标风格，1-5万字）
And 用户配置训练参数（学习率、轮数、batch size等）
And 用户点击"开始训练"
Then 系统将上传的文本进行分块处理
And 创建Celery异步训练任务
And 返回任务ID用于进度追踪
And 生成示例模型文件作为输出
```

**验证标准**:
- [ ] 文本上传支持 .txt, .md, .docx 格式，大小限制 10MB
- [ ] 文本自动分块：每块512 tokens，重叠128 tokens
- [ ] 训练参数默认值：学习率 2e-4，轮数 3，batch size 4
- [ ] 任务状态：PENDING -> PROCESSING -> COMPLETED/FAILED

---

#### US-003: 训练进度监控 - 实时查看训练状态
**作为**用户，**我希望**实时查看模型训练进度，**以便**了解训练状态和预计完成时间。

**验收标准**:
```gherkin
Given 用户已提交一个训练任务
When 训练任务开始执行
Then 系统通过 WebSocket 向前端推送训练进度
And 前端显示当前epoch、loss值、已用时间、预计剩余时间
And 显示训练日志的最后10行

Given 训练任务已完成
When 进度达到100%
Then 系统推送完成通知
And 更新风格列表，新风格状态变为"可用"
```

**验证标准**:
- [ ] WebSocket连接断线后5秒内自动重连
- [ ] 进度更新频率：每5秒或每完成一个epoch
- [ ] 支持查看历史任务的训练日志

---

#### US-004: 生成结果可视化 - 查看评估报告
**作为**用户，**我希望**查看风格转换效果的评估结果，**以便**了解模型质量。

**验收标准**:
```gherkin
Given 用户进入"生成结果可视化"界面
When 用户选择某个已完成的训练任务
And 点击"查看评估报告"
Then 后端返回简单的HTML替代界面
And 前端渲染显示该界面
And 界面包含占位文本"评估功能将在后续版本开放"
```

**验证标准**:
- [ ] API返回完整HTML文档，前端通过 iframe 或 v-html 渲染
- [ ] 界面响应时间 < 2秒

---

#### US-005: 风格管理 - 管理已有风格
**作为**用户，**我希望**查看和管理所有已创建的风格，**以便**维护风格库。

**验收标准**:
```gherkin
Given 用户进入"风格管理"界面
When 页面加载完成
Then 显示所有风格的卡片列表
And 每张卡片显示：风格名称、描述、创建时间、状态
And 底座模型细节对用户不可见

Given 用户点击某个风格的"编辑"按钮
When 编辑表单加载完成
Then 显示可编辑字段：名称、描述、目标风格
And 底座模型信息只读显示
And 用户保存后更新风格信息

Given 用户点击"删除"按钮
When 系统弹出确认对话框
And 用户确认删除
Then 从数据库中删除该风格记录
And 清理关联的历史记录
And 显示删除成功提示
```

**验证标准**:
- [ ] 风格列表支持分页，每页10条
- [ ] 支持按名称搜索过滤
- [ ] 删除操作需要二次确认，防止误操作
- [ ] 正在训练中的风格不允许删除

---

#### US-006: 系统配置 - 配置大模型API
**作为**管理员，**我希望**配置外部大模型API参数，**以便**系统能调用外部模型服务。

**验收标准**:
```gherkin
Given 系统管理员访问配置文件或管理界面
When 配置以下参数：
  - base_url: API基础URL
  - model_name: 模型名称
  - api_key: API密钥
Then 系统保存配置并验证连接
And "风格转化"功能调用该API进行文本转换
```

**验证标准**:
- [ ] API配置支持环境变量或配置文件方式
- [ ] 配置变更后无需重启服务即可生效
- [ ] API调用失败时记录详细错误日志

---

## 3. 非功能需求

### 3.1 性能需求
无

### 3.2 安全需求

| 需求 | 优先级 | 验证标准 |
|------|--------|----------|
| API密钥不在前端暴露 | Must | 密钥仅存储于后端环境变量 |
| 文件上传类型限制 | Must | 仅允许 .txt, .md, .docx |
| 文件上传大小限制 | Must | 单文件最大 10MB |
| SQL注入防护 | Must | 使用 ORM 参数化查询 |
| XSS防护 | Must | 输入过滤+输出转义 |

### 3.3 可扩展性需求

| 需求 | 优先级 | 说明 |
|------|--------|------|
| 支持新底座模型接入 | Should | 模型配置化，无需修改核心业务代码 |
| 支持多种评估指标扩展 | Should | 评估模块插件化设计 |
| 水平扩展能力 | Could | 支持多Worker节点部署 |

### 3.4 可用性需求

| 需求 | 优先级 | 验证标准 |
|------|--------|----------|
| 浏览器兼容性 | Must | Chrome 90+, Firefox 88+, Edge 90+ |
| 响应式设计 | Should | 支持1280x768及以上分辨率 |
| 离线任务状态保持 | Must | 刷新页面后任务状态不丢失 |

---

## 4. 数据模型

### 4.1 ER 关系图

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│    Style    │       │    Task     │       │   Message   │
│   (风格)     │◄──────│  (训练任务)  │       │  (历史消息)  │
├─────────────┤       ├─────────────┤       ├─────────────┤
│ id (PK)     │       │ id (PK)     │       │ id (PK)     │
│ name        │       │ style_id(FK)│       │ style_id(FK)│
│ description │       │ status      │       │ role        │
│ source_style│       │ progress    │       │ content     │
│ target_style│       │ config      │       │ created_at  │
│ base_model  │       │ logs        │       └─────────────┘
│ status      │       │ created_at  │
│ created_at  │       │ updated_at  │
│ updated_at  │       └─────────────┘
└─────────────┘
```

### 4.2 实体定义

#### Style（风格）
```yaml
Style:
  id: UUID          # 主键，系统自动生成
  name: String      # 风格名称，唯一，2-50字符
  description: Text # 风格描述，可选，最大500字符
  target_style: String  # 目标风格类型，如"幽默"、"学术"
  base_model: String    # 底座模型标识，如"llama-2-3b"
  adapter_path: String  # Adapter路径（训练后填充）
  status: Enum      # 状态: pending/training/completed/failed
  created_at: DateTime
  updated_at: DateTime
```

#### Task（训练任务）
```yaml
Task:
  id: UUID          # 主键
  style_id: UUID    # 外键 -> Style.id
  status: Enum      # PENDING/PROCESSING/COMPLETED/FAILED
  progress: Integer # 进度百分比 0-100
  config: JSON      # 训练配置参数
  logs: Text        # 训练日志
  result_path: String  # 输出模型路径
  error_message: Text  # 错误信息（失败时）
  created_at: DateTime
  updated_at: DateTime
  completed_at: DateTime
```

#### Message（历史消息）
```yaml
Message:
  id: UUID          # 主键
  style_id: UUID    # 外键 -> Style.id
  role: Enum        # user/assistant/system
  content: Text     # 消息内容
  metadata: JSON    # 额外元数据（如原文、需求拆分）
  created_at: DateTime
```

#### Config（系统配置）
```yaml
Config:
  key: String       # 配置键，主键
  value: Text       # 配置值
  description: String   # 配置说明
  updated_at: DateTime
```

### 4.3 数据约束

1. **唯一约束**: Style.name 全局唯一
2. **外键约束**: Task.style_id 级联删除，Message.style_id 级联删除
3. **状态流转**: pending → processing → completed/failed
4. **数据保留**: 已完成任务保留30天日志，消息记录保留100条/风格

---

## 5. 接口契约

### 5.1 API 概览

| 模块 | 端点 | 方法 | 描述 |
|------|------|------|------|
| 风格 | /api/styles | GET/POST | 列表/创建 |
| 风格 | /api/styles/{id} | GET/PUT/DELETE | 详情/更新/删除 |
| 任务 | /api/tasks | GET/POST | 列表/创建训练任务 |
| 任务 | /api/tasks/{id} | GET | 任务详情 |
| 任务 | /api/tasks/{id}/logs | GET | 获取训练日志 |
| 消息 | /api/styles/{id}/messages | GET/POST | 历史/发送消息 |
| 评估 | /api/tasks/{id}/evaluation | GET | 获取评估HTML |
| 配置 | /api/config/llm | GET/PUT | LLM配置管理 |
| WebSocket | /ws/tasks/{id} | WS | 训练进度推送 |

### 5.2 标准响应格式

```json
{
  "code": 200,
  "message": "success",
  "data": { ... },
  "timestamp": "2026-04-11T10:30:00Z"
}
```

### 5.3 错误码定义

| 错误码 | 含义 | HTTP状态码 | 场景 |
|--------|------|-----------|------|
| 200 | 成功 | 200 | 正常响应 |
| 400 | 请求参数错误 | 400 | 参数缺失/格式错误 |
| 401 | 未授权 | 401 | API密钥无效 |
| 404 | 资源不存在 | 404 | 风格/任务ID不存在 |
| 409 | 资源冲突 | 409 | 名称重复 |
| 422 | 业务逻辑错误 | 422 | 状态不允许此操作 |
| 429 | 请求过于频繁 | 429 | 限流触发 |
| 500 | 服务器内部错误 | 500 | 未预期异常 |
| 502 | 外部服务错误 | 502 | 大模型API调用失败 |

### 5.4 详细接口定义

#### POST /api/styles
创建新风格

**Request**:
```json
{
  "name": "幽默风格",
  "description": "转换为幽默风格",
  "source_style": "正式",
  "target_style": "幽默"
}
```

**Response**:
```json
{
  "code": 200,
  "data": {
    "id": "uuid",
    "name": "幽默风格",
    "description": "...",
    "status": "pending",
    "created_at": "2026-04-11T10:30:00Z"
  }
}
```

#### POST /api/tasks
创建训练任务

**Request**:
```json
{
  "style_id": "uuid",
  "base_model": "llama-2-3b",
  "training_text": "文本内容...",
  "config": {
    "learning_rate": 0.0002,
    "num_epochs": 3,
    "batch_size": 4,
    "max_length": 512
  }
}
```

**Response**:
```json
{
  "code": 200,
  "data": {
    "id": "task-uuid",
    "style_id": "uuid",
    "status": "PENDING",
    "progress": 0,
    "created_at": "2026-04-11T10:30:00Z"
  }
}
```

#### GET /api/tasks/{id}
获取任务详情

**Response**:
```json
{
  "code": 200,
  "data": {
    "id": "task-uuid",
    "style_id": "uuid",
    "status": "PROCESSING",
    "progress": 45,
    "config": { ... },
    "logs": "Epoch 1/3: loss=0.523...",
    "created_at": "...",
    "updated_at": "..."
  }
}
```

#### POST /api/styles/{id}/messages
发送风格转换消息

**Request**:
```json
{
  "original_text": "这是一段正式的文本内容...",
  "requirement": "请转换为幽默风格，保持原意",
  "history": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}
```

**Response**:
```json
{
  "code": 200,
  "data": {
    "id": "msg-uuid",
    "role": "assistant",
    "content": "转换后的幽默风格文本...",
    "metadata": {
      "original_text": "...",
      "requirement": "..."
    },
    "created_at": "2026-04-11T10:30:00Z"
  }
}
```

#### GET /api/tasks/{id}/evaluation
获取评估HTML

**Response**:
```html
<!DOCTYPE html>
<html>
<head><title>评估报告</title></head>
<body>
  <h1>风格迁移评估</h1>
  <p>评估功能将在后续版本开放</p>
  <p>任务ID: {task_id}</p>
</body>
</html>
```

Content-Type: text/html

#### WebSocket /ws/tasks/{id}
训练进度实时推送

**Message Format**:
```json
{
  "type": "progress",
  "data": {
    "task_id": "uuid",
    "status": "PROCESSING",
    "progress": 45,
    "current_epoch": 2,
    "total_epochs": 3,
    "current_loss": 0.423,
    "elapsed_time": 120,
    "estimated_remaining": 180,
    "log_lines": ["...", "..."]
  },
  "timestamp": "2026-04-11T10:30:00Z"
}
```

---

## 6. 技术栈约束

### 6.1 前端

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue.js | ^3.3.x | 框架 |
| Vue Router | ^4.2.x | 路由 |
| Pinia | ^2.1.x | 状态管理 |
| Element Plus | ^2.4.x | UI组件库 |
| Axios | ^1.6.x | HTTP客户端 |
| Markdown-it | ^14.x | Markdown渲染 |

**代码规范**:
- ESLint + Prettier 统一代码风格
- Vue3 Composition API 风格
- 组件命名 PascalCase
- Props 必须定义类型和默认值

### 6.2 后端

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.10+ | 运行时 |
| FastAPI | ^0.104.x | Web框架 |
| Uvicorn | ^0.24.x | ASGI服务器 |
| SQLAlchemy | ^2.0.x | ORM |
| Pydantic | ^2.5.x | 数据验证 |
| Celery | ^5.3.x | 异步任务队列 |
| Redis | ^7.x | 消息代理/缓存 |
| PostgreSQL | ^15.x | 主数据库 |
| Websockets | ^12.x | WebSocket支持 |
| OpenAI SDK | ^1.x | 大模型API调用 |

**代码规范**:
- PEP 8 编码规范
- Black 代码格式化
- isort 导入排序
- mypy 类型检查
- pytest 单元测试

### 6.3 部署与运维

| 技术 | 版本 | 用途 |
|------|------|------|
| Docker | 24.x+ | 容器化 |
| Docker Compose | 2.x+ | 编排 |
| Nginx | 1.24+ | 反向代理 |

### 6.4 待实现占位清单

根据需求，以下模块在 v0.1 版本中需要留空或替换，需记录在 `TODO_IMPLEMENTATION.md` 文件中：

| 序号 | 模块 | 文件位置 | 说明 |
|------|------|----------|------|
| 1 | 本地模型推理 | `backend/services/inference.py` | 替换为API调用 |
| 2 | QLoRA训练逻辑 | `backend/services/training.py` | 留空，输出示例模型文件 |
| 3 | 评估指标计算 | `backend/services/evaluation.py` | 留空，返回占位HTML |
| 4 | 文本预处理 | `backend/services/preprocessing.py` | 实现文本分块，其他留空 |

---

## 7. 质量标准

### 7.1 代码覆盖率

| 类型 | 目标 | 说明 |
|------|------|------|
| 单元测试覆盖率 | >= 70% | 核心业务逻辑 |
| 集成测试覆盖率 | >= 50% | API接口测试 |
| E2E测试 | 核心流程 | 风格创建→训练→转换 |

### 7.2 Lint 规则

**前端 (ESLint + Prettier)**:
```json
{
  "extends": [
    "@vue/eslint-config-typescript",
    "@vue/eslint-config-prettier"
  ],
  "rules": {
    "vue/multi-word-component-names": "off",
    "@typescript-eslint/no-explicit-any": "warn"
  }
}
```

**后端 (Flake8 + Black)**:
```ini
[flake8]
max-line-length = 100
exclude = .git,__pycache__,venv,migrations
ignore = E203,W503

[black]
line-length = 100
target-version = ['py310']
```

### 7.3 测试策略

| 测试类型 | 工具 | 范围 | 触发时机 |
|----------|------|------|----------|
| 单元测试 | pytest/jest | 服务函数、工具类 | 每次提交 |
| 集成测试 | pytest/httpx | API端点 | PR合并前 |
| E2E测试 | Cypress/Playwright | 完整用户流程 | 发布前 |
| 性能测试 | k6 | API响应时间 | 版本发布前 |

### 7.4 文档要求

| 文档类型 | 要求 | 存放位置 |
|----------|------|----------|
| API文档 | 自动生成 | `/docs` (Swagger UI) |
| 代码注释 | 复杂逻辑必须注释 | 源码内 |
| 部署文档 | 步骤清晰 | `DEPLOYMENT.md` |
| 开发指南 | 环境搭建、开发流程 | `DEVELOPMENT.md` |

---

## 8. 附录

### 8.1 术语表

| 术语 | 说明 |
|------|------|
| QLoRA | Quantized Low-Rank Adaptation，量化低秩适配微调技术 |
| Adapter | 适配器，轻量级微调模块 |
| Celery | Python分布式任务队列 |
| WebSocket | 全双工通信协议，用于实时推送 |

### 8.2 相关文档索引

- `requ.md` - 原始需求文档
- `TODO_IMPLEMENTATION.md` - 待实现/替换代码清单
- `DEPLOYMENT.md` - 部署指南（待创建）
- `DEVELOPMENT.md` - 开发指南（待创建）

### 8.3 修订历史

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|----------|------|
| 0.1 | 2026-04-11 | 初始版本 | Claude |

---

**文档结束**
