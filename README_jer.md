# Product Repricing Pipeline — Technical Assessment (ekz)

* This README serves as both the implementation guide and submission documentation for the EKZ Technical Assessment.

A complete **end‑to‑end data pipeline** that:
- Fetches product data from a local API
- Applies detailed business repricing rules
- Stores results in an SQLite database
- Exposes repriced data through a FastAPI service
- Runs manually or on schedule using Prefect

---

## Folder Structure
```
ekz_technical_assessment/
├── api/                     # Provided local mock API (data source)
├── your_pipeline/
│   ├── clients/             # API client logic
│   ├── config/              # Configuration (env settings, logging)
│   ├── db/                  # Database models & repository layer
│   ├── flows/               # Prefect orchestration flows
│   ├── models/              # Pydantic data models
│   ├── pricing/             # Core pricing rules
│   ├── scripts/             # CLI scripts (run_flow, deploy)
│   ├── services/            # FastAPI query service
│   └── tests/               # Unit tests
└── README_jer.md
```

---

## Setup

### 1. Create a Python virtual environment
```bash
python -m venv venv
# Activate it
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate
```

### 2️. Install dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure environment variables
Copy `.env.example` → `.env` and fill in:
```bash
API_BASE_URL=http://127.0.0.1:8000/api/v1
API_KEY=testkey123           # read the readme in api folder
DB_URL=sqlite:///your_pipeline/data.db
```

---

## Run Components

### 1. Start the **Source API**
In one terminal:
```bash
uvicorn api.app.app:app --reload --port 8000
```
Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 2. Run the **Pipeline Flow**
In another terminal:
```bash
python -m your_pipeline.scripts.run_flow
```

This performs:
1. **Extract** product data from the local API  
2. **Transform** with pricing rules (vendor → category → brand hierarchy)  
3. **Load** results into `your_pipeline/data.db`

If successful:
```
Flow run '...' - Finished in state Completed()
```

### 3. Start the **Query API (Read Service)**
After the flow successfully populates the database, start the FastAPI service to query and inspect repriced products:
```bash
uvicorn your_pipeline.services.app:app --reload --port 9000
Docs: [http://127.0.0.1:9000/docs](http://127.0.0.1:9000/docs)

Endpoints:
- `/repriced` → all repriced products  
- `/repriced?vendor_id=1` → filter by vendor  
- `/repriced?category_id=3&brand_id=2` → multiple filters  

---

## Schedule with Prefect

Run the flow automatically at **03:00 AM (Local time)**:
```bash
python -m your_pipeline.flows.deploy
```

Prefect will launch a lightweight local scheduler and execute daily.

---

## Testing
Run all tests:
```bash
pytest -v
```

Covers:
- Pricing rule logic (vendor/category/brand hierarchy)
- Rounding and margin computations
- Database upserts & idempotence

---


## Typical Run Order
```bash
# Terminal 1: start mock API
uvicorn api.app.app:app --reload --port 8000

# Terminal 2: run flow manually
python -m your_pipeline.scripts.run_flow

# Terminal 3: serve read API
uvicorn your_pipeline.services.app:app --reload --port 9000
```

---

**Author:** Jer Heseoh Arsolon  
**Language:** Python 3.12  
**Frameworks:** Prefect 3 · FastAPI · SQLAlchemy · Pydantic  
**Database:** SQLite
