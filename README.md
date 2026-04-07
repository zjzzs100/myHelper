# myHelper — Phase II

分步开发，每步有对应测试（见 `tests/test_0*.py`）。

## Step 1 — 环境与依赖

```bash
cd myHelper
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -U pip
pip install -r requirements.txt
pytest tests/test_01_environment.py -v
```

## Step 2 — 数据库模型

```bash
pytest tests/test_02_database.py -v
```

## Step 3 — 任务服务层（create / list / cancel）

```bash
pytest tests/test_03_service.py -v
```

## Step 4 — FastAPI 路由

```bash
pytest tests/test_04_api.py -v
```

## Step 5 — APScheduler + Gotify 推送

```bash
pytest tests/test_05_scheduler.py -v
```

## 一次性跑全部测试

```bash
pytest tests/ -v
```

## 本地启动 API（会启动调度器）

```bash
source .venv/bin/activate
export MYHELPER_GOTIFY_TOKEN=你的_app_token
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

环境变量前缀为 `MYHELPER_`，例如：`MYHELPER_DATABASE_URL`、`MYHELPER_GOTIFY_URL`、`MYHELPER_GOTIFY_TOKEN`、`MYHELPER_SCAN_INTERVAL_SECONDS` 等，字段定义见 `app/core/config.py`。

后续步骤见各 `tests/test_0*.py` 文件顶部说明。
