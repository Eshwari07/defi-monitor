# DeFi Protocol Monitor

A robust monitoring pipeline for tracking the health of DeFi protocols in vault allocations. It fetches metrics (TVL, APY, Utilization), detects anomalies, and provides a health API.

## Features

- **Multi-Protocol Support**: Monitors Felix (Lending) and HLP (Vault).
- **Metric Ingestion**: Fetches TVL from DeFiLlama and simulates APY/Utilization (extensible to on-chain).
- **Anomaly Detection**:
  - **Critical**: TVL drops > 20% in 24 hours.
  - **Warning**: APY drops below 2%.
  - **Warning**: Utilization > 95% (Lending protocols).
- **Resilient Pipeline**: Handles API failures, timeouts, and is idempotent.
- **REST API**: FastAPI endpoints for health checks, history, and alerts.
- **Dashboard**: Simple HTML dashboard to view status.

## Prerequisites

- Python 3.10+ (Tested with 3.11 and 3.13)
- Windows/Linux/macOS

## Installation

1.  **Clone the repository**:
    ```bash
    git clone <repository_url>
    cd defi-monitor
    ```

2.  **Create and activate a virtual environment**:
    ```bash
    # Windows
    python -m venv venv
    .\venv\Scripts\Activate.ps1

    # Linux/Mac
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

### 1. Run the Application
Start the API and Ingestion server:
```bash
python run.py
```
The server will start at `http://0.0.0.0:8000`.

- **Dashboard**: [http://localhost:8000/dashboard](http://localhost:8000/dashboard)
- **API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

### 2. Manual Ingestion (Optional)
The ingestion runs automatically, but you can trigger it manually via the script:

**Windows (PowerShell):**
```powershell
$env:PYTHONPATH="."
python app/services/ingest.py
```

**Linux/Mac:**
```bash
export PYTHONPATH=$PYTHONPATH:.
python app/services/ingest.py
```

### 3. Resolving Alerts
You can resolve alerts directly from the Dashboard by clicking the **Resolve** button on an alert item.

Alternatively, use the helper script:
```bash
python scripts/resolve_alert.py
```

### 4. Run Demo Alert
To simulate a protocol crash and verify alerts:
```bash
python scripts/demo_alert.py
```
This script injects specific database entries to simulate a 50% TVL drop in the 'felix' protocol and triggers a CRITICAL alert.

## API Endpoints

- `GET /`: System health check.
- `GET /protocols`: List of monitored protocols and their status.
- `GET /protocols/{name}/history`: Historical metrics.
- `GET /alerts`: List active alerts (filter by status='open').
- `POST /alerts/{id}/resolve`: Resolve an alert.

## Configuration

Settings are managed in `app/core/config.py` and can be overridden by environment variables or a `.env` file.

| Variable | Default | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | `sqlite:///./defi_monitor.db` | Database connection string |
| `TVL_DROP_THRESHOLD` | `0.20` | 20% drop triggers critical alert |
| `APY_MIN_THRESHOLD` | `2.0` | Below 2% triggers warning |
| `UTILIZATION_MAX_THRESHOLD` | `0.95` | Above 95% triggers warning |

## Project Structure

```
defi-monitor/
├── app/
│   ├── core/               # Configuration and database setup
│   │   ├── config.py
│   │   └── database.py
│   ├── models/             # Data models
│   │   ├── models.py       # SQLAlchemy ORM models
│   │   └── schemas.py      # Pydantic schemas
│   ├── services/           # Business logic
│   │   ├── fetchers/       # Protocol data fetchers
│   │   ├── anomaly_detector.py
│   │   └── ingest.py
│   ├── static/             # Frontend assets
│   │   └── index.html
│   └── main.py             # FastAPI application
├── scripts/
│   ├── demo_alert.py       # Simulation script
│   └── resolve_alert.py    # Alert resolution utility
├── run.py                  # Application entry point
├── requirements.txt        # Python dependencies
└── README.md
```
