# Enterprise Knowledge Copilot

一个用于演示企业知识问答链路的前后端项目。用户可以在聊天页面提问，后端根据当前模拟身份过滤可访问且有效的知识，再检索证据、生成带引用的回答，并记录各处理步骤的 Trace。

> 默认使用本地 Mock 模式和 SQLite 演示数据。项目中的身份切换用于演示 ACL 流程，不构成生产环境的身份认证或授权方案。

## 功能概览

- **Knowledge Chat**：问题路由、追问改写、混合检索、回答和证据引用。
- **ACL 与版本过滤**：检索前按租户、文档访问组、生效状态和有效日期筛选知识。
- **混合检索**：BM25 关键词检索与本地哈希向量检索，通过 RRF 合并，再使用规则重排。
- **多跳查询演示**：结合 Phoenix 项目文档和 HR 组织关系完成两跳查询；实现可选地使用 LangGraph。
- **Trace Explorer**：记录并查看每个处理步骤的输入、输出、状态和耗时。
- **知识治理页面**：查看文档元数据、切换演示身份、运行 Golden Case 评估和登记 Bad Case。

## 技术栈

| 部分 | 技术 |
| --- | --- |
| 前端 | React 18、TypeScript、Vite、Ant Design、React Router、Zustand、Axios、ECharts |
| 后端 | Python、FastAPI、Pydantic、SQLite、httpx、LangGraph（多跳查询可选） |
| 本地部署 | Docker Compose、Nginx |
| 可选模型服务 | DeepSeek Chat Completions API |

## 项目结构

```text
.
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI 应用、API 路由和启动初始化
│   │   ├── pipeline.py      # 问题路由与问答流程编排
│   │   ├── retrieval.py     # ACL、BM25、哈希向量、RRF、重排和上下文构造
│   │   ├── llm.py            # DeepSeek HTTP 客户端
│   │   ├── db.py             # SQLite 表结构和连接
│   │   ├── security.py       # 从请求头构造演示用身份上下文
│   │   ├── trace.py          # Trace 持久化与查询
│   │   ├── eval_service.py   # Golden Case 评估
│   │   └── seed.py           # 演示知识、组织关系和评估数据
│   ├── tests/                # 问答流水线测试
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/            # 聊天、总览、文档、Trace、评估、Bad Case、权限页面
│   │   ├── api/client.ts     # Axios 客户端和演示身份请求头
│   │   └── store/identity.ts # Zustand 身份状态
│   ├── Dockerfile
│   └── nginx.conf
├── scripts/                  # Windows 与 macOS/Linux 启动脚本
├── docker-compose.yml
└── .env.example
```

## 问答流程

```text
前端提交问题和对话历史
  → FastAPI 构造 SecurityContext
  → 规则路由：问候 / HR 查询 / 多跳查询 / 知识问答
  → Query Rewrite
  → 过滤不可访问或未生效的知识
  → BM25 与哈希向量检索
  → RRF 融合、规则重排、构造上下文
  → Mock 或 DeepSeek 生成回答
  → 返回答案、引用和 Trace
```

默认 `MOCK_MODE=true`，不会调用外部模型。将其设为 `false` 时，Query Rewrite 和回答生成会使用 DeepSeek；检索部分仍是本地确定性实现。

## 快速启动

需要安装并启动 Docker Desktop（Windows）或 Docker Engine 与 Docker Compose（macOS/Linux）。在项目根目录运行：

### Windows PowerShell

```powershell
.\scripts\start-windows.ps1
```

### macOS / Linux

```bash
./scripts/start-mac.sh
```

也可以手动启动：

```bash
cp .env.example .env
docker compose up --build -d
```

Windows PowerShell 复制配置文件可使用：

```powershell
Copy-Item .env.example .env
docker compose up --build -d
```

启动后访问：

- 前端：http://localhost:3000
- FastAPI Swagger 文档：http://localhost:8000/docs
- 后端健康检查：http://localhost:8000/health

停止服务：

```bash
docker compose down
```

数据库保存在 Docker 命名卷 `knowledge_data` 中。首次启动时，如果文档表为空，后端会初始化并载入演示数据。

## 配置

根目录 `.env.example` 中提供了可复制的配置模板：

| 变量 | 默认值 | 用途 |
| --- | --- | --- |
| `MOCK_MODE` | `true` | 使用本地 Mock；设为 `false` 才启用 DeepSeek 调用 |
| `DEEPSEEK_API_KEY` | 空 | DeepSeek API 密钥，真实模式必填 |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | DeepSeek API 地址 |
| `DEEPSEEK_MODEL` | `deepseek-v4-flash` | 使用的模型名称 |

`.env` 已加入 `.gitignore`，请勿将真实密钥提交到版本库。Compose 会把 `DATABASE_PATH` 配置到容器内的 `/app/data/knowledge.db`，并使用 `knowledge_data` 卷持久化。

## API 概览

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| `GET` | `/health` | 健康状态和运行模式 |
| `GET` | `/api/v1/runtime` | 模型及检索运行配置 |
| `POST` | `/api/v1/chat` | 企业知识问答 |
| `GET` | `/api/v1/documents` | 当前身份可见的文档元数据 |
| `GET` | `/api/v1/traces/{trace_id}` | 查询一次问答的 Trace |
| `GET` | `/api/v1/dashboard` | 获取运行总览数据 |
| `POST` | `/api/v1/eval/run` | 运行 Golden Case |
| `GET` / `POST` | `/api/v1/bad-cases` | 查询或登记 Bad Case |

聊天请求示例：

```json
{
  "question": "P6 去上海出差住宿标准是多少？",
  "history": []
}
```

请求身份通过 `x-user-id`、`x-tenant-id`、`x-user-role`、`x-user-department` 和 `x-user-groups` 请求头传递。当前这些请求头由前端模拟身份切换产生，仅用于本地演示；不能将客户端可控请求头当作生产环境的身份凭据。

## 测试

在后端目录安装依赖后运行：

```bash
cd backend
python -m pip install -r requirements.txt
python -m pytest
```

## 当前实现边界

- 向量检索通过 token 哈希构造固定维度向量，不是由 embedding 模型生成的语义向量。
- BM25、RRF 与重排均在本地实现；重排采用规则评分。
- 演示数据由 `backend/app/seed.py` 提供，首次启动后存入 SQLite。
- 当前身份来自请求头，未实现生产级登录、令牌校验或服务端身份映射。
- Mock 模式的答案由预设逻辑生成；真实模式仅在 Query Rewrite 与回答生成阶段调用 DeepSeek。
