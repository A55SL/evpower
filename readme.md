# EV Lader Integrations Service

Et microservice der integrerer tredjeparts EV-ladere i et charge management system uden at være bundet til én bestemt producent. Servicen validerer OCPP-standarder og udløser automatiske OTA firmware-opdateringer via GitHub Actions når der opdages en versions-mismatch.

---

## Flowet

1. EV-laderen sender telemetri til `POST /telemetry`
2. Servicen udløser **Validerings-pipeline** (GitHub Actions)
3. Hvis OCPP-versionen matcher → lader registreret (`CONFIG_SUCCESS`)
4. Hvis OCPP-versionen ikke matcher → **OTA Opdaterings-pipeline** udløses automatisk
5. GitHub Actions opdaterer firmware og kalder tilbage til servicen
6. Servicen udløser validering igen for det endelige handshake

---

## Tech stack

| Komponent | Teknologi |
|---|---|
| API | FastAPI (Python) |
| Database | MySQL 8.0 |
| Overvågning | Prometheus + Grafana |
| CI/CD | GitHub Actions |
| Containerisering | Docker + Docker Compose |
| Lader-simulering | Postman |

---

## Kom i gang

### Forudsætninger
- Docker Desktop
- ngrok konto
- GitHub konto

### 1. Klon repo'et
```bash
git clone https://github.com/a55sl/evpower.git
cd evpower
```

### 2. Opsæt miljøvariabler
```bash
cp .env.example .env
```

Åbn `.env` og udfyld dine værdier:

```env
API_KEY=din_api_nøgle
GITHUB_TOKEN=dit_github_token
GITHUB_REPO_OWNER=dit_brugernavn
GITHUB_REPO_NAME=dit_repo_navn
MYSQL_HOST=mysql
MYSQL_PORT=3306
MYSQL_USER=ev_user
MYSQL_PASSWORD=dit_password
MYSQL_DATABASE=ev_charger_db
SERVICE_CALLBACK_URL=din_ngrok_url
```

### 3. Tilføj GitHub Actions secrets
Gå til dit repo → **Settings → Secrets and variables → Actions** og tilføj:
- `API_KEY`
- `SERVICE_CALLBACK_URL`

### 4. Start ngrok
```bash
ngrok http 8000
```

Kopiér `https://` URL'en og opdater `SERVICE_CALLBACK_URL` i både `.env` og GitHub Actions secrets.

### 5. Start alle services
```bash
docker-compose up --build
```

### 6. Verificér at services kører

| Service | URL |
|---|---|
| FastAPI | http://localhost:8000/docs |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 |

---

## API endpoints

| Metode | Endpoint | Beskrivelse | Auth |
|---|---|---|---|
| `GET` | `/health` | Helbredstjek | Nej |
| `POST` | `/telemetry` | Lader sender data | Ja |
| `POST` | `/chargers/{id}/validate` | Validerings-callback fra GitHub Actions | Ja |
| `PATCH` | `/chargers/{id}/firmware` | OTA-callback fra GitHub Actions | Ja |
| `GET` | `/chargers/{id}/status` | Hent aktuel ladertilstand | Ja |
| `GET` | `/chargers/{id}/ota-history` | Hent OTA opdateringshistorik | Ja |
| `GET` | `/metrics` | Prometheus metrics | Nej |
