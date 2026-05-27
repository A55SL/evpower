# EV Charger Automated Validation & OTA Update Pipeline

A demo system that simulates the validation and OTA firmware update loop between an EV charger and a CSMS (Central Station Management System). Postman acts as the charger, a FastAPI server acts as the middleware, and GitHub Actions handles the validation and update logic.

---

## How It Works

```
Postman POST /charger/telemetry
        │
        ▼
FastAPI receiver (Docker)
        │  fires repository_dispatch → validate-charger
        ▼
Pipeline 1 — Validate Charger
    ├── PASS → charger is ready for CSMS. Done.
    └── FAIL (retry_count < 3)
            │  fires repository_dispatch → ota-update
            ▼
        Pipeline 2 — OTA Firmware Update
            │  simulates OTA push (httpbin.org)
            │  sets firmware_ver = v2.0.0
            │  fires repository_dispatch → validate-charger
            ▼
        Pipeline 1 — re-runs and PASSES. Done.
```

### Validation Rules (Pipeline 1)

| Field | Rule |
|---|---|
| `ocpp_variant` | Must be exactly `OCPP-1.6J` or `OCPP-2.0.1` |
| `firmware_ver` | Must be `>= v2.0.0` (e.g. `v2.0.0`, `v2.1.0`, `v3.0.0`) |

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- A GitHub **Personal Access Token** (PAT) with `repo` scope
  - GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
  - Check the `repo` box and generate
- This repo pushed to GitHub (the pipeline dispatches go to the GitHub API)

---

## Setup

### 1. Add your `.env` file

```bash
cp receiver/.env.example receiver/.env
```

Edit `receiver/.env`:

```
GH_TOKEN=ghp_your_personal_access_token_here
GH_OWNER=your-github-username
GH_REPO=evpower
```

### 2. Add the `GH_PAT` secret to your GitHub repo

This allows the pipelines to dispatch events to each other.

GitHub repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

- Name: `GH_PAT`
- Value: same PAT you put in your `.env`

### 3. Start the receiver

```bash
docker compose up --build
```

The receiver is now running at `http://localhost:8000`.

---

## Sending Requests from Postman

**Method:** `POST`  
**URL:** `http://localhost:8000/charger/telemetry`  
**Headers:** `Content-Type: application/json`

### Scenario A — Validation Fails → OTA Triggered

```json
{
  "charger_id": "CHG-001",
  "manufacture": "ABB",
  "model_name": "Terra 54",
  "ocpp_variant": "OCPP-1.6J",
  "firmware_ver": "v1.9.5"
}
```

Expected: Pipeline 1 fails → Pipeline 2 fires (OTA to v2.0.0) → Pipeline 1 re-runs and passes.

### Scenario B — Validation Passes Immediately

```json
{
  "charger_id": "CHG-002",
  "manufacture": "ChargePoint",
  "model_name": "CT4000",
  "ocpp_variant": "OCPP-2.0.1",
  "firmware_ver": "v2.1.0"
}
```

Expected: Pipeline 1 passes on the first run. No OTA triggered.

### Scenario C — Invalid OCPP Variant

```json
{
  "charger_id": "CHG-003",
  "manufacture": "Wallbox",
  "model_name": "Pulsar Plus",
  "ocpp_variant": "OCPP-1.5",
  "firmware_ver": "v2.0.0"
}
```

Expected: Pipeline 1 fails (bad OCPP variant) → OTA triggered (but OCPP is still wrong after OTA) → retries up to 3x then aborts with an error.

---

## Project Structure

```
evpower/
├── .github/
│   └── workflows/
│       ├── pipeline1_validate.yml     # Validation logic + OTA trigger
│       └── pipeline2_ota_update.yml   # Simulated OTA + re-validation loop
├── receiver/
│   ├── main.py                        # FastAPI app
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example                   # Copy to .env and fill in values
├── docker-compose.yml
└── readme.md
```

---

## API Reference

### `GET /health`
Returns `{"status": "ok"}`. Useful for checking the container is up.

### `POST /charger/telemetry`
Accepts charger telemetry and dispatches Pipeline 1.

**Request body:**
```json
{
  "charger_id": "string",
  "manufacture": "string",
  "model_name": "string",
  "ocpp_variant": "string",
  "firmware_ver": "string"
}
```

**Response (202):**
```json
{
  "status": "dispatched",
  "event_type": "validate-charger",
  "charger_id": "CHG-001",
  "github_status": 204,
  "message": "Pipeline 1 (validation) has been triggered on GitHub Actions."
}
```

Interactive docs available at `http://localhost:8000/docs` while the container is running.
