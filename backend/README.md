# AgriAI Backend

FastAPI modular monolith backend for Flutter Web and Flutter Mobile.

## Run locally

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\alembic upgrade head
.\.venv\Scripts\uvicorn app.main:app --reload
```

The required plain commands also work after activating the virtual environment:

```bash
python -m venv .venv
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

## Architecture

The backend is a modular monolith. There are no microservices, containers, queues, event buses, or cloud dependencies.

Main modules:

- `auth`: register, login, refresh, current user
- `farms`: create, update, delete, list
- `crops`: create, update, delete, list
- `chat`: message handling and conversation history
- `disease`: image upload and explainable diagnosis
- `recommendations`: generation and history
- `weather`: provider abstraction with local weather fallback
- `orchestrator`: hierarchical agriculture flow

## API response format

All modern `/api/v1` endpoints return:

```json
{
  "success": true,
  "message": "",
  "data": {}
}
```

Compatibility endpoints are also available for the existing Flutter client:

- `GET /api/weather`
- `GET /api/crop`
- `POST /api/crop`
- `POST /api/chat`
- `POST /api/scan`

## Hierarchical XAI orchestration

Image analysis runs sequentially:

1. Context Builder
2. Crop Detection
3. Disease Detection
4. Severity Estimation
5. Weather Context
6. Historical Context
7. Recommendation Engine
8. Response Builder

The predictor interfaces are:

```python
CropPredictor.predict(image)
DiseasePredictor.predict(crop, image)
SeverityPredictor.predict(crop, disease, image)
RecommendationEngine.generate(crop, disease, severity, weather, history)
ResponseBuilder.generate(recommendation)
```

The included model implementations are local explainable adapters. They return confidence, evidence, rule traces, and heatmap hints, so the platform works immediately and can later swap in TensorFlow, PyTorch, ONNX, or another trained plant-disease model behind the same interfaces.

## Database

Default local fallback:

```env
DATABASE_URL=sqlite:///./agri_ai.db
```

PostgreSQL:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/agri_ai
```

SQLite is the default so the backend starts without PostgreSQL. For PostgreSQL, install a compatible `psycopg[binary]` driver for your Python version.
