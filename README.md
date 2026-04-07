# myHelper — Daily Task Scheduler (Phase II)

基于 FastAPI + SQLite(SQLAlchemy) + APScheduler + Gotify 的任务管理系统。  
支持一次性任务、间隔任务、Cron 任务，并将到点提醒推送到手机。

---

## 1. 功能概览

- 任务类型：
  - `once`：一次性任务
  - `interval`：固定间隔任务（秒）
  - `cron`：Cron 表达式任务
- API：
  - `POST /tasks/`：创建任务
  - `GET /tasks/`：获取任务列表
  - `DELETE /tasks/{task_id}`：取消任务
- 到点后通过 Gotify 推送到手机

---

## 2. 环境要求

- Python 3.10+
- 已部署可访问的 Gotify（本机或容器）
- 推荐 Linux/macOS（Windows 也可，命令略有差异）

---

## 3. 安装与启动

```bash
cd myHelper

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate
# Windows: .venv\Scripts\activate

# 安装依赖
pip install -U pip
pip install -r requirements.txt
```

设置环境变量（至少要有 Gotify token）：

```bash
export MYHELPER_GOTIFY_URL=http://127.0.0.1:8080
export MYHELPER_GOTIFY_TOKEN=你的_gotify_app_token
export MYHELPER_DATABASE_URL=sqlite:///./myhelper.db
```

启动服务（会自动启动调度器）：

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

打开文档：
- Swagger UI: `http://127.0.0.1:8000/docs`

---

## 4. API 使用示例

### 4.1 创建一次性任务（2 分钟后）

```bash
RUN_AT=$(python3 -c "from datetime import datetime,timedelta,timezone; print((datetime.now(timezone.utc)+timedelta(minutes=2)).isoformat())")

curl -X POST "http://127.0.0.1:8000/tasks/" \
  -H "Content-Type: application/json" \
  -d "{\
    \"title\": \"两分钟后提醒\",\
    \"message\": \"这是一次性测试消息\",\
    \"task_type\": \"once\",\
    \"run_at\": \"${RUN_AT}\"\
  }"
```

### 4.2 创建 interval 周期任务（每 60 秒）

```bash
RUN_AT=$(python3 -c "from datetime import datetime,timedelta,timezone; print((datetime.now(timezone.utc)+timedelta(seconds=30)).isoformat())")

curl -X POST "http://127.0.0.1:8000/tasks/" \
  -H "Content-Type: application/json" \
  -d "{\
    \"title\": \"每分钟提醒\",\
    \"message\": \"interval 任务触发\",\
    \"task_type\": \"interval\",\
    \"run_at\": \"${RUN_AT}\",\
    \"interval_seconds\": 60\
  }"
```

### 4.3 创建 cron 周期任务（工作日 09:00，UTC）

```bash
curl -X POST "http://127.0.0.1:8000/tasks/" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "工作日提醒",
    "message": "cron 任务触发",
    "task_type": "cron",
    "run_at": "2026-04-07T09:00:00+00:00",
    "cron_expr": "0 9 * * 1-5"
  }'
```

> 当前调度器按 UTC 处理时间，建议统一传入带时区的时间。

### 4.4 查询任务列表

```bash
curl "http://127.0.0.1:8000/tasks/"
```

### 4.5 取消任务

```bash
curl -X DELETE "http://127.0.0.1:8000/tasks/1"
```

---

## 5. 测试

运行全部测试：

```bash
pytest tests/ -v
```

分步骤测试：

```bash
pytest tests/test_01_environment.py -v
pytest tests/test_02_database.py -v
pytest tests/test_03_service.py -v
pytest tests/test_04_api.py -v
pytest tests/test_05_scheduler.py -v
```

---

## 6. 手机推送联调（Gotify + Tailscale）

1. 确保 Gotify 可访问（例如 `http://<服务器IP>:8080` 或 Tailscale IP）
2. 在 Gotify Web 中创建 Application，拿到 App Token
3. 设置 `MYHELPER_GOTIFY_TOKEN`
4. 在手机 Gotify 客户端登录同一服务器
5. 创建 once 任务验证是否到点推送

---

## 7. 常见问题

### Q1: 提交代码时出现 `Author identity unknown`

先配置 git 用户信息：

```bash
git config --global user.name "你的名字"
git config --global user.email "你的邮箱"
```

### Q2: `sqlite3.OperationalError: no such table: tasks`

通常是数据库未初始化或连接指向错误；确认：
- `MYHELPER_DATABASE_URL` 正确
- 服务是通过 `app.main` 启动（会初始化表）

### Q3: 手机收不到 Gotify 推送

检查：
- Token 是否是 Application Token
- 手机客户端是否连接到同一个 Gotify 服务
- 服务器网络/Tailscale 是否可达

---

## 8. 项目结构（简要）

- `app/main.py`：FastAPI 入口 + 生命周期
- `app/api/`：路由与依赖
- `app/services/task_service.py`：任务业务逻辑
- `app/scheduler/engine.py`：调度执行引擎
- `app/integrations/gotify.py`：Gotify 推送封装
- `app/db/`：SQLAlchemy 模型与会话
- `tests/`：分阶段测试
